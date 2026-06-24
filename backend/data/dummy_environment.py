"""
실시간 환경 더미 데이터 (기상 + 조석)
ASOS 실 데이터 연동 전 구현 검증용
군산 기준 (위도 35.97, 경도 126.71)
"""
import random
import math
from datetime import datetime, timedelta

random.seed(int(datetime.now().timestamp()) % 10000)


def get_current_environment() -> dict:
    now = datetime.now()
    hour = now.hour

    # 야간 판단 (일몰 19:30 ~ 일출 05:30 기준, 계절 무시)
    is_night = hour >= 20 or hour < 6

    # 시정 (안개: 야간 + 습도 높을 때 자주 발생)
    fog_prob = 0.35 if is_night else 0.10
    is_fog = random.random() < fog_prob
    visibility_km = round(random.uniform(0.3, 1.2) if is_fog else random.uniform(3.0, 15.0), 1)

    # 풍속 (m/s)
    wind_speed = round(random.uniform(0.5, 8.0), 1)
    wind_dir_deg = random.randint(0, 359)
    wind_directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                       "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    wind_dir = wind_directions[round(wind_dir_deg / 22.5) % 16]

    # 기온
    temp_c = round(random.uniform(15.0, 28.0) if not is_night else random.uniform(12.0, 22.0), 1)

    # 습도
    humidity = random.randint(70, 96) if is_fog else random.randint(50, 85)

    # 조위 (군산항 기준, 6시간 주기 사인파 시뮬레이션)
    # 군산 평균 조차 약 6m (서해 최대)
    tide_cycle_hours = 12.42  # 반일주조
    phase = (now.timestamp() % (tide_cycle_hours * 3600)) / (tide_cycle_hours * 3600)
    tide_height_m = round(3.2 * math.sin(2 * math.pi * phase) + 3.0, 2)  # 0.0 ~ 6.2m

    # 만조 판단 (조위 5.0m 이상 — 군산 평균 최고조위 약 6.2m 기준)
    is_high_tide = tide_height_m >= 5.0

    # 다음 만조/간조까지 시간 계산
    next_high_tide_h = tide_cycle_hours / 2 * (1 - phase) if phase < 0.5 else tide_cycle_hours * (1 - phase)
    next_low_tide_h = tide_cycle_hours / 2 * (0.5 - phase) if phase < 0.5 else tide_cycle_hours * (1.5 - phase)
    next_high_tide_h = abs(round(next_high_tide_h, 1))
    next_low_tide_h = abs(round(next_low_tide_h, 1))

    # 3중 취약 판단 (야간 + 만조 + 안개)
    triple_risk = is_night and is_high_tide and is_fog

    return {
        "timestamp": now.isoformat(),
        "station": "군산 (140)",
        "weather": {
            "temperature_c": temp_c,
            "humidity_pct": humidity,
            "wind_speed_ms": wind_speed,
            "wind_direction": wind_dir,
            "wind_direction_deg": wind_dir_deg,
            "visibility_km": visibility_km,
            "is_fog": is_fog,
            "condition": "안개" if is_fog else ("흐림" if humidity > 80 else "맑음"),
        },
        "tide": {
            "height_m": tide_height_m,
            "is_high_tide": is_high_tide,
            "next_high_tide_in_h": next_high_tide_h,
            "next_low_tide_in_h": next_low_tide_h,
            "tide_phase": "만조" if is_high_tide else ("간조" if tide_height_m < 1.5 else "중간"),
        },
        "time": {
            "hour": hour,
            "is_night": is_night,
            "period": "야간" if is_night else "주간",
        },
        "triple_risk": {
            "active": triple_risk,
            "components": {
                "night": is_night,
                "high_tide": is_high_tide,
                "fog": is_fog,
            },
            "level": "위험" if triple_risk else (
                "경계" if sum([is_night, is_high_tide, is_fog]) == 2 else (
                    "주의" if sum([is_night, is_high_tide, is_fog]) == 1 else "정상"
                )
            ),
        },
    }


def get_7day_forecast() -> list:
    """7일 3중취약일 예측 (더미)"""
    forecast = []
    now = datetime.now()

    for i in range(7):
        date = now + timedelta(days=i)
        risk_score = random.randint(0, 3)
        forecast.append({
            "date": date.strftime("%Y-%m-%d"),
            "day_label": ["오늘", "내일", "모레"][i] if i < 3 else date.strftime("%m/%d"),
            "triple_risk_count": risk_score,
            "risk_hours": [f"{random.randint(0,5):02d}:00" for _ in range(risk_score)],
            "level": "위험" if risk_score >= 3 else ("경계" if risk_score == 2 else ("주의" if risk_score == 1 else "정상")),
            "fog_prob_pct": random.randint(10, 80),
            "high_tide_times": [f"{random.randint(0,23):02d}:{random.choice(['00','15','30','45'])}"],
        })

    return forecast


def get_timeseries_anomaly(grid_id: str, days: int = 30) -> list:
    """격자별 야간 이상 지수 시계열 (STL 잔차 더미)"""
    series = []
    now = datetime.now()
    random.seed(hash(grid_id) % 10000)

    for i in range(days):
        date = now - timedelta(days=days - i)
        # STL 계절 성분 (가을에 높음: 9~10월)
        month = date.month
        seasonal = 0.3 if month in [9, 10] else (0.1 if month in [8, 11] else -0.05)
        trend = 0.02 * (i / days)
        residual = random.gauss(0, 0.15)
        anomaly = round(max(0, seasonal + trend + residual), 3)

        series.append({
            "date": date.strftime("%Y-%m-%d"),
            "anomaly_index": anomaly,
            "seasonal": round(seasonal, 3),
            "trend": round(trend, 3),
            "residual": round(residual, 3),
            "is_triple_risk": anomaly > 0.4 and random.random() < 0.3,
        })

    return series
