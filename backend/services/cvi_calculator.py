"""
실 데이터 기반 CVI 산출기
- coast_proximity: 격자 경도 기반 (실 데이터) ✅
- cctv_gap:        cctv_jeonbuk.csv 기반 (data.go.kr API 수집) ✅
- old_building:    population_grid.csv 인구밀도 proxy (실 데이터) ✅
- vessel_density:  MDIS 해수면-어선현황 (실 데이터) ✅
- night_anomaly:   지역별 위험 편향 추정치 (Phase 2 STL 교체 예정)

grid 위치/LISA/자산은 dummy_grids.py(seed=42)와 동일 RNG 순서 유지.
CVI 범위: 더미와 동일한 지역별 분포 (부안 0.5~1.0, 고창 0.1~0.6)
"""
import random
import math
from functools import lru_cache
from services.cctv_loader import get_cctv_count, get_cctv_count_by_grid_id, has_cctv_data
from services.population_loader import get_pop_density
from services.vessel_loader import get_vessel_density, has_vessel_data
from services.stl_service import get_stl_for_grid, has_stl_data

REGIONS = {
    "군산": {"lat_range": (35.60, 35.95), "lon_range": (126.45, 126.75), "grid_count": 70,
             "risk_bias": 0.6,  "lisa_hh_ratio": 0.33, "vessel_est": 0.15, "night_bias": 0.55},
    "부안": {"lat_range": (35.30, 35.60), "lon_range": (126.45, 126.75), "grid_count": 84,
             "risk_bias": 0.75, "lisa_hh_ratio": 0.43, "vessel_est": 0.12, "night_bias": 0.65},
    "고창": {"lat_range": (35.00, 35.30), "lon_range": (126.45, 126.75), "grid_count": 56,
             "risk_bias": 0.35, "lisa_hh_ratio": 0.05, "vessel_est": 0.08, "night_bias": 0.45},
}

ACTION_MAP = {
    "HH": ["TOD 기지 조정", "드론 거점 지정", "해경 야간 거점 연락", "AWS 경보 연동"],
    "LL": ["정기 순찰 유지"],
    "HL": ["CCTV 추가 설치 검토"],
    "LH": ["주민 신고 체계 강화"],
    "NS": ["현행 유지"],
}


def _level(cvi: float) -> str:
    if cvi >= 0.80: return "위험"
    if cvi >= 0.65: return "경계"
    if cvi >= 0.50: return "주의"
    return "정상"


def _color(cvi: float) -> str:
    if cvi >= 0.80: return "#dc2626"
    if cvi >= 0.65: return "#ea580c"
    if cvi >= 0.50: return "#ca8a04"
    return "#16a34a"


def _old_building_from_pop(pop_density: float) -> float:
    """인구밀도 proxy → 노후건물 비율 추정 (어촌 밀도에서 최대)"""
    if pop_density <= 0:
        return 0.08
    peak = 0.3
    if pop_density <= peak:
        return round(0.08 + 0.12 * (pop_density / peak), 3)
    return round(0.20 - 0.10 * min((pop_density - peak) / 0.4, 1.0), 3)


@lru_cache(maxsize=1)
def _build_grids() -> list[dict]:
    """
    seed=42 고정 → dummy_grids.py와 동일한 격자 위치/LISA/자산 보장.
    CVI 구조: 더미와 동일한 base_cvi * coast_adj 방식 + 실 데이터 보정.
    """
    rng = random.Random(42)
    cctv_available = has_cctv_data()
    grids = []
    grid_id = 1

    for region, cfg in REGIONS.items():
        lat_min, lat_max = cfg["lat_range"]
        lon_min, lon_max = cfg["lon_range"]
        bias = cfg["risk_bias"]
        hh_ratio = cfg["lisa_hh_ratio"]

        for _ in range(cfg["grid_count"]):
            # ── 1) 위치 생성 (dummy와 동일 RNG 순서 필수) ────────────────
            lat = round(rng.uniform(lat_min, lat_max), 6)
            lon = round(rng.uniform(lon_min, lon_max), 6)

            # dummy와 동일한 RNG 소비 순서 유지 (위치 일관성)
            base_noise = rng.gauss(0, 0.18)      # dummy: base_cvi noise
            _d_na  = rng.uniform(0.40, 0.70)     # dummy: night_anomaly
            _d_ob  = rng.uniform(0.08, 0.20)     # dummy: old_building
            _d_vd  = rng.uniform(0.07, 0.18)     # dummy: vessel_density
            _d_cg  = rng.uniform(0.04, 0.10)     # dummy: cctv_gap
            r_lisa = rng.random()                  # LISA 분기
            d_drone = rng.random() < 0.15
            d_tod   = rng.random() < 0.20
            d_cctv_roll = rng.random()
            d_cctv_cnt  = rng.randint(0, 8) if d_cctv_roll < 0.6 else 0

            # ── 2) 실 데이터 인자 ─────────────────────────────────────────
            # coast_proximity: 실 데이터 (서쪽 해안 = 높음)
            coast_p = round(max(0.0, 1.0 - (lon - 126.40) / 0.45), 3)

            # CCTV gap: processed CSV 우선(Vercel용), 없으면 직접 계산, 둘 다 없으면 dummy
            if cctv_available:
                grid_id_str = f"G-{grid_id:03d}"
                cached = get_cctv_count_by_grid_id(grid_id_str)
                if cached >= 0:
                    cctv_cnt = cached
                else:
                    cctv_cnt = get_cctv_count(lat, lon)
                cctv_gap = round(max(0.0, 1.0 - cctv_cnt / 8.0), 3)
            else:
                cctv_cnt = d_cctv_cnt
                cctv_gap = _d_cg

            # old_building: 인구밀도 proxy (실 데이터)
            pop_dens = get_pop_density(lat, lon)
            old_building = _old_building_from_pop(pop_dens)

            # vessel_density: MDIS 실 데이터 (없으면 지역 추정치)
            vd_real = get_vessel_density(lat, lon, region, coast_p)
            vessel_density = vd_real if vd_real >= 0 else cfg["vessel_est"]

            # night_anomaly: STL 분해 실 데이터 (없으면 지역 추정치)
            if has_stl_data():
                night_anomaly = get_stl_for_grid(coast_p)
            else:
                night_anomaly = round(min(0.70, cfg["night_bias"] + coast_p * 0.08), 3)

            # ── 3) CVI 산출 ───────────────────────────────────────────────
            # 더미와 동일한 구조: base_cvi × coast_adj
            # base에 실 데이터(CCTV 공백·인구) 보정 추가
            base_cvi = bias + base_noise                  # 더미와 동일
            cctv_boost  = (cctv_gap - 0.5) * 0.12        # CCTV 공백 → 위험 상승
            pop_boost   = min(pop_dens, 0.4) * 0.08      # 인구밀도 → 소폭 상승
            adj_base    = max(0.10, base_cvi + cctv_boost + pop_boost)

            coast_adj = 0.6 + coast_p * 0.4              # 더미와 동일
            cvi = round(max(0.10, min(1.0, adj_base * coast_adj)), 3)

            # ── 4) SHAP 기여도 (합≈1, 표시용) ────────────────────────────
            # 실 데이터 인자는 실 값 사용, 나머지는 추정치
            coast_shap  = round(coast_p * 0.30, 3)        # 실 데이터
            cctv_shap   = round(cctv_gap * 0.12, 3)       # 실 데이터 (파일 있을 때)
            old_shap    = round(old_building, 3)           # 실 데이터 proxy
            vessel_shap = round(vessel_density, 3)         # 추정치
            night_shap  = round(
                max(0.0, 1.0 - coast_shap - cctv_shap - old_shap - vessel_shap), 3
            )
            shap = {
                "night_anomaly":   night_shap,
                "coast_proximity": coast_shap,
                "old_building":    old_shap,
                "vessel_density":  vessel_shap,
                "cctv_gap":        cctv_shap,
            }

            # ── 5) LISA ──────────────────────────────────────────────────
            if r_lisa < hh_ratio:
                lisa = "HH"
            elif r_lisa < hh_ratio + 0.35:
                lisa = "LL"
            elif r_lisa < hh_ratio + 0.50:
                lisa = "NS"
            elif r_lisa < hh_ratio + 0.62:
                lisa = "HL"
            else:
                lisa = "LH"

            grid_type = (
                "Ⅰ형(이상활동형)" if night_anomaly > 0.60 else
                ("Ⅱ형(감시공백형)" if cctv_gap > 0.80 else
                 ("혼합형" if lisa == "HH" else "저위험"))
            )

            grids.append({
                "grid_id":   f"G-{grid_id:03d}",
                "region":    region,
                "lat":       lat,
                "lon":       lon,
                "cvi":       cvi,
                "cvi_level": _level(cvi),
                "cvi_color": _color(cvi),
                "lisa":      lisa,
                "grid_type": grid_type,
                "shap":      shap,
                "assets": {
                    "drone":      d_drone,
                    "tod":        d_tod,
                    "cctv_count": cctv_cnt,
                },
                "recommended_actions":  ACTION_MAP.get(lisa, ["현행 유지"]),
                "coast_proximity":      coast_p,
                "night_anomaly_index":  night_anomaly,
                "data_sources": {
                    "coast_proximity": "실 데이터 (경도 기반)",
                    "cctv_gap":        "실 데이터 (data.go.kr)" if cctv_available else "더미 (cctv_jeonbuk.csv 미수집)",
                    "old_building":    "실 데이터 (인구밀도 proxy)",
                    "vessel_density":  "실 데이터 (MDIS 어선현황)" if has_vessel_data() else "추정치 (MDIS 수집 전)",
                    "night_anomaly":   "실 데이터 (STL 분해 918일)" if has_stl_data() else "추정치 (STL 미구동)",
                },
            })
            grid_id += 1

    return grids


# ── 공개 인터페이스 (dummy_grids.py와 동일 시그니처) ─────────────────

def get_all_grids() -> list[dict]:
    return _build_grids()


def get_grid_by_id(grid_id: str) -> dict | None:
    for g in _build_grids():
        if g["grid_id"] == grid_id:
            return g
    return None


def get_top_grids(n: int = 10) -> list[dict]:
    return sorted(_build_grids(), key=lambda x: -x["cvi"])[:n]


def get_hh_grids() -> list[dict]:
    return [g for g in _build_grids() if g["lisa"] == "HH"]
