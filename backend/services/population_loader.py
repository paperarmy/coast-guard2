"""
SGIS 500m 인구격자 → CGIP 격자별 인구밀도 조회
processed/population_grid.csv 기반 공간 매핑
"""
import math
import csv
from functools import lru_cache
from pathlib import Path

POPULATION_FILE = Path(__file__).resolve().parent.parent / "data" / "processed" / "population_grid.csv"
LOOKUP_RADIUS_KM = 2.0  # CGIP 격자(3km) 대비 SGIS 격자(0.5km) 집계 반경


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@lru_cache(maxsize=1)
def _load_sgis() -> list[dict]:
    rows = []
    with open(POPULATION_FILE, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                rows.append({
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "pop_density_norm": float(row["pop_density_norm"]),
                    "population": float(row["population"]),
                })
            except (ValueError, KeyError):
                pass
    return rows


def get_pop_density(grid_lat: float, grid_lon: float) -> float:
    """CGIP 격자 중심으로부터 LOOKUP_RADIUS_KM 이내 SGIS 격자 중 최대 pop_density_norm 반환 (0~1)"""
    sgis = _load_sgis()
    nearby = [
        r["pop_density_norm"] for r in sgis
        if _haversine_km(grid_lat, grid_lon, r["lat"], r["lon"]) <= LOOKUP_RADIUS_KM
    ]
    return max(nearby) if nearby else 0.0


def get_total_population(grid_lat: float, grid_lon: float) -> int:
    """격자 반경 내 총 인구 합계"""
    sgis = _load_sgis()
    total = sum(
        r["population"] for r in sgis
        if _haversine_km(grid_lat, grid_lon, r["lat"], r["lon"]) <= LOOKUP_RADIUS_KM
    )
    return int(total)
