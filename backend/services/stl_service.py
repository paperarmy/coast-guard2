"""
STL 분해 결과 기반 night_anomaly_index 서비스
processed/night_anomaly_monthly.csv, night_anomaly_daily.csv 에서 읽음

night_anomaly_index: STL 잔차의 월별 평균 (0~1 정규화)
  - 12월(1.0), 11월(0.97), 1~2월(0.83) — 동절기 야간 안개 집중
  - 9월(0.0), 6월(0.13) — 하절기 낮은 이상 지수
"""
import csv
from datetime import datetime, date
from functools import lru_cache
from pathlib import Path

_HERE = Path(__file__).resolve()
_PROCESSED = _HERE.parent.parent / "data" / "processed"

MONTHLY_CSV = _PROCESSED / "night_anomaly_monthly.csv"
DAILY_CSV   = _PROCESSED / "night_anomaly_daily.csv"

# fallback: STL 이전 더미값 (Phase 1 추정치)
_FALLBACK = {m: 0.5 for m in range(1, 13)}


@lru_cache(maxsize=1)
def _load_monthly() -> dict:
    if not MONTHLY_CSV.exists():
        return {}
    try:
        with open(MONTHLY_CSV, encoding="utf-8-sig") as f:
            return {int(r["month"]): float(r["anomaly_index"]) for r in csv.DictReader(f)}
    except Exception:
        return {}


@lru_cache(maxsize=1)
def _load_daily() -> dict:
    """일별 STL 결과. 이상탐지 탭에서 격자 시계열 표시용."""
    if not DAILY_CSV.exists():
        return {}
    try:
        with open(DAILY_CSV, encoding="utf-8-sig") as f:
            return {r["date"]: {
                "night_risk": float(r["night_risk"]),
                "trend":      float(r["trend"]),
                "seasonal":   float(r["seasonal"]),
                "residual":   float(r["residual"]),
            } for r in csv.DictReader(f)}
    except Exception:
        return {}


def has_stl_data() -> bool:
    return MONTHLY_CSV.exists()


def get_night_anomaly(month: int | None = None) -> float:
    """
    월별 야간 이상지수 반환 (0~1).
    month 미지정 시 현재 달 사용.
    """
    if month is None:
        month = datetime.now().month
    monthly = _load_monthly()
    return monthly.get(month, _FALLBACK.get(month, 0.5))


def get_monthly_table() -> list[dict]:
    """12개월 전체 anomaly 테이블 (API 응답용)."""
    monthly = _load_monthly() or _FALLBACK
    labels = {1:"1월",2:"2월",3:"3월",4:"4월",5:"5월",6:"6월",
              7:"7월",8:"8월",9:"9월",10:"10월",11:"11월",12:"12월"}
    return [{"month": m, "label": labels[m], "anomaly_index": monthly.get(m, 0.5)}
            for m in range(1, 13)]


def get_daily_timeseries(days: int = 90) -> list[dict]:
    """최근 N일 STL 시계열 (이상탐지 탭 차트용)."""
    daily = _load_daily()
    dates = sorted(daily.keys())[-days:]
    return [{"date": d, **daily[d]} for d in dates]


def get_stl_for_grid(coast_proximity: float, month: int | None = None) -> float:
    """
    격자별 night_anomaly_index 산출.
    해안 근접도가 높을수록 야간 이상에 더 민감.
    """
    base = get_night_anomaly(month)
    # 해안 근접 격자는 안개·조석 영향 더 강함 → 최대 20% 상향
    return round(min(1.0, base * (0.85 + coast_proximity * 0.30)), 3)
