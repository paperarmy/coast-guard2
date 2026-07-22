"""
기상청 ASOS 지상관측 API → 현재 시간 실측 기상 조회
군산 관측소 (stnId=140)

엔드포인트: GET /1360000/AsosHourlyInfoService/getWthrDataList
주요 반환 필드:
  tm: 관측 시각 (YYYYMMDD HH:mm)
  ta: 기온 (℃)
  wd: 풍향 (16방위)
  ws: 풍속 (m/s)
  hm: 상대습도 (%)
  vs: 시정 (m)
  rn: 강수량 (mm)
"""
import os
import json
import urllib.request
from datetime import datetime, timedelta

BASE_URL = "https://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
STN_ID   = "140"  # 군산

# 풍향 코드 → 문자 변환 (16방위)
_WD_MAP = {
    "N": "N", "NNE": "NNE", "NE": "NE", "ENE": "ENE",
    "E": "E", "ESE": "ESE", "SE": "SE", "SSE": "SSE",
    "S": "S", "SSW": "SSW", "SW": "SW", "WSW": "WSW",
    "W": "W", "WNW": "WNW", "NW": "NW", "NNW": "NNW",
    "정온": "CALM",
}


def _get_api_key() -> str | None:
    return os.getenv("DATA_GO_KR_KEY")


def _fetch_asos(date_str: str, hour_str: str) -> dict | None:
    """
    ASOS 지상관측 시간별 1건 조회.
    date_str: "YYYYMMDD", hour_str: "HH" (예: "14")
    """
    key = _get_api_key()
    if not key:
        return None

    params = (
        f"?serviceKey={key}"
        f"&pageNo=1&numOfRows=1&dataType=JSON"
        f"&dataCd=ASOS&dateCd=HR"
        f"&stnIds={STN_ID}"
        f"&startDt={date_str}&startHh={hour_str}"
        f"&endDt={date_str}&endHh={hour_str}"
    )
    try:
        with urllib.request.urlopen(BASE_URL + params, timeout=5) as resp:
            data = json.loads(resp.read())
        items = data["response"]["body"]["items"]["item"]
        if not items:
            return None
        return items[0]
    except Exception:
        return None


def get_current_weather() -> dict | None:
    """
    현재 시각 군산 실측 기상 반환.
    API 실패 시 None (호출부에서 seasonal fallback 적용).

    반환 구조:
      temperature_c, wind_speed_ms, wind_direction, wind_direction_deg,
      humidity_pct, visibility_km, is_fog, condition, data_source
    """
    now = datetime.now()
    # ASOS는 정각 관측 → 현재 시각 또는 1시간 전 데이터
    for delta in [0, 1]:
        target = now - timedelta(hours=delta)
        date_str = target.strftime("%Y%m%d")
        hour_str = target.strftime("%H")
        item = _fetch_asos(date_str, hour_str)
        if item:
            break
    else:
        return None

    def _f(key: str, fallback=None):
        try:
            v = item.get(key, "")
            return float(v) if v not in ("", None) else fallback
        except (ValueError, TypeError):
            return fallback

    temp_c   = _f("ta")
    wind_ms  = _f("ws", 3.0)
    humidity = _f("hm", 70.0)
    vis_m    = _f("vs")         # 시정 (m)
    rn_mm    = _f("rn", 0.0)    # 강수량

    # 풍향: ASOS는 16방위 문자열 반환
    wd_raw = item.get("wd", "W")
    wind_dir = _WD_MAP.get(wd_raw, "W")

    # 풍향 → 각도 변환
    _DEG = {"N":0,"NNE":22,"NE":45,"ENE":67,"E":90,"ESE":112,"SE":135,"SSE":157,
             "S":180,"SSW":202,"SW":225,"WSW":247,"W":270,"WNW":292,"NW":315,"NNW":337,"CALM":0}
    wind_deg = _DEG.get(wind_dir, 270)

    # 시정 판단
    if vis_m is not None:
        vis_km  = round(vis_m / 1000, 1)
        is_fog  = vis_m < 1000  # 기상학적 안개 기준: 1km 미만
    else:
        vis_km  = None
        is_fog  = humidity >= 90 and (now.hour >= 20 or now.hour < 6)

    # 날씨 상태
    if rn_mm and rn_mm > 0:
        condition = "비"
    elif is_fog:
        condition = "안개"
    elif humidity and humidity > 80:
        condition = "흐림"
    else:
        condition = "맑음"

    result = {
        "temperature_c":       round(temp_c, 1) if temp_c is not None else None,
        "wind_speed_ms":       round(wind_ms, 1),
        "wind_direction":      wind_dir,
        "wind_direction_deg":  wind_deg,
        "humidity_pct":        round(humidity),
        "visibility_km":       vis_km,
        "is_fog":              is_fog,
        "condition":           condition,
        "data_source":         f"기상청 ASOS 실측 (군산 {target.strftime('%H')}시)",
        "_obs_time":           target.strftime("%Y-%m-%d %H:00"),
    }
    return result
