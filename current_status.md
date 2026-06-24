# 현재 개발 진행 상황
최종 업데이트: 2026-06-24

---

## 전체 진행률

```
Phase 0 (프로토타입)   ████████████████████ 100%  ✅
Phase 1 (실 데이터)    █████████████░░░░░░░  65%  🔄 진행 중
Phase 2 (자동화)       ░░░░░░░░░░░░░░░░░░░░   0%  🔲
Phase 3 (전국 확장)    ░░░░░░░░░░░░░░░░░░░░   0%  🔲
```

---

## Phase 0 완료 항목 ✅

### 백엔드 (FastAPI)
- [x] `main.py` — FastAPI 앱, CORS 설정 (localhost:5173, 3000)
- [x] `routers/grids.py` — 격자 목록/상세/시계열/핫스팟 API
- [x] `routers/alerts.py` — 오늘 경보 / 7일 예측 (만조 기준 수정 완료)
- [x] `routers/environment.py` — 현재 환경 데이터
- [x] `routers/assets.py` — 자산 목록 / 위치 수정
- [x] `data/dummy_grids.py` — 210개 격자 더미 (CVI·SHAP·LISA 포함)
- [x] `data/dummy_environment.py` — 기상·조위·3중취약 더미 (만조 기준 수정 완료)
- [x] `data/assets.json` — 드론 3 / TOD 3 / CCTV 3 / 해경 1 기본값

### 프론트엔드 (HTML/CSS/JS)
- [x] `index.html` — 5탭 레이아웃 (대시보드/격자분석/감시자산/이상탐지/위험캘린더)
- [x] `style.css` — 군용 다크모드 스타일 전체 (cal-* 포함)
- [x] `app.js` — 전체 로직 (지도·테이블·차트·상세패널·캘린더·API 호출)
- [x] Leaflet 지도 — CVI 히트맵, 자산 지도 2개
- [x] 경보 배너 — 3중 취약 레벨에 따른 pulse 애니메이션
- [x] 격자 테이블 — 정렬·필터·CSV 내보내기
- [x] SHAP 기여도 패널 — 5개 변수 막대 시각화
- [x] Chart.js 시계열 — STL 잔차 + 3중취약일 마커
- [x] 7일 예측 캘린더 카드
- [x] 오늘의 경계 중점 + 인쇄 기능

### 초기 데이터 수집
- [x] 전북 CCTV 8,284개 (`data/cctv_jeonbuk.csv`)
- [x] 군산 기상 2023년 8,760행 (`data/weather_gunsan_2023.csv`)
- [x] 군산 기상 2024~2025년 17,545행 (`data/weather_gunsan_2023_2025.csv`)

---

## Phase 1 완료 항목 🔄 (2026-06-24 기준)

### 실 데이터 수집 (수동 다운로드)
- [x] KHOA 조위 관측 — `data/군산_*.txt` (2023/03~2026/05, 월별 TXT)
- [x] SGIS 인구격자 SHP — `data/sgis/grid_나마_500M.shp`, `grid_다마_500M.shp`
- [x] SGIS 인구 CSV — `data/sgis/격자_*_읍면동별_인구.csv`

### 실 데이터 전처리 파이프라인
- [x] `services/data_pipeline.py` — 조위·기상·인구 일괄 전처리 (1회성 실행)
- [x] `data/processed/tide_hourly.csv` — KHOA 조위 **25,656행** (is_high_tide: ≥500cm)
- [x] `data/processed/weather_hourly.csv` — ASOS 기상 **26,304행** (is_fog, is_night 플래그)
- [x] `data/processed/population_grid.csv` — SGIS 500m 격자 **8,575개** (해안 필터)
- [x] `data/processed/daily_risk.csv` — **918일** 일별 위험 점수
- [x] `data/processed/seasonal_stats.csv` — 월별 계절 통계 (12개월)

### 위험 캘린더 백엔드
- [x] `services/risk_calendar.py` — 과거 실측 조회 + 미래 예측 서비스 (@lru_cache)
- [x] `routers/calendar.py` — 4개 API 엔드포인트
- [x] `main.py` — calendar 라우터 등록

### 위험 캘린더 프론트엔드
- [x] 월간 히트맵 — risk-0~risk-10 색상 + 3중취약 노란 점 표시
- [x] 실측/예측 구분 — 예측 셀에 점선 테두리 오버레이
- [x] 날짜 클릭 → 24시간 막대 차트 (빨강=3중/주황=2중/파랑=만조/보라=안개)
- [x] 일별 조건 합계 패널 (만조·안개·야간·3중취약 시간 수)
- [x] 예측 신뢰도 바 (80%→30%, 경과 일수 비례 감소)
- [x] 하단 트렌드 차트 — 90일 실측 + 30일 예측 바차트

---

## 실 데이터 기반 발견 사실

| 지표 | 값 | 비고 |
|------|-----|------|
| 분석 기간 | 918일 (2023-03-01 ~ 2025-09-04) | 조위·기상 교집합 |
| 3중 취약일 | **330일 (35.9%)** | 야간+만조+안개 동시 |
| 최고 위험 월 | **6월 (avg 0.754)** | 7월(0.713), 8월(0.694) 순 |
| 논문과의 차이 | 실 데이터는 여름 집중 | 논문: 가을 집중 가설 → 수정 필요 |
| 만조 시간 비율 | 28.4% | 조위 ≥ 500cm 기준 |
| 안개 시간 비율 | 20.5% | 시정 < 1km 기준 |

---

## Phase 1 잔여 작업

| 항목 | 더미 위치 | 교체 필요 소스 | 우선순위 |
|------|----------|--------------|---------|
| 격자별 CCTV 수 | `dummy_grids.py` L69 | `cctv_jeonbuk.csv` | High |
| 격자별 고령비율 | `dummy_grids.py` L62~63 | `processed/population_grid.csv` | High |
| 실 CVI 재산출 | `dummy_grids.py` 전체 | SHAP 가중치 적용 | Critical |
| 현재 환경 실 연동 | `dummy_environment.py` | `processed/tide_hourly.csv` + 최신 기상 | Medium |
| 격자별 노후건물 | `dummy_grids.py` L63 | SGIS or 건물대장 | Low |
| 어선 밀도 | `dummy_grids.py` L64 | MDIS 어업총조사 | Low |

---

## 확인된 이슈

| # | 이슈 | 영향 | 상태 |
|---|------|------|------|
| 1 | 조석 API (1192136) 500 오류 | KHOA TXT 직접 다운으로 우회 완료 | ✅ 해결 |
| 2 | 건물대장 API 응답 빈값 | 노후건물 비율 더미 유지 (Low 우선순위) | 🔲 |
| 3 | 어업통계 API 500 오류 | 어선 밀도 더미 유지 (Low 우선순위) | 🔲 |
| 4 | Node.js 없음 | Python http.server로 프론트엔드 서빙 | ✅ 해결 |
| 5 | 기상 2023년 1월 API 타임아웃 | 분기별 나눠 재수집 완료 | ✅ 해결 |
| 6 | 캘린더 range API 400 오류 | 1100일 제한 → 1500일로 상향 | ✅ 해결 |
| 7 | 3중 취약 간조→만조 오기재 | 논문 오입력 → 전체 6개 파일 수정 완료 | ✅ 해결 |

---

## API 동작 확인 (2026-06-24 기준)

```
✅ GET /
✅ GET /api/grids/summary
✅ GET /api/grids/top
✅ GET /api/grids/hotspots
✅ GET /api/alert/today
✅ GET /api/alert/forecast
✅ GET /api/environment/current
✅ GET /api/assets
✅ GET /api/calendar/range?start=2023-03-01&end=2025-09-04   (948일 실측)
✅ GET /api/calendar/day/2025-09-07                           (시간별 24행, 3중취약 확인)
✅ GET /api/calendar/forecast?days=30                         (30일 예측)
✅ GET /api/calendar/stats                                    (종합 통계)
```

서버: http://localhost:8000 | 프론트: http://localhost:5173

---

## 다음 추천 작업 (우선순위 순)

1. **`services/cvi_calculator.py`** — `cctv_jeonbuk.csv` + `population_grid.csv` 기반 실 CVI 산출, `dummy_grids.py` 교체
2. **`/api/environment/current` 실 연동** — `tide_hourly.csv` 최신 행 + 기상청 ASOS API로 현재 조위·기상 반환
3. **기상청 단기예보 API 연동** — 3일 예측 정밀도 향상 (현재 계절 통계 기반)
