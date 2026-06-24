from fastapi import APIRouter, HTTPException, Query
from datetime import date, timedelta
from services.risk_calendar import (
    get_calendar_range, get_day_hourly, get_forecast
)

router = APIRouter()


@router.get("/range")
def calendar_range(
    start: date = Query(default=None, description="시작일 YYYY-MM-DD"),
    end:   date = Query(default=None, description="종료일 YYYY-MM-DD"),
):
    today = date.today()
    if start is None:
        start = date(2023, 3, 1)
    if end is None:
        end = today
    if (end - start).days > 1500:
        raise HTTPException(400, "조회 기간은 최대 1500일입니다")
    days = get_calendar_range(start, end)
    return {
        "start": str(start),
        "end": str(end),
        "total_days": len(days),
        "days": days,
    }


@router.get("/day/{target_date}")
def calendar_day(target_date: date):
    today = date.today()
    min_date = date(2023, 3, 1)
    if target_date < min_date and target_date > today + timedelta(days=90):
        raise HTTPException(400, "조회 가능 범위 초과")
    return get_day_hourly(target_date)


@router.get("/forecast")
def calendar_forecast(days: int = Query(default=30, le=90)):
    return {"forecast": get_forecast(days)}


@router.get("/stats")
def calendar_stats():
    from services.risk_calendar import _load_daily, _load_seasonal
    import pandas as pd
    daily    = _load_daily()
    seasonal = _load_seasonal()

    return {
        "data_range": {
            "start": str(daily["date"].min().date()),
            "end":   str(daily["date"].max().date()),
            "total_days": len(daily),
        },
        "triple_risk": {
            "total_days": int((daily["triple_risk_hours"] > 0).sum()),
            "pct_of_total": round((daily["triple_risk_hours"] > 0).mean() * 100, 1),
            "avg_hours_per_day": round(float(daily["triple_risk_hours"].mean()), 2),
        },
        "risk_level_counts": daily["risk_level"].value_counts().to_dict(),
        "monthly_avg": seasonal[
            ["month", "avg_risk_score", "avg_triple_hours", "fog_prob"]
        ].to_dict(orient="records"),
        "peak_month": int(seasonal.loc[seasonal["avg_risk_score"].idxmax(), "month"]),
    }
