"""
환경 더미 데이터 — import 오류 시 fallback용
정상 경로: services/environment_service.py (실 데이터 + 기상청 ASOS API)
"""
import math
import random
from datetime import datetime, timedelta


def get_current_environment() -> dict:
    rng = random.Random(int(datetime.now().timestamp()) // 3600)  # 1시간 단위 고정
    now = datetime.now()
    hour = now.hour
    is_night = hour >= 20 or hour < 6
    is_fog = rng.random() < (0.35 if is_night else 0.10)
    vis_km = round(rng.uniform(0.3, 1.2) if is_fog else rng.uniform(3.0, 15.0), 1)
    wind_ms = round(rng.uniform(0.5, 8.0), 1)
    wind_deg = rng.randint(0, 359)
    dirs = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    wind_dir = dirs[round(wind_deg / 22.5) % 16]
    temp_c = round(rng.uniform(12.0, 22.0) if is_night else rng.uniform(15.0, 28.0), 1)
    humidity = rng.randint(70, 96) if is_fog else rng.randint(50, 85)
    phase = (now.timestamp() % (12.42 * 3600)) / (12.42 * 3600)
    tide_m = round(3.2 * math.sin(2 * math.pi * phase) + 3.0, 2)
    is_high = tide_m >= 5.0
    triple = is_night and is_high and is_fog
    dual = sum([is_night, is_high, is_fog])
    return {
        "timestamp": now.isoformat(),
        "station": "군산 (140)",
        "data_source": "더미 (fallback)",
        "weather": {"temperature_c": temp_c, "humidity_pct": humidity, "wind_speed_ms": wind_ms,
                    "wind_direction": wind_dir, "wind_direction_deg": wind_deg,
                    "visibility_km": vis_km, "is_fog": is_fog,
                    "condition": "안개" if is_fog else ("흐림" if humidity > 80 else "맑음")},
        "tide": {"height_m": tide_m, "height_cm": round(tide_m * 100),
                 "is_high_tide": is_high,
                 "next_high_tide_in_h": round(abs(12.42 / 2 * (1 - phase)), 1),
                 "next_low_tide_in_h": round(abs(12.42 / 2 * (0.5 - phase)), 1),
                 "tide_phase": "만조" if is_high else ("간조" if tide_m < 1.5 else "중간")},
        "time": {"hour": hour, "is_night": is_night, "period": "야간" if is_night else "주간"},
        "triple_risk": {"active": triple,
                        "components": {"night": is_night, "high_tide": is_high, "fog": is_fog},
                        "level": "위험" if triple else ("경계" if dual == 2 else ("주의" if dual == 1 else "정상"))},
    }


def get_7day_forecast() -> list:
    rng = random.Random(42)
    now = datetime.now()
    result = []
    for i in range(7):
        d = now + timedelta(days=i)
        cnt = rng.randint(0, 3)
        result.append({
            "date": d.strftime("%Y-%m-%d"),
            "day_label": ["오늘","내일","모레"][i] if i < 3 else d.strftime("%m/%d"),
            "triple_risk_count": cnt,
            "risk_hours": [],
            "level": "위험" if cnt >= 3 else ("경계" if cnt == 2 else ("주의" if cnt == 1 else "정상")),
            "fog_prob_pct": rng.randint(10, 80),
            "high_tide_times": [],
            "risk_score": round(cnt / 6, 3),
            "confidence_pct": 50,
        })
    return result


def get_timeseries_anomaly(grid_id: str, days: int = 90) -> list:
    """STL 실 데이터 fallback — services/stl_service.py 사용 불가 시."""
    rng = random.Random(hash(grid_id) % 10000)
    now = datetime.now()
    series = []
    for i in range(days):
        d = now - timedelta(days=days - i)
        month = d.month
        seasonal = 0.3 if month in [11, 12, 1, 2] else (0.1 if month in [3, 10] else -0.05)
        trend = 0.01 * (i / days)
        residual = rng.gauss(0, 0.10)
        anomaly = round(max(0, seasonal + trend + residual), 3)
        series.append({
            "date": d.strftime("%Y-%m-%d"),
            "anomaly_index": anomaly,
            "seasonal": round(seasonal, 3),
            "trend": round(trend, 3),
            "residual": round(residual, 3),
            "is_triple_risk": anomaly > 0.30,
            "source": "더미 (fallback)",
        })
    return series
