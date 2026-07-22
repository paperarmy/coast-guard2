from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date as date_type, datetime as dt_obj

try:
    from services.cvi_calculator import get_all_grids, get_grid_by_id, get_top_grids, get_hh_grids
except Exception:
    from data.dummy_grids import get_all_grids, get_grid_by_id, get_top_grids, get_hh_grids

try:
    from services.stl_service import get_daily_timeseries as _stl_daily, has_stl_data
    _USE_STL = has_stl_data()
except Exception:
    _USE_STL = False

from data.dummy_environment import get_timeseries_anomaly as _dummy_timeseries

router = APIRouter()


def _cvi_level(cvi: float) -> str:
    if cvi >= 0.80: return "위험"
    if cvi >= 0.65: return "경계"
    if cvi >= 0.50: return "주의"
    return "정상"


def _cvi_color(cvi: float) -> str:
    if cvi >= 0.80: return "#dc2626"
    if cvi >= 0.65: return "#ea580c"
    if cvi >= 0.50: return "#ca8a04"
    return "#16a34a"


@router.get("")
def list_grids(
    region: Optional[str] = Query(None, description="군산|부안|고창"),
    lisa: Optional[str] = Query(None, description="HH|LL|HL|LH|NS"),
    min_cvi: float = Query(0.0, ge=0.0, le=1.1),
    max_cvi: float = Query(1.1, ge=0.0, le=1.1),
    limit: int = Query(210, le=210),
):
    grids = get_all_grids()
    if region:
        grids = [g for g in grids if g["region"] == region]
    if lisa:
        grids = [g for g in grids if g["lisa"] == lisa]
    grids = [g for g in grids if min_cvi <= g["cvi"] <= max_cvi]
    return {"total": len(grids), "grids": grids[:limit]}


@router.get("/top")
def top_grids(n: int = Query(10, le=50, description="상위 N개")):
    return {"grids": get_top_grids(n)}


@router.get("/hotspots")
def hotspot_grids():
    hh = get_hh_grids()
    return {"count": len(hh), "grids": hh}


@router.get("/summary")
def grid_summary():
    grids = get_all_grids()
    lisa_counts = {}
    region_avg = {}
    for g in grids:
        lisa_counts[g["lisa"]] = lisa_counts.get(g["lisa"], 0) + 1
        r = g["region"]
        if r not in region_avg:
            region_avg[r] = []
        region_avg[r].append(g["cvi"])

    return {
        "total_grids": len(grids),
        "avg_cvi": round(sum(g["cvi"] for g in grids) / len(grids), 3),
        "max_cvi": max(g["cvi"] for g in grids),
        "min_cvi": min(g["cvi"] for g in grids),
        "lisa_distribution": lisa_counts,
        "region_avg_cvi": {r: round(sum(v)/len(v), 3) for r, v in region_avg.items()},
        "danger_count": len([g for g in grids if g["cvi"] >= 0.80]),
        "warning_count": len([g for g in grids if 0.65 <= g["cvi"] < 0.80]),
    }


@router.get("/forecast")
def grid_forecast(date: str = Query(..., description="YYYY-MM-DD 형식 미래 날짜 (최대 90일)")):
    try:
        target = dt_obj.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식 오류 (YYYY-MM-DD)")

    today = date_type.today()
    if target <= today:
        raise HTTPException(status_code=400, detail="내일 이후 날짜만 지원합니다")
    delta = (target - today).days
    if delta > 90:
        raise HTTPException(status_code=400, detail="90일 이내 날짜만 지원합니다")

    from services.risk_calendar import get_env_day_forecast
    env = get_env_day_forecast(target)
    env_mult = env["env_multiplier"]

    grids = get_all_grids()
    predicted = []
    for g in grids:
        coast_p = g.get("coast_proximity", 0.5)
        night_a = g.get("night_anomaly_index", 0.5)
        sensitivity = 0.40 + coast_p * 0.35 + night_a * 0.25

        pred_cvi = g["cvi"] * (1.0 + (env_mult - 1.0) * sensitivity)
        pred_cvi = round(max(0.10, min(1.0, pred_cvi)), 4)
        pred_level = _cvi_level(pred_cvi)
        pred_color = _cvi_color(pred_cvi)

        predicted.append({
            **g,
            "cvi": pred_cvi,
            "cvi_level": pred_level,
            "cvi_color": pred_color,
            "cvi_base": g["cvi"],
            "cvi_delta": round(pred_cvi - g["cvi"], 4),
        })

    predicted.sort(key=lambda x: -x["cvi"])
    for i, g in enumerate(predicted):
        g["rank"] = i + 1

    # 신뢰도: 7일 이하 80-65%, 30일 이하 65-50%, 45일 이하 50-40%, 90일 이하 40-30%
    if delta <= 7:
        confidence = max(65, int(80 - (delta - 1) * 2.5))
    elif delta <= 30:
        confidence = max(50, int(65 - (delta - 7) * 0.65))
    elif delta <= 45:
        confidence = max(40, int(50 - (delta - 30) * 0.67))
    else:
        confidence = max(30, int(40 - (delta - 45) * 0.22))

    return {
        "date": str(target),
        "source": "예측",
        "days_ahead": delta,
        "confidence_pct": confidence,
        "env": env,
        "total": len(predicted),
        "grids": predicted,
    }


@router.get("/{grid_id}")
def get_grid(grid_id: str):
    grid = get_grid_by_id(grid_id)
    if not grid:
        raise HTTPException(status_code=404, detail=f"격자 {grid_id} 없음")
    return grid


@router.get("/{grid_id}/timeseries")
def grid_timeseries(grid_id: str, days: int = Query(90, le=918)):
    grid = get_grid_by_id(grid_id)
    if not grid:
        raise HTTPException(status_code=404, detail=f"격자 {grid_id} 없음")

    if _USE_STL:
        coast_p = grid.get("coast_proximity", 0.5)
        raw = _stl_daily(days)
        series = []
        for r in raw:
            # 격자 해안 근접도로 스케일 (해안 격자일수록 야간 이상 민감)
            scale = 0.7 + coast_p * 0.6
            anomaly = round(min(1.0, (r["night_risk"] + max(0, r["residual"])) * scale), 3)
            series.append({
                "date":          r["date"],
                "anomaly_index": anomaly,
                "seasonal":      round(r["seasonal"] * scale, 3),
                "trend":         round(r["trend"] * scale, 3),
                "residual":      round(r["residual"] * scale, 3),
                "is_triple_risk": anomaly > 0.15,
                "source":        "STL 실 데이터 (918일)",
            })
    else:
        series = _dummy_timeseries(grid_id, days)

    return {
        "grid_id":    grid_id,
        "region":     grid["region"],
        "data_source": "STL 분해 실측 (tide+weather 918일)" if _USE_STL else "더미",
        "series":     series,
    }
