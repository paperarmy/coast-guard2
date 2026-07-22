"""
야간 위험 시계열 STL 분해 → processed/night_anomaly_monthly.csv 생성

STL (Seasonal-Trend decomposition using LOESS):
  - 입력: tide_hourly + weather_hourly → 야간(20~06시) 시간별 triple-risk
  - 출력: 월별 야간 이상지수 (0~1 정규화)

실행: python backend/scripts/run_stl.py
"""
import sys
import os
import csv
import math
from datetime import datetime, date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PROCESSED = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))


def _load_hourly() -> list[dict]:
    """tide_hourly + weather_hourly join (공통 datetime 기준)."""
    tide: dict[str, float] = {}
    with open(os.path.join(PROCESSED, "tide_hourly.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            dt_str = row["dt"][:16]  # "YYYY-MM-DD HH:MM"
            tide[dt_str] = float(row["tide_cm"])

    rows = []
    with open(os.path.join(PROCESSED, "weather_hourly.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            dt_str = row["dt"][:16]
            if dt_str not in tide:
                continue
            tide_cm = tide[dt_str]
            is_night = row["is_night"] == "True"
            is_fog = row["is_fog"] == "True"
            is_high_tide = tide_cm >= 500
            is_triple = is_night and is_fog and is_high_tide
            rows.append({
                "dt":         dt_str,
                "date":       dt_str[:10],
                "hour":       int(row["hour"]),
                "is_night":   is_night,
                "is_fog":     is_fog,
                "is_high":    is_high_tide,
                "is_triple":  is_triple,
            })
    return rows


def _daily_night_risk(rows: list[dict]) -> dict[str, float]:
    """날짜별 야간 triple-risk 비율 (0~1)."""
    nightly: dict[str, list] = {}
    for r in rows:
        if not r["is_night"]:
            continue
        d = r["date"]
        if d not in nightly:
            nightly[d] = []
        nightly[d].append(1 if r["is_triple"] else 0)
    return {d: sum(v) / len(v) for d, v in nightly.items() if v}


def _stl_decompose(series: list[float], period: int = 365) -> dict[str, list[float]]:
    """statsmodels STL 분해. 실패 시 단순 이동평균 fallback."""
    try:
        from statsmodels.tsa.seasonal import STL
        import numpy as np
        arr = np.array(series, dtype=float)
        result = STL(arr, period=period, robust=True).fit()
        return {
            "trend":    result.trend.tolist(),
            "seasonal": result.seasonal.tolist(),
            "resid":    result.resid.tolist(),
        }
    except Exception as e:
        print(f"  STL 실패: {e} → 이동평균 fallback")
        n = len(series)
        w = min(period, n // 2)
        trend = []
        for i in range(n):
            lo = max(0, i - w // 2)
            hi = min(n, i + w // 2 + 1)
            trend.append(sum(series[lo:hi]) / (hi - lo))
        resid = [series[i] - trend[i] for i in range(n)]
        return {"trend": trend, "seasonal": [0.0] * n, "resid": resid}


def _monthly_anomaly(dates: list[str], residuals: list[float]) -> dict[int, float]:
    """월별 residual 평균 → 0~1 정규화."""
    monthly: dict[int, list] = {m: [] for m in range(1, 13)}
    for d, r in zip(dates, residuals):
        m = int(d[5:7])
        monthly[m].append(r)
    avg = {m: sum(v) / len(v) if v else 0.0 for m, v in monthly.items()}
    vmin, vmax = min(avg.values()), max(avg.values())
    span = vmax - vmin if vmax > vmin else 1.0
    return {m: round((v - vmin) / span, 4) for m, v in avg.items()}


def main():
    print("야간 시계열 로드 중...")
    rows = _load_hourly()
    print(f"  시간별 레코드: {len(rows):,}행")

    daily = _daily_night_risk(rows)
    print(f"  일별 야간 위험 비율: {len(daily)}일")

    dates = sorted(daily.keys())
    series = [daily[d] for d in dates]
    triple_days = sum(1 for v in series if v > 0)
    print(f"  야간 triple-risk 발생일: {triple_days}일 ({triple_days/len(series)*100:.1f}%)")

    print("STL 분해 중...")
    decomposed = _stl_decompose(series, period=365)
    residuals = decomposed["resid"]

    monthly = _monthly_anomaly(dates, residuals)
    print(f"  월별 anomaly: {monthly}")

    out = os.path.join(PROCESSED, "night_anomaly_monthly.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["month", "anomaly_index", "description"])
        labels = {1:"1월", 2:"2월", 3:"3월", 4:"4월", 5:"5월", 6:"6월",
                  7:"7월", 8:"8월", 9:"9월", 10:"10월", 11:"11월", 12:"12월"}
        for m in range(1, 13):
            writer.writerow([m, monthly.get(m, 0.5), labels[m]])

    print(f"저장: {out}")

    # 전체 통계 요약
    overall_avg = sum(series) / len(series)
    print(f"\n  전체 야간 triple-risk 발생률: {overall_avg*100:.2f}%")
    max_month = max(monthly, key=monthly.get)
    min_month = min(monthly, key=monthly.get)
    print(f"  최고 이상 월: {max_month}월 (index={monthly[max_month]:.3f})")
    print(f"  최저 이상 월: {min_month}월 (index={monthly[min_month]:.3f})")

    # 일별 STL 결과도 저장 (이상탐지 탭용)
    out_daily = os.path.join(PROCESSED, "night_anomaly_daily.csv")
    with open(out_daily, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "night_risk", "trend", "seasonal", "residual", "month"])
        for i, d in enumerate(dates):
            writer.writerow([
                d,
                round(series[i], 4),
                round(decomposed["trend"][i], 4),
                round(decomposed["seasonal"][i], 4),
                round(residuals[i], 4),
                int(d[5:7]),
            ])
    print(f"저장: {out_daily} ({len(dates)}행)")


if __name__ == "__main__":
    main()
