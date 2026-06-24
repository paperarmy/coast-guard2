"""
전북 서해안 210개 격자 더미 데이터 생성기
실제 데이터(SGIS, KHOA, CCTV) 수신 전 구현 검증용
격자 범위: 군산(35.9~35.6°N) / 부안(35.6~35.3°N) / 고창(35.3~35.0°N)
해안선 기준 3km x 3km 격자
"""
import random
import math
from typing import List, Dict

random.seed(42)

# 전북 서해안 3개 시군 격자 중심점 범위
REGIONS = {
    "군산": {
        "lat_range": (35.60, 35.95),
        "lon_range": (126.45, 126.75),
        "grid_count": 70,
        "risk_bias": 0.6,   # 어선 밀집 → 중간-높은 위험
        "lisa_hh_ratio": 0.33,
    },
    "부안": {
        "lat_range": (35.30, 35.60),
        "lon_range": (126.45, 126.75),
        "grid_count": 84,
        "risk_bias": 0.75,  # 최고 위험 (HH 핫스팟 집중)
        "lisa_hh_ratio": 0.43,
    },
    "고창": {
        "lat_range": (35.00, 35.30),
        "lon_range": (126.45, 126.75),
        "grid_count": 56,
        "risk_bias": 0.35,  # 냉스팟 (LL 집중)
        "lisa_hh_ratio": 0.05,
    },
}

LISA_TYPES = ["HH", "LL", "HL", "LH", "NS"]
GRID_TYPES = ["Ⅰ형(이상활동형)", "Ⅱ형(감시공백형)", "혼합형", "저위험"]
ACTION_MAP = {
    "HH": ["TOD 기지 조정", "드론 거점 지정", "해경 야간 거점 연락", "AWS 경보 연동"],
    "LL": ["정기 순찰 유지"],
    "HL": ["CCTV 추가 설치 검토"],
    "LH": ["주민 신고 체계 강화"],
    "NS": ["현행 유지"],
}


def _cvi_to_level(cvi: float) -> str:
    if cvi >= 0.80: return "위험"
    if cvi >= 0.65: return "경계"
    if cvi >= 0.50: return "주의"
    return "정상"


def _cvi_to_color(cvi: float) -> str:
    if cvi >= 0.80: return "#dc2626"
    if cvi >= 0.65: return "#ea580c"
    if cvi >= 0.50: return "#ca8a04"
    return "#16a34a"


def generate_grids() -> List[Dict]:
    grids = []
    grid_id = 1

    for region, cfg in REGIONS.items():
        lat_min, lat_max = cfg["lat_range"]
        lon_min, lon_max = cfg["lon_range"]
        count = cfg["grid_count"]
        bias = cfg["risk_bias"]
        hh_ratio = cfg["lisa_hh_ratio"]

        for i in range(count):
            lat = round(random.uniform(lat_min, lat_max), 6)
            lon = round(random.uniform(lon_min, lon_max), 6)

            # 해안 근접도 (서쪽일수록 높음)
            coast_proximity = round(max(0, 1 - (lon - 126.40) / 0.45), 3)

            # CVI 생성 (지역 편향 + 정규분포 노이즈)
            base_cvi = bias + random.gauss(0, 0.18)
            cvi = round(max(0.10, min(1.05, base_cvi * (0.6 + coast_proximity * 0.4))), 3)

            # SHAP 기여도 (합계 ≈ 1)
            night_anomaly = round(random.uniform(0.40, 0.70), 3)
            old_building = round(random.uniform(0.08, 0.20), 3)
            vessel_density = round(random.uniform(0.07, 0.18), 3)
            cctv_gap = round(random.uniform(0.04, 0.10), 3)
            coast_score = round(1 - night_anomaly - old_building - vessel_density - cctv_gap, 3)

            # LISA 유형
            r = random.random()
            if r < hh_ratio:
                lisa = "HH"
            elif r < hh_ratio + 0.35:
                lisa = "LL"
            elif r < hh_ratio + 0.50:
                lisa = "NS"
            elif r < hh_ratio + 0.62:
                lisa = "HL"
            else:
                lisa = "LH"

            # 감시 자산 현황
            has_drone = random.random() < 0.15
            has_tod = random.random() < 0.20
            cctv_count = random.randint(0, 8) if random.random() < 0.6 else 0

            grid_type = "Ⅰ형(이상활동형)" if night_anomaly > 0.55 else (
                "Ⅱ형(감시공백형)" if cctv_count == 0 else (
                    "혼합형" if lisa == "HH" else "저위험"
                )
            )

            grids.append({
                "grid_id": f"G-{grid_id:03d}",
                "region": region,
                "lat": lat,
                "lon": lon,
                "cvi": cvi,
                "cvi_level": _cvi_to_level(cvi),
                "cvi_color": _cvi_to_color(cvi),
                "lisa": lisa,
                "grid_type": grid_type,
                "shap": {
                    "night_anomaly": night_anomaly,
                    "old_building": old_building,
                    "vessel_density": vessel_density,
                    "cctv_gap": cctv_gap,
                    "coast_proximity": max(0, coast_score),
                },
                "assets": {
                    "drone": has_drone,
                    "tod": has_tod,
                    "cctv_count": cctv_count,
                },
                "recommended_actions": ACTION_MAP.get(lisa, ["현행 유지"]),
                "coast_proximity": coast_proximity,
                "night_anomaly_index": night_anomaly,
                "cctv_gap_score": cctv_gap,
            })
            grid_id += 1

    # CVI 내림차순 정렬
    grids.sort(key=lambda x: x["cvi"], reverse=True)

    # 순위 부여
    for rank, g in enumerate(grids, 1):
        g["rank"] = rank
        g["rank_pct"] = round(rank / len(grids) * 100, 1)

    return grids


GRIDS = generate_grids()


def get_all_grids() -> List[Dict]:
    return GRIDS


def get_grid_by_id(grid_id: str) -> Dict | None:
    return next((g for g in GRIDS if g["grid_id"] == grid_id), None)


def get_top_grids(n: int = 10) -> List[Dict]:
    return GRIDS[:n]


def get_hh_grids() -> List[Dict]:
    return [g for g in GRIDS if g["lisa"] == "HH"]
