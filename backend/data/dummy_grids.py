"""
격자 더미 데이터 — import 오류 시 fallback용
정상 경로: services/cvi_calculator.py (실 데이터)
"""
import random
from functools import lru_cache

REGIONS = {
    "군산": {"lat_range": (35.60, 35.95), "lon_range": (126.45, 126.75), "grid_count": 70, "risk_bias": 0.6,  "lisa_hh_ratio": 0.33},
    "부안": {"lat_range": (35.30, 35.60), "lon_range": (126.45, 126.75), "grid_count": 84, "risk_bias": 0.75, "lisa_hh_ratio": 0.43},
    "고창": {"lat_range": (35.00, 35.30), "lon_range": (126.45, 126.75), "grid_count": 56, "risk_bias": 0.35, "lisa_hh_ratio": 0.05},
}

ACTION_MAP = {
    "HH": ["TOD 기지 조정", "드론 거점 지정", "해경 야간 거점 연락", "AWS 경보 연동"],
    "LL": ["정기 순찰 유지"],
    "HL": ["CCTV 추가 설치 검토"],
    "LH": ["주민 신고 체계 강화"],
    "NS": ["현행 유지"],
}


def _level(cvi):
    if cvi >= 0.80: return "위험"
    if cvi >= 0.65: return "경계"
    if cvi >= 0.50: return "주의"
    return "정상"


def _color(cvi):
    if cvi >= 0.80: return "#dc2626"
    if cvi >= 0.65: return "#ea580c"
    if cvi >= 0.50: return "#ca8a04"
    return "#16a34a"


@lru_cache(maxsize=1)
def _build() -> list:
    rng = random.Random(42)  # 인스턴스 RNG — 전역 state 오염 없음
    grids = []
    gid = 1
    for region, cfg in REGIONS.items():
        lat_min, lat_max = cfg["lat_range"]
        lon_min, lon_max = cfg["lon_range"]
        bias = cfg["risk_bias"]
        hh_ratio = cfg["lisa_hh_ratio"]
        for _ in range(cfg["grid_count"]):
            lat = round(rng.uniform(lat_min, lat_max), 6)
            lon = round(rng.uniform(lon_min, lon_max), 6)
            coast_p = round(max(0, 1 - (lon - 126.40) / 0.45), 3)
            base_cvi = bias + rng.gauss(0, 0.18)
            cvi = round(max(0.10, min(1.0, base_cvi * (0.6 + coast_p * 0.4))), 3)
            night_a = round(rng.uniform(0.40, 0.70), 3)
            old_b   = round(rng.uniform(0.08, 0.20), 3)
            vessel  = round(rng.uniform(0.07, 0.18), 3)
            cctv_g  = round(rng.uniform(0.04, 0.10), 3)
            r = rng.random()
            lisa = ("HH" if r < hh_ratio else
                    "LL" if r < hh_ratio + 0.35 else
                    "NS" if r < hh_ratio + 0.50 else
                    "HL" if r < hh_ratio + 0.62 else "LH")
            has_drone = rng.random() < 0.15
            has_tod   = rng.random() < 0.20
            cctv_cnt  = rng.randint(0, 8) if rng.random() < 0.6 else 0
            grids.append({
                "grid_id":   f"G-{gid:03d}",
                "region":    region,
                "lat":       lat,
                "lon":       lon,
                "cvi":       cvi,
                "cvi_level": _level(cvi),
                "cvi_color": _color(cvi),
                "lisa":      lisa,
                "grid_type": ("Ⅰ형(이상활동형)" if night_a > 0.55 else
                              "Ⅱ형(감시공백형)" if cctv_cnt == 0 else
                              "혼합형" if lisa == "HH" else "저위험"),
                "shap": {"night_anomaly": night_a, "old_building": old_b,
                         "vessel_density": vessel, "cctv_gap": cctv_g,
                         "coast_proximity": max(0, round(1 - night_a - old_b - vessel - cctv_g, 3))},
                "assets": {"drone": has_drone, "tod": has_tod, "cctv_count": cctv_cnt},
                "recommended_actions": ACTION_MAP.get(lisa, ["현행 유지"]),
                "coast_proximity":    coast_p,
                "night_anomaly_index": night_a,
            })
            gid += 1
    return grids


def get_all_grids() -> list:
    return _build()

def get_grid_by_id(grid_id: str) -> dict | None:
    return next((g for g in _build() if g["grid_id"] == grid_id), None)

def get_top_grids(n: int = 10) -> list:
    return sorted(_build(), key=lambda x: -x["cvi"])[:n]

def get_hh_grids() -> list:
    return [g for g in _build() if g["lisa"] == "HH"]
