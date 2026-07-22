"""
data.go.kr 전북 CCTV API → data/cctv_jeonbuk.csv 수집 스크립트
실행: python backend/scripts/collect_cctv.py
"""
import sys
import os
import csv
import time
import urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_KEY = os.getenv("DATA_GO_KR_KEY", "")
if not API_KEY:
    raise RuntimeError("DATA_GO_KR_KEY 환경변수를 설정하세요 (.env 파일 또는 export)")
BASE_URL = "https://apis.data.go.kr/6540000/cctvService/getCctvList"
PAGE_SIZE = 1000
OUT_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "data", "cctv_jeonbuk.csv")


def fetch_page(page_no: int) -> tuple[list[dict], int]:
    url = (f"{BASE_URL}?serviceKey={API_KEY}"
           f"&pageNo={page_no}&numOfRows={PAGE_SIZE}")
    with urllib.request.urlopen(url, timeout=30) as resp:
        xml_data = resp.read()

    root = ET.fromstring(xml_data)
    total = int(root.findtext(".//totalCount") or 0)

    rows = []
    for item in root.findall(".//list"):
        x = item.findtext("XPos")
        y = item.findtext("YPos")
        if not x or not y:
            continue
        try:
            lat = float(y)
            lon = float(x)
        except ValueError:
            continue
        rows.append({
            "위도": lat,
            "경도": lon,
            "주소": item.findtext("lotAddrNm") or "",
            "설치유형": item.findtext("installType") or "",
            "관리기관": item.findtext("manageNm") or "",
            "설치일": item.findtext("installDate") or "",
        })
    return rows, total


def main():
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    print("전북 CCTV 데이터 수집 시작...")
    first_rows, total = fetch_page(1)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    print(f"총 {total:,}건 / {total_pages}페이지")

    all_rows = first_rows[:]
    for page in range(2, total_pages + 1):
        print(f"  페이지 {page}/{total_pages} 수집 중...", end="\r")
        rows, _ = fetch_page(page)
        all_rows.extend(rows)
        time.sleep(0.3)

    print(f"\n수집 완료: {len(all_rows):,}건")

    with open(OUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["위도", "경도", "주소", "설치유형", "관리기관", "설치일"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"저장 완료: {OUT_FILE}")

    # 전북 서해안 범위 내 건수 확인
    coastal = [r for r in all_rows
               if 35.0 <= r["위도"] <= 35.97 and 126.45 <= r["경도"] <= 126.75]
    print(f"서해안 격자 범위 내 CCTV: {len(coastal):,}건")


if __name__ == "__main__":
    main()
