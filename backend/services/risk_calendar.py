"""
위험 캘린더 서비스
- 과거: 실 데이터(조위+기상) 기반 일별/시간별 위험 점수
- 미래: 조석 수식 + 계절 통계 기반 예측
"""
import math
import pandas as pd
import numpy as np
from datetime import date, datetime, timedelta
from pathlib import Path
from functools import lru_cache

PROCESSED = Path(__file__).parent.parent / "data" / "processed"

# ── 데이터 로드 (앱 시작 시 1회) ────────────────────────────
@lru_cache(maxsize=1)
def _load_daily():
    p = PROCESSED / "daily_risk.csv"
    df = pd.read_csv(p, parse_dates=["date"])
    df["date_d"] = df["date"].dt.date
    return df

@lru_cache(maxsize=1)
def _load_tide():
    p = PROCESSED / "tide_hourly.csv"
    return pd.read_csv(p, parse_dates=["dt"])

@lru_cache(maxsize=1)
def _load_weather():
    p = PROCESSED / "weather_hourly.csv"
    return pd.read_csv(p, parse_dates=["dt"])

@lru_cache(maxsize=1)
def _load_seasonal():
    p = PROCESSED / "seasonal_stats.csv"
    return pd.read_csv(p)


# ── 과거 일별 위험 캘린더 ────────────────────────────────────
def get_calendar_range(start: date, end: date) -> list[dict]:
    daily = _load_daily()
    mask = (daily["date_d"] >= start) & (daily["date_d"] <= end)
    rows = daily[mask].copy()

    today = date.today()
    result = []
    for _, r in rows.iterrows():
        d = r["date_d"]
        result.append({
            "date": str(d),
            "risk_score": round(float(r["risk_score"]), 4),
            "risk_level": str(r["risk_level"]),
            "triple_risk_hours": int(r["triple_risk_hours"]),
            "dual_risk_hours": int(r["dual_risk_hours"]),
            "fog_hours": int(r["fog_hours"]),
            "high_tide_hours": int(r["high_tide_hours"]),
            "night_hours": int(r["night_hours"]),
            "avg_tide_cm": round(float(r["avg_tide_cm"]), 1),
            "min_vis_m": round(float(r["min_vis_m"]), 0) if pd.notna(r["min_vis_m"]) else None,
            "is_past": d <= today,
            "source": "실측",
        })
    return result


# ── 특정 날짜 시간별 분해 ────────────────────────────────────
def get_day_hourly(target: date) -> dict:
    tide = _load_tide()
    weather = _load_weather()
    today = date.today()

    if target <= today:
        # 실 데이터
        t_day = tide[tide["dt"].dt.date == target].copy()
        w_day = weather[weather["dt"].dt.date == target].copy()

        t_day["dt_h"] = t_day["dt"].dt.floor("h")
        w_day["dt_h"] = w_day["dt"].dt.floor("h")
        merged = pd.merge(
            t_day[["dt_h", "tide_cm", "is_high_tide"]],
            w_day[["dt_h", "vs_m", "is_fog", "is_night"]],
            on="dt_h", how="outer"
        ).sort_values("dt_h")

        hours = []
        for _, row in merged.iterrows():
            triple = bool(row.get("is_high_tide", False) and
                          row.get("is_fog", False) and
                          row.get("is_night", False))
            hours.append({
                "hour": int(row["dt_h"].hour) if pd.notna(row["dt_h"]) else None,
                "tide_cm": int(row["tide_cm"]) if pd.notna(row.get("tide_cm")) else None,
                "is_high_tide": bool(row.get("is_high_tide", False)),
                "vis_m": float(row["vs_m"]) if pd.notna(row.get("vs_m")) else None,
                "is_fog": bool(row.get("is_fog", False)),
                "is_night": bool(row.get("is_night", False)),
                "triple_risk": triple,
                "risk_score": _hour_score(row),
            })
        source = "실측"
    else:
        # 미래 예측
        hours = _forecast_hourly(target)
        source = "예측"

    daily_score = _load_daily()[_load_daily()["date_d"] == target]
    summary = {}
    if not daily_score.empty:
        r = daily_score.iloc[0]
        summary = {
            "risk_score": round(float(r["risk_score"]), 4),
            "risk_level": str(r["risk_level"]),
            "triple_risk_hours": int(r["triple_risk_hours"]),
        }
    else:
        hrs = [h for h in hours if h.get("triple_risk")]
        summary = {
            "risk_score": round(len(hrs) / max(len(hours), 1), 4),
            "risk_level": _score_to_level(len(hrs) / max(len(hours), 1)),
            "triple_risk_hours": len(hrs),
        }

    return {"date": str(target), "source": source, "summary": summary, "hours": hours}


def _hour_score(row) -> float:
    score = 0.0
    if pd.notna(row.get("is_high_tide")) and row["is_high_tide"]: score += 0.35
    if pd.notna(row.get("is_fog")) and row["is_fog"]:             score += 0.40
    if pd.notna(row.get("is_night")) and row["is_night"]:         score += 0.25
    return round(score, 2)


def _score_to_level(score: float) -> str:
    if score >= 0.35: return "위험"
    if score >= 0.15: return "경계"
    if score >= 0.05: return "주의"
    return "정상"


# ── 미래 예측 ────────────────────────────────────────────────
def get_forecast(days: int = 30) -> list[dict]:
    seasonal = _load_seasonal()
    today = date.today()
    result = []

    for i in range(1, days + 1):
        target = today + timedelta(days=i)
        month = target.month
        stats = seasonal[seasonal["month"] == month]

        if stats.empty:
            avg_risk = 0.5
            fog_prob = 0.3
            avg_triple = 1.0
        else:
            avg_risk  = float(stats["avg_risk_score"].iloc[0])
            fog_prob  = float(stats["fog_prob"].iloc[0])
            avg_triple = float(stats["avg_triple_hours"].iloc[0])

        # 조석은 결정론적 예측 (사인파 근사)
        tide_pred = _predict_tide_day(target)
        high_tide_h = sum(1 for t in tide_pred if t >= 500)

        # 신뢰도: 7일 이하 80%, 14일 이하 65%, 30일 50%, 이후 감소
        confidence = max(30, int(80 - (i - 1) * 1.8))

        risk_score = round(min(avg_risk * (0.85 + 0.3 * (high_tide_h / 12)), 1.0), 4)

        result.append({
            "date": str(target),
            "risk_score": risk_score,
            "risk_level": _score_to_level(risk_score),
            "predicted_triple_hours": round(avg_triple * (high_tide_h / 6), 1),
            "fog_prob_pct": round(fog_prob * 100),
            "high_tide_hours": high_tide_h,
            "confidence_pct": confidence,
            "is_past": False,
            "source": "예측",
            "tide_hourly": tide_pred,
        })

    return result


def get_env_day_forecast(target: date) -> dict:
    """미래 날짜의 환경 위험 지수 요약 — 격자별 CVI 예측에 사용"""
    hours = _forecast_hourly(target)
    triple_h = sum(1 for h in hours if h["triple_risk"])
    high_tide_h = sum(1 for h in hours if h["is_high_tide"])
    fog_h = sum(1 for h in hours if h["is_fog"])

    env_ratio = (triple_h / 6.0) * 0.60 + (high_tide_h / 12.0) * 0.25 + (fog_h / 14.0) * 0.15
    env_multiplier = round(0.75 + min(env_ratio, 1.0) * 0.50, 4)

    return {
        "triple_hours": triple_h,
        "high_tide_hours": high_tide_h,
        "fog_hours": fog_h,
        "env_ratio": round(env_ratio, 4),
        "env_multiplier": env_multiplier,
    }


def _predict_tide_day(target: date) -> list[int]:
    """군산항 조석 수식 근사 (반일주조 12.42h + 진폭 395cm + 기준 290cm)"""
    # 기준점: 2023-03-01 00:00 = 319cm (실측 첫 값)
    ref = datetime(2023, 3, 1, 0, 0)
    period_h = 12.42
    amplitude = 240  # cm (반진폭)
    mean_tide = 290  # cm (평균 기준면)

    result = []
    for h in range(24):
        dt = datetime(target.year, target.month, target.day, h, 0)
        elapsed_h = (dt - ref).total_seconds() / 3600
        phase = (elapsed_h % period_h) / period_h * 2 * math.pi
        tide = round(mean_tide + amplitude * math.sin(phase))
        result.append(tide)
    return result


def _forecast_hourly(target: date) -> list[dict]:
    """미래 날짜 시간별 예측"""
    seasonal = _load_seasonal()
    month = target.month
    stats = seasonal[seasonal["month"] == month]
    fog_prob = float(stats["fog_prob"].iloc[0]) if not stats.empty else 0.3

    tide_pred = _predict_tide_day(target)
    hours = []
    for h, tide_cm in enumerate(tide_pred):
        is_high = tide_cm >= 500
        is_night = h >= 20 or h < 6
        # 안개는 확률적으로 야간에 높음
        fog_chance = fog_prob * (1.4 if is_night else 0.6)
        is_fog_pred = fog_chance > 0.5  # 결정론적 임계값 적용

        triple = is_high and is_fog_pred and is_night
        hours.append({
            "hour": h,
            "tide_cm": tide_cm,
            "is_high_tide": is_high,
            "vis_m": None,
            "is_fog": is_fog_pred,
            "is_fog_prob": round(fog_chance, 2),
            "is_night": is_night,
            "triple_risk": triple,
            "risk_score": _hour_score({"is_high_tide": is_high,
                                       "is_fog": is_fog_pred,
                                       "is_night": is_night}),
            "is_predicted": True,
        })
    return hours
