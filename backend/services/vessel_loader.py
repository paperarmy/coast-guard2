"""
MDIS 농림어업총조사(어업) > 해수면-어선현황 → 격자별 어선 밀도 산출
data/2020_해수면-어선현황_*.csv 기반

MDIS 코드 체계 (실측 확인):
  시도코드 35 = 전라북도
  시군구코드 020 = 군산시 (456척)
  시군구코드 380 = 부안군 (409척)
  시군구코드 370 = 고창군  (75척)
"""
import csv
import glob
import os
from functools import lru_cache
from pathlib import Path

_HERE = Path(__file__).resolve()
DATA_DIR = _HERE.parent.parent.parent / "data"
PROCESSED_VESSEL = _HERE.parent.parent / "data" / "processed" / "vessel_summary.csv"

# MDIS 시군구 코드 → 지역명 매핑 (실측 확인 값)
SIGUN_MAP = {
    ("35", "020"): "군산",
    ("35", "380"): "부안",
    ("35", "370"): "고창",
}

# CGIP 격자 수 (cvi_calculator.py와 동일)
REGION_GRID_COUNT = {"군산": 70, "부안": 84, "고창": 56}

# 어선 수 → vessel_density 정규화 기준 (격자당 최대 어선 수)
NORMALIZE_MAX = 15.0


def _find_mdis_files() -> list[Path]:
    pattern = str(DATA_DIR / "*해수면-어선현황*.csv")
    files = glob.glob(pattern)
    # 최신 연도 우선 (2020 > 2015)
    return sorted(files, reverse=True)


@lru_cache(maxsize=1)
def _load_processed_vessel() -> dict:
    """processed/vessel_summary.csv 로드 (Vercel 배포 시 사용)."""
    if not PROCESSED_VESSEL.exists():
        return {}
    try:
        with open(PROCESSED_VESSEL, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return {row["region"]: int(row["vessel_count"]) for row in reader}
    except Exception:
        return {}


@lru_cache(maxsize=1)
def _count_vessels_by_region() -> dict:
    """지역별 총 어선 척수 반환. processed CSV 우선, 없으면 MDIS 원본 파일."""
    processed = _load_processed_vessel()
    if processed:
        return processed

    files = _find_mdis_files()
    if not files:
        return {}

    target_file = files[0]  # 가장 최신 파일
    counts: dict[str, int] = {"군산": 0, "부안": 0, "고창": 0}

    try:
        with open(target_file, encoding="euc-kr") as f:
            reader = csv.reader(f)
            next(reader, None)  # 헤더 스킵
            for row in reader:
                if len(row) < 3:
                    continue
                key = (row[0].strip('"'), row[1].strip('"'))
                region = SIGUN_MAP.get(key)
                if region:
                    counts[region] += 1
    except UnicodeDecodeError:
        # utf-8-sig 재시도
        try:
            with open(target_file, encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) < 3:
                        continue
                    key = (row[0].strip('"'), row[1].strip('"'))
                    region = SIGUN_MAP.get(key)
                    if region:
                        counts[region] += 1
        except Exception:
            return {}
    except Exception:
        return {}

    return counts


def has_vessel_data() -> bool:
    return bool(_find_mdis_files()) and bool(_count_vessels_by_region())


def get_vessel_density(grid_lat: float, grid_lon: float, region: str, coast_proximity: float) -> float:
    """
    CGIP 격자의 vessel_density 반환 (0~1 범위).
    지역별 어선 수를 격자 수로 나눠 격자당 평균 어선 수를 구한 뒤,
    해안 근접도로 가중해 정규화.
    """
    counts = _count_vessels_by_region()
    if not counts or region not in counts:
        return -1.0  # -1 = 데이터 없음 (fallback 신호)

    total_in_region = counts[region]
    grid_count = REGION_GRID_COUNT.get(region, 70)

    # 격자당 평균 어선 수 × 해안 근접도 가중 (해안일수록 어선 더 많음)
    avg_per_grid = total_in_region / grid_count
    weighted = avg_per_grid * (0.5 + coast_proximity * 1.0)

    return round(min(1.0, weighted / NORMALIZE_MAX), 4)


def get_region_summary() -> dict:
    """수집 현황 요약 (디버그용)"""
    counts = _count_vessels_by_region()
    files = _find_mdis_files()
    return {
        "source_file": os.path.basename(files[0]) if files else None,
        "vessel_counts": counts,
        "has_data": bool(counts),
    }
