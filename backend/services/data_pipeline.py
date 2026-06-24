"""
실 데이터 전처리 파이프라인
실행: python -m services.data_pipeline
출력: backend/data/processed/ 폴더에 CSV 생성
"""
import sys, os, glob
import pandas as pd
import numpy as np
import geopandas as gpd
from pathlib import Path

DATA_SRC = Path("C:/Users/육군35사단-PC15/Desktop/클로드/data")
OUT_DIR  = Path(__file__).parent.parent / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────
# 1. 조위 데이터 처리 (KHOA TXT → CSV)
# ────────────────────────────────────────────
def process_tide():
    files = sorted(glob.glob(str(DATA_SRC / "군산_*.txt")))
    records = []
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fp:
            for line in fp:
                parts = line.strip().split()
                if len(parts) == 3:
                    try:
                        dt  = pd.to_datetime(parts[0] + " " + parts[1], format="%Y/%m/%d %H:%M")
                        val = int(parts[2])
                        records.append({"dt": dt, "tide_cm": val})
                    except:
                        pass

    df = pd.DataFrame(records).drop_duplicates("dt").sort_values("dt").reset_index(drop=True)
    # 만조 판단: 500cm 이상 (군산항 최대 790cm 기준, 상위 ~28% 시간대)
    df["is_high_tide"] = df["tide_cm"] >= 500
    df.to_csv(OUT_DIR / "tide_hourly.csv", index=False)
    print(f"[조위] {len(df)}행 저장 | 범위: {df.dt.min()} ~ {df.dt.max()}")
    print(f"       만조(≥500cm): {df.is_high_tide.sum()}시간 ({df.is_high_tide.mean()*100:.1f}%)")
    return df


# ────────────────────────────────────────────
# 2. 기상 데이터 처리 (ASOS CSV → CSV)
# ────────────────────────────────────────────
def process_weather():
    files = [
        DATA_SRC / "weather_gunsan_2023.csv",
        DATA_SRC / "weather_gunsan_2023_2025.csv",
    ]
    dfs = []
    for f in files:
        if f.exists():
            dfs.append(pd.read_csv(f, encoding="utf-8-sig"))

    df = pd.concat(dfs).drop_duplicates("tm").copy()
    df["dt"] = pd.to_datetime(df["tm"])
    df = df.sort_values("dt").reset_index(drop=True)

    # 시정(vs): m 단위. 1000m 미만 = 안개
    df["vs_m"] = pd.to_numeric(df["vs"], errors="coerce")
    df["is_fog"] = df["vs_m"] < 1000

    # 야간: 20시 이후 ~ 06시 미만
    df["hour"] = df["dt"].dt.hour
    df["is_night"] = (df["hour"] >= 20) | (df["hour"] < 6)

    df[["dt", "vs_m", "is_fog", "is_night", "hour"]].to_csv(
        OUT_DIR / "weather_hourly.csv", index=False
    )
    print(f"[기상] {len(df)}행 저장 | 범위: {df.dt.min()} ~ {df.dt.max()}")
    print(f"       안개(vs<1000m): {df.is_fog.sum()}시간 ({df.is_fog.mean()*100:.1f}%)")
    return df[["dt", "vs_m", "is_fog", "is_night", "hour"]]


# ────────────────────────────────────────────
# 3. 인구 격자 처리 (SGIS SHP + CSV)
# ────────────────────────────────────────────
def process_population():
    # 나마(군산 인근) + 다마(전라북도) 500M 격자 합치기
    gdfs = []
    for prefix in ["나마", "다마"]:
        shp = DATA_SRC / f"grid_{prefix}_500M.shp"
        if shp.exists():
            g = gpd.read_file(str(shp))
            g = g.to_crs(epsg=4326)
            # centroid 계산 (투영좌표계에서 먼저)
            g_proj = gpd.read_file(str(shp))
            g["lat"] = g_proj.geometry.centroid.to_crs(epsg=4326).y
            g["lon"] = g_proj.geometry.centroid.to_crs(epsg=4326).x
            gdfs.append(g[["GRID_CD", "lat", "lon"]])

    grid_df = pd.concat(gdfs).drop_duplicates("GRID_CD").reset_index(drop=True)

    # 인구 CSV 합치기
    pop_dfs = []
    for prefix in ["나마", "다마"]:
        csv = DATA_SRC / f"2024년_인구_{prefix}_500M.csv"
        if csv.exists():
            d = pd.read_csv(csv, encoding="cp949", header=None,
                            names=["year", "GRID_CD", "var_cd", "value"])
            pop_dfs.append(d)

    pop = pd.concat(pop_dfs).drop_duplicates(["GRID_CD", "var_cd"])
    # 총인구만 사용 (to_in_001)
    total_pop = pop[pop["var_cd"] == "to_in_001"][["GRID_CD", "value"]].rename(
        columns={"value": "population"}
    )

    result = grid_df.merge(total_pop, on="GRID_CD", how="left")
    result["population"] = result["population"].fillna(0).astype(int)

    # 해안 근접 필터 (서해안: 경도 126.7 이하)
    coastal = result[result["lon"] <= 126.75].copy()
    # 전북 서해안 위도 범위 (34.9~36.2)
    coastal = coastal[(coastal["lat"] >= 34.9) & (coastal["lat"] <= 36.2)]

    # 인구밀도 정규화 (0~1)
    max_pop = coastal["population"].max() if coastal["population"].max() > 0 else 1
    coastal["pop_density_norm"] = coastal["population"] / max_pop

    coastal.to_csv(OUT_DIR / "population_grid.csv", index=False)
    print(f"[인구] 전체:{len(result)} → 해안:{len(coastal)}개 격자 저장")
    return coastal


# ────────────────────────────────────────────
# 4. 일별 위험 점수 계산 (3중 취약 지수)
# ────────────────────────────────────────────
def compute_daily_risk(tide_df=None, weather_df=None):
    if tide_df is None:
        tide_df = pd.read_csv(OUT_DIR / "tide_hourly.csv", parse_dates=["dt"])
    if weather_df is None:
        weather_df = pd.read_csv(OUT_DIR / "weather_hourly.csv", parse_dates=["dt"])

    # 시간 단위 병합 (조위 + 기상)
    tide_df["dt_h"] = tide_df["dt"].dt.floor("h")
    weather_df["dt_h"] = weather_df["dt"].dt.floor("h")

    merged = pd.merge(
        tide_df[["dt_h", "tide_cm", "is_high_tide"]],
        weather_df[["dt_h", "vs_m", "is_fog", "is_night"]],
        on="dt_h", how="inner"
    )
    merged["triple_risk"] = (
        merged["is_high_tide"] & merged["is_fog"] & merged["is_night"]
    )
    merged["dual_risk"] = (
        merged["is_high_tide"].astype(int) +
        merged["is_fog"].astype(int) +
        merged["is_night"].astype(int)
    ) >= 2
    merged["date"] = merged["dt_h"].dt.date

    # 일별 집계
    daily = merged.groupby("date").agg(
        triple_risk_hours  = ("triple_risk", "sum"),
        dual_risk_hours    = ("dual_risk", "sum"),
        high_tide_hours    = ("is_high_tide", "sum"),
        fog_hours          = ("is_fog", "sum"),
        night_hours        = ("is_night", "sum"),
        avg_tide_cm        = ("tide_cm", "mean"),
        min_vis_m          = ("vs_m", "min"),
        total_hours        = ("dt_h", "count"),
    ).reset_index()

    # 위험 점수 (0~1): 3중 발생 시간 비중 + 보정
    daily["risk_score"] = (
        daily["triple_risk_hours"] * 0.6 +
        daily["dual_risk_hours"]   * 0.25 +
        (daily["fog_hours"] / daily["total_hours"]) * 0.1 +
        (daily["high_tide_hours"] / daily["total_hours"]) * 0.05
    ) / daily["total_hours"].clip(lower=1) * 10  # 0~1 스케일 조정

    daily["risk_score"] = daily["risk_score"].clip(0, 1).round(4)
    daily["risk_level"] = pd.cut(
        daily["risk_score"],
        bins=[-0.001, 0.05, 0.15, 0.35, 1.01],
        labels=["정상", "주의", "경계", "위험"]
    )

    # 계절 분류
    daily["date"] = pd.to_datetime(daily["date"])
    daily["month"] = daily["date"].dt.month
    daily["season"] = daily["month"].map(
        lambda m: "봄" if m in [3,4,5] else "여름" if m in [6,7,8]
        else "가을" if m in [9,10,11] else "겨울"
    )

    daily.to_csv(OUT_DIR / "daily_risk.csv", index=False)
    print(f"[일별위험] {len(daily)}일 저장")
    print(f"  3중취약일: {(daily.triple_risk_hours > 0).sum()}일")
    print(f"  위험등급: {dict(daily.risk_level.value_counts())}")
    return daily


# ────────────────────────────────────────────
# 5. 미래 예측용 계절 통계 생성
# ────────────────────────────────────────────
def compute_seasonal_stats(daily_df=None):
    if daily_df is None:
        daily_df = pd.read_csv(OUT_DIR / "daily_risk.csv", parse_dates=["date"])

    daily_df["month"] = daily_df["date"].dt.month
    daily_df["day_of_year"] = daily_df["date"].dt.day_of_year

    # 월별 위험 통계
    monthly = daily_df.groupby("month").agg(
        avg_risk_score      = ("risk_score", "mean"),
        avg_triple_hours    = ("triple_risk_hours", "mean"),
        fog_prob            = ("fog_hours", lambda x: (x > 0).mean()),
        high_tide_avg_hours = ("high_tide_hours", "mean"),
    ).reset_index()

    monthly.to_csv(OUT_DIR / "seasonal_stats.csv", index=False)
    print(f"[계절통계] 월별 위험 패턴 저장")
    print(monthly[["month", "avg_risk_score", "avg_triple_hours", "fog_prob"]].to_string())
    return monthly


if __name__ == "__main__":
    print("=" * 50)
    print("CGIP 데이터 파이프라인 실행")
    print("=" * 50)
    tide_df    = process_tide()
    weather_df = process_weather()
    pop_df     = process_population()
    daily_df   = compute_daily_risk(tide_df, weather_df)
    compute_seasonal_stats(daily_df)
    print("\n✅ 전처리 완료 →", OUT_DIR)
