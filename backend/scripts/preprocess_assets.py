"""
원본 데이터 → backend/data/processed/ 전처리 스크립트
Vercel 배포 시 raw data 폴더에 접근 불가하므로 processed/ 에 미리 저장.

생성 파일:
  processed/cctv_grid_counts.csv  - 격자별 CCTV 수 (210행)
  processed/vessel_summary.csv    - 지역별 어선 척수 (3행)

실행: python backend/scripts/preprocess_assets.py
"""
import sys
import os
import csv
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PROCESSED = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

# ── 격자 위치 생성 (cvi_calculator.py와 동일 seed/순서 필수) ──────────
REGIONS = {
    "군산": {"lat_range": (35.60, 35.95), "lon_range": (126.45, 126.75), "grid_count": 70},
    "부안": {"lat_range": (35.30, 35.60), "lon_range": (126.45, 126.75), "grid_count": 84},
    "고창": {"lat_range": (35.00, 35.30), "lon_range": (126.45, 126.75), "grid_count": 56},
}

def _generate_grid_positions():
    rng = random.Random(42)
    grids = []
    gid = 1
    for region, cfg in REGIONS.items():
        lat_min, lat_max = cfg["lat_range"]
        lon_min, lon_max = cfg["lon_range"]
        for _ in range(cfg["grid_count"]):
            lat = round(rng.uniform(lat_min, lat_max), 6)
            lon = round(rng.uniform(lon_min, lon_max), 6)
            # dummy RNG 소비 (cvi_calculator 순서 유지)
            rng.gauss(0, 0.18)
            rng.uniform(0.40, 0.70)
            rng.uniform(0.08, 0.20)
            rng.uniform(0.07, 0.18)
            rng.uniform(0.04, 0.10)
            rng.random()
            rng.random()
            rng.random()
            rng.random()
            rng.randint(0, 8)
            grids.append({"grid_id": f"G-{gid:03d}", "region": region, "lat": lat, "lon": lon})
            gid += 1
    return grids


# ── 1) CCTV 격자별 수 전처리 ─────────────────────────────────────────
def preprocess_cctv():
    from services.cctv_loader import _load_cctv_points, GRID_RADIUS_KM, CCTV_FILE
    import math

    if not CCTV_FILE.exists():
        print("  [SKIP] cctv_jeonbuk.csv 없음")
        return

    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    points = _load_cctv_points()
    grids = _generate_grid_positions()

    out = os.path.join(PROCESSED, "cctv_grid_counts.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["grid_id", "cctv_count"])
        for i, g in enumerate(grids):
            cnt = sum(1 for lat, lon in points if haversine(g["lat"], g["lon"], lat, lon) <= GRID_RADIUS_KM)
            writer.writerow([g["grid_id"], cnt])
            if (i + 1) % 50 == 0:
                print(f"  CCTV 처리: {i+1}/210", end="\r")

    print(f"\n  저장: {out}")


# ── 2) 어선 지역별 집계 전처리 ──────────────────────────────────────
def preprocess_vessel():
    from services.vessel_loader import _count_vessels_by_region, _find_mdis_files

    files = _find_mdis_files()
    if not files:
        print("  [SKIP] MDIS 어선 파일 없음")
        return

    counts = _count_vessels_by_region()
    out = os.path.join(PROCESSED, "vessel_summary.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["region", "vessel_count", "source_year"])
        year = "2020" if "2020" in os.path.basename(files[0]) else "2015"
        for region, cnt in counts.items():
            writer.writerow([region, cnt, year])

    print(f"  저장: {out}")
    print(f"  집계: {counts}")


if __name__ == "__main__":
    print("=== CCTV 격자별 수 전처리 ===")
    preprocess_cctv()
    print("\n=== 어선 지역별 집계 전처리 ===")
    preprocess_vessel()
    print("\n완료. backend/data/processed/ 파일을 git commit하면 Vercel에서 사용 가능합니다.")
