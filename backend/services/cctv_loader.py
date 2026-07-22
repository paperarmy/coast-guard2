"""
전북 CCTV 데이터 → 격자별 CCTV 수 매핑
data/cctv_jeonbuk.csv 가 없으면 빈 결과 반환 (fallback)
"""
import csv
import math
import os
from functools import lru_cache
from pathlib import Path

_HERE = Path(__file__).resolve()
CCTV_FILE = _HERE.parent.parent.parent / "data" / "cctv_jeonbuk.csv"
PROCESSED_CCTV = _HERE.parent.parent / "data" / "processed" / "cctv_grid_counts.csv"
GRID_RADIUS_KM = 1.5  # 3km×3km 격자의 내접원 반경

# 공공데이터포털 CCTV CSV 위·경도 컬럼 후보
_LAT_COLS = ["위도", "소재지위도", "lat", "latitude", "WGS84위도"]
_LON_COLS = ["경도", "소재지경도", "lon", "longitude", "WGS84경도"]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _find_col(header: list[str], candidates: list[str]) -> str | None:
    h_lower = [c.strip().lower() for c in header]
    for cand in candidates:
        if cand.lower() in h_lower:
            return header[h_lower.index(cand.lower())]
    return None


@lru_cache(maxsize=1)
def _load_cctv_points() -> list[tuple[float, float]]:
    if not CCTV_FILE.exists():
        return []

    points = []
    try:
        with open(CCTV_FILE, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames or []
            lat_col = _find_col(list(header), _LAT_COLS)
            lon_col = _find_col(list(header), _LON_COLS)
            if not lat_col or not lon_col:
                return []
            for row in reader:
                try:
                    lat = float(row[lat_col])
                    lon = float(row[lon_col])
                    # 전북 서해안 경계 필터 (느슨하게)
                    if 34.5 <= lat <= 36.5 and 125.5 <= lon <= 127.5:
                        points.append((lat, lon))
                except (ValueError, KeyError):
                    pass
    except Exception:
        return []

    return points


@lru_cache(maxsize=1)
def _load_processed_cctv() -> dict:
    """processed/cctv_grid_counts.csv 로드 (Vercel 배포 시 사용)."""
    if not PROCESSED_CCTV.exists():
        return {}
    try:
        with open(PROCESSED_CCTV, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return {row["grid_id"]: int(row["cctv_count"]) for row in reader}
    except Exception:
        return {}


def has_cctv_data() -> bool:
    return PROCESSED_CCTV.exists() or (CCTV_FILE.exists() and len(_load_cctv_points()) > 0)


def get_cctv_count_by_grid_id(grid_id: str) -> int:
    """processed CSV에서 격자 ID로 직접 조회 (빠름, Vercel 배포용)."""
    processed = _load_processed_cctv()
    return processed.get(grid_id, -1)  # -1 = 데이터 없음


def get_cctv_count(grid_lat: float, grid_lon: float, radius_km: float = GRID_RADIUS_KM) -> int:
    points = _load_cctv_points()
    if not points:
        return -1  # -1 = 데이터 없음 (fallback 신호)
    return sum(
        1 for lat, lon in points
        if _haversine_km(grid_lat, grid_lon, lat, lon) <= radius_km
    )
