"""
실 데이터 기반 현재 환경 조회
- 기상: 기상청 ASOS 실측 API (군산 140) → 실패 시 계절통계 fallback
- 조위: 조석 수식 (군산항 반일주조 근사, 실시간 API 없음)
- 완전 랜덤 제거: 같은 시각 같은 환경 값 반환
"""
import math
from datetime import datetime, date, timedelta
from functools import lru_cache
from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).parent.parent / "data" / "processed"

# ── 계절 통계 로드 ────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_seasonal() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "seasonal_stats.csv")


def _seasonal_row(month: int) -> dict:
    df = _load_seasonal()
    row = df[df["month"] == month]
    if row.empty:
        return {"fog_prob": 0.3, "high_tide_avg_hours": 6.0, "avg_risk_score": 0.5}
    return row.iloc[0].to_dict()


# ── 조석 수식 (risk_calendar._predict_tide_day 로직 동일) ────────────

def _tide_at_hour(target_dt: datetime) -> int:
    """군산항 조석 근사 → 해당 시각 조위(cm)"""
    ref = datetime(2023, 3, 1, 0, 0)
    period_h = 12.42
    amplitude = 240
    mean_tide = 290
    elapsed_h = (target_dt - ref).total_seconds() / 3600
    phase = (elapsed_h % period_h) / period_h * 2 * math.pi
    return round(mean_tide + amplitude * math.sin(phase))


def _next_tide_event(now: datetime, want_high: bool) -> float:
    """다음 만조/간조까지 남은 시간(h)"""
    for m in range(1, 60 * 8):  # 최대 8시간 탐색
        future = now + timedelta(minutes=m)
        t = _tide_at_hour(future)
        t_prev = _tide_at_hour(future - timedelta(minutes=1))
        if want_high and t < t_prev:  # 만조 직후(하강 시작)
            return m / 60
        if not want_high and t > t_prev:  # 간조 직후(상승 시작)
            return m / 60
    return 6.0


# ── 안개 판단 ─────────────────────────────────────────────────────────

def _fog_estimate(month: int, hour: int, tide_cm: int) -> tuple[bool, float]:
    """
    안개 여부·시정 추정
    seasonal fog_prob × 시간대 가중치 × 만조 근접 가중치
    """
    stats = _seasonal_row(month)
    base_prob = float(stats["fog_prob"])

    is_night = hour >= 20 or hour < 6
    time_weight = 1.6 if is_night else 0.7
    tide_weight = 1.2 if tide_cm >= 450 else 1.0  # 만조 시 해무 증가

    fog_prob = min(0.95, base_prob * time_weight * tide_weight)
    is_fog = fog_prob >= 0.55  # 확률 55% 이상이면 안개로 판단

    if is_fog:
        # 안개 시정: 0.2~0.9km (확률에 반비례)
        vis = round(max(0.2, 1.0 - fog_prob), 1)
    else:
        # 맑을 때 시정: 월별 평균 반영 (여름 안개 많으면 평균 시정 낮음)
        vis = round(max(2.0, 15.0 - base_prob * 12.0), 1)

    return is_fog, vis


# ── 기온·풍속 월별 추정 ───────────────────────────────────────────────

_MONTHLY_TEMP = {
    1: 0.5, 2: 2.0, 3: 7.5, 4: 13.5, 5: 18.5, 6: 22.5,
    7: 26.0, 8: 27.5, 9: 22.0, 10: 15.5, 11: 8.0, 12: 2.5,
}
_MONTHLY_WIND = {
    1: 5.5, 2: 5.0, 3: 4.5, 4: 4.0, 5: 3.5, 6: 3.0,
    7: 3.5, 8: 3.0, 9: 3.5, 10: 4.0, 11: 4.5, 12: 5.5,
}


# ── 공개 인터페이스 ───────────────────────────────────────────────────

def get_current_environment() -> dict:
    now = datetime.now()
    hour = now.hour
    month = now.month
    is_night = hour >= 20 or hour < 6

    # ── 조위 (조석 수식) ─────────────────────────────────────────────
    tide_cm = _tide_at_hour(now)
    tide_m = round(tide_cm / 100, 2)
    is_high_tide = tide_cm >= 500
    tide_phase = "만조" if is_high_tide else ("간조" if tide_cm < 150 else "중간")
    next_high_h = round(_next_tide_event(now, want_high=True), 1)
    next_low_h = round(_next_tide_event(now, want_high=False), 1)

    # ── 기상: ASOS 실측 API 우선 → 계절통계 fallback ────────────────
    from services.weather_api import get_current_weather
    real_wx = get_current_weather()

    if real_wx:
        temp_c   = real_wx["temperature_c"] or round(_MONTHLY_TEMP.get(month, 15.0) - (3.0 if is_night else 0.0), 1)
        wind_ms  = real_wx["wind_speed_ms"]
        wind_dir = real_wx["wind_direction"]
        wind_deg = real_wx["wind_direction_deg"]
        humidity = real_wx["humidity_pct"]
        vis_km   = real_wx["visibility_km"]
        is_fog   = real_wx["is_fog"]
        condition = real_wx["condition"]
        wx_source = real_wx["data_source"]
    else:
        # 계절통계 fallback
        is_fog, vis_km = _fog_estimate(month, hour, tide_cm)
        temp_c  = round(_MONTHLY_TEMP.get(month, 15.0) - (3.0 if is_night else 0.0), 1)
        wind_ms = round(_MONTHLY_WIND.get(month, 4.0), 1)
        if month in [12, 1, 2]:
            wind_dir, wind_deg = "NW", 315
        elif month in [6, 7, 8]:
            wind_dir, wind_deg = "SW", 225
        else:
            wind_dir, wind_deg = "W", 270
        humidity = 85 if is_fog else (75 if is_night else 65)
        condition = "안개" if is_fog else ("흐림" if humidity > 80 else "맑음")
        wx_source = "계절통계 (ASOS API 실패)"

    # ── 3중 취약 ─────────────────────────────────────────────────────
    triple = is_night and is_high_tide and is_fog
    dual_count = sum([is_night, is_high_tide, is_fog])

    return {
        "timestamp": now.isoformat(),
        "station": "군산 (140)",
        "data_source": f"조석수식 + {wx_source}",
        "weather": {
            "temperature_c":      temp_c,
            "humidity_pct":       humidity,
            "wind_speed_ms":      wind_ms,
            "wind_direction":     wind_dir,
            "wind_direction_deg": wind_deg,
            "visibility_km":      vis_km,
            "is_fog":             is_fog,
            "condition":          condition,
        },
        "tide": {
            "height_m":           tide_m,
            "height_cm":          tide_cm,
            "is_high_tide":       is_high_tide,
            "next_high_tide_in_h": next_high_h,
            "next_low_tide_in_h":  next_low_h,
            "tide_phase":         tide_phase,
        },
        "time": {
            "hour":    hour,
            "is_night": is_night,
            "period":  "야간" if is_night else "주간",
        },
        "triple_risk": {
            "active": triple,
            "components": {
                "night":     is_night,
                "high_tide": is_high_tide,
                "fog":       is_fog,
            },
            "level": (
                "위험" if triple else
                ("경계" if dual_count == 2 else
                 ("주의" if dual_count == 1 else "정상"))
            ),
        },
    }


def get_7day_forecast() -> list:
    """7일 환경 예측 (risk_calendar get_forecast 데이터 활용)"""
    from services.risk_calendar import get_forecast
    forecast_data = get_forecast(days=7)
    result = []
    now = datetime.now()

    for i, fc in enumerate(forecast_data):
        target = date.today() + timedelta(days=i)
        month = target.month
        stats = _seasonal_row(month)

        result.append({
            "date": fc["date"],
            "day_label": ["오늘", "내일", "모레"][i] if i < 3 else target.strftime("%m/%d"),
            "triple_risk_count": fc["predicted_triple_hours"],
            "risk_hours": [],
            "level": fc["risk_level"],
            "fog_prob_pct": fc["fog_prob_pct"],
            "high_tide_times": [],
            "risk_score": fc["risk_score"],
            "confidence_pct": fc["confidence_pct"],
        })

    return result
