# 현재 개발 진행 상황
최종 업데이트: 2026-07-22

---

## 전체 진행률

```
Phase 0 (프로토타입)         ████████████████████ 100%  ✅
Phase 1 (Vercel + 실 데이터) ████████████████████ 100%  ✅ 완료
Phase 2 (자동화 + 고도화)    ████████████████████ 100%  ✅ 완료
Phase 3 (전국 확장)          ░░░░░░░░░░░░░░░░░░░░   0%  🔲
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
- [x] 전북 CCTV 13,865개 (`data/cctv_jeonbuk.csv`, data.go.kr API 수집)
- [x] 군산 기상 2023년 8,760행 (`data/weather_gunsan_2023.csv`)
- [x] 군산 기상 2024~2025년 17,545행 (`data/weather_gunsan_2023_2025.csv`)

---

## Phase 1 완료 항목 ✅ (2026-07-22 완료)

### 1-A. Vercel 배포 환경 ✅ 완료

- [x] `vercel.json` — 정적 프론트엔드 + `/api/*` 서버리스 라우팅
- [x] `api/index.py` — Vercel Python 런타임용 FastAPI ASGI 래퍼 (`sys.path` 설정)
- [x] `api/requirements.txt` — Vercel 전용 (uvicorn/apscheduler/geopandas 제외)
- [x] `frontend/app.js` `API` 상수 — `localhost` 판별 → 환경별 자동 분기
- [x] `backend/main.py` CORS — `allow_origin_regex` 로 `coast-guard*.vercel.app` 허용
- [x] `backend/data/processed/` 7개 CSV — git 포함 (Vercel 접근 가능)
- [x] `.gitattributes` — `eol=lf` 강제 (Vercel Linux 환경 기준)
- [x] `.env.example` 생성, `.gitignore` 정비 (`/data/` 원본 제외)
- [x] `routers/assets.py` `PUT` — Vercel 파일시스템 쓰기 실패 시 HTTP 503 반환
- [x] GitHub push → Vercel 자동 배포 연결 확인

### 실 데이터 수집 (수동 다운로드)
- [x] KHOA 조위 관측 — `data/군산_*.txt` (2023/03~2026/05, 월별 TXT)
- [x] SGIS 인구격자 SHP — `data/sgis/grid_나마_500M.shp`, `grid_다마_500M.shp`
- [x] SGIS 인구 CSV — `data/sgis/격자_*_읍면동별_인구.csv`
- [x] MDIS 해수면-어선현황 — `data/2020_해수면-어선현황_*.csv` (군산 456, 부안 409, 고창 75척)
- [x] 전북 CCTV 수집 — `backend/scripts/collect_cctv.py` → `data/cctv_jeonbuk.csv` (13,865건)

### 실 데이터 전처리 파이프라인
- [x] `services/data_pipeline.py` — 조위·기상·인구 일괄 전처리 (1회성 실행)
- [x] `data/processed/tide_hourly.csv` — KHOA 조위 **25,656행** (is_high_tide: ≥500cm)
- [x] `data/processed/weather_hourly.csv` — ASOS 기상 **26,304행** (is_fog, is_night 플래그)
- [x] `data/processed/population_grid.csv` — SGIS 500m 격자 **8,575개** (해안 필터)
- [x] `data/processed/daily_risk.csv` — **918일** 일별 위험 점수
- [x] `data/processed/seasonal_stats.csv` — 월별 계절 통계 (12개월)
- [x] `data/processed/cctv_grid_counts.csv` — **210개 격자별 CCTV 수** (Vercel 배포용)
- [x] `data/processed/vessel_summary.csv` — **지역별 어선 집계** 3행 (Vercel 배포용)

### 실 데이터 서비스 레이어 ✅ 전부 완료
- [x] `services/cctv_loader.py` — data.go.kr CCTV 데이터 → 격자별 CCTV 수 매핑
- [x] `services/population_loader.py` — SGIS 인구밀도 → 격자별 old_building proxy
- [x] `services/vessel_loader.py` — MDIS 어선현황 → 격자별 vessel_density
- [x] `services/cvi_calculator.py` — SHAP 가중치 기반 실 CVI 산출 (dummy_grids 교체)
- [x] `services/environment_service.py` — 조석수식 + 계절통계 기반 현재 환경 (dummy_environment 교체)
- [x] `backend/scripts/preprocess_assets.py` — Vercel용 processed CSV 생성 스크립트

### 위험 캘린더 백엔드
- [x] `services/risk_calendar.py` — 과거 실측 조회 + 미래 예측 서비스 (@lru_cache)
- [x] `routers/calendar.py` — 4개 API 엔드포인트

### 위험 캘린더 프론트엔드
- [x] 월간 히트맵 — risk-0~risk-10 색상 + 3중취약 노란 점 표시
- [x] 실측/예측 구분 — 예측 셀에 점선 테두리 오버레이
- [x] 날짜 클릭 → 24시간 막대 차트
- [x] 예측 신뢰도 바 (80%→30%, 경과 일수 비례 감소)
- [x] 하단 트렌드 차트 — 90일 실측 + 90일 예측 바차트
- [x] 날짜 직접 입력 (`<input type="date">`) — 선택 즉시 해당 월·일 자동 이동

### 격자별 미래 CVI 예측 모드
- [x] `GET /api/grids/forecast?date=YYYY-MM-DD` — 격자 예측 CVI (최대 90일)
- [x] 대시보드 예측 컨트롤 바 — 날짜 선택 → 지도·테이블 전부 예측 CVI로 교체
- [x] 지도 팝업 — 기본 CVI 대비 변화량(Δ) 표시

---

## Phase 2 완료 항목 ✅ (2026-07-22 완료)

### night_anomaly 실 데이터화 (STL 분해)
- [x] `backend/scripts/run_stl.py` — 918일 야간·만조·안개 시계열 STL 분해 실행
- [x] `data/processed/night_anomaly_monthly.csv` — 월별 이상지수 12행 (12월=1.0, 9월=0.0)
- [x] `data/processed/night_anomaly_daily.csv` — 918일 trend/seasonal/residual
- [x] `services/stl_service.py` — 월별·일별 STL 결과 서비스 레이어
- [x] `services/cvi_calculator.py` night_anomaly — STL 실 데이터로 교체 완료

### 기상청 ASOS 실측 API 연동
- [x] `services/weather_api.py` — 군산 관측소(140) 현재 시각 기상 조회
  - 실패 시 계절통계 fallback
- [x] `services/environment_service.py` — ASOS API 우선 → 계절통계 fallback
- [x] `GET /api/environment/current` — 실측 기상 + 조석 수식 혼합 응답

### Vercel Cron Job 설정
- [x] `vercel.json` — Cron Job 매일 자정 UTC 실행 (`"0 0 * * *"`)
- [x] `routers/cron.py` — 캐시 초기화·워밍 엔드포인트 (`/api/cron/refresh`)
  - CRON_SECRET 인증 필수
- [x] 캐시 갱신 대상: cctv, vessel, population, stl, environment, cvi, risk_calendar

### STL 잔차 이상탐지 탭 실 데이터 연동
- [x] `routers/grids.py` — STL 일별 시계열 → `/api/grids/{id}/timeseries` (최대 918일)
- [x] 이상탐지 탭 차트 — 실측 night_anomaly_index + 3중취약일 마커

### 코드 리뷰 버그 수정 (2026-07-22)
- [x] `collect_cctv.py` — API 키 하드코딩 제거 (→ `DATA_GO_KR_KEY` 환경변수)
- [x] `cron.py` — CRON_SECRET 미설정 시 인증 우회 수정 (기본 차단으로 변경)
- [x] `cron.py` — `_clear_caches()` 누락 모듈 추가 (cvi_calculator, risk_calendar)
- [x] `cron.py` — `/api/cron/status` 인증 없는 접근 차단
- [x] `environment_service.py` — 7일 예측 레이블 1일 오프셋 수정 (오늘→내일 기준 정렬)
- [x] `environment_service.py` — 0°C falsy-zero 버그 수정 (`is not None` 체크)
- [x] `main.py` — CORS regex 범위 축소 (`coast-guard*` 한정)
- [x] `weather_api.py` — 안개 판단 시각 오류 수정 (`now.hour` → `target.hour`)
- [x] `app.js` — `data.series` undefined 가드 추가
- [x] `app.js` — 날짜 계산 UTC 오프셋 버그 수정 (`fmtDate` 로컬 날짜 헬퍼 도입)

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
| STL 최대 이상 월 | 12월(1.0), 11월(0.97), 1~2월(0.83) | 동절기 야간 안개 집중 |
| STL 최저 이상 월 | 9월(0.0), 6월(0.13) | 하절기 이상지수 낮음 |
| 서해안 격자 내 CCTV | 2,179건 / 13,865건 전체 | 서비스 범위: 35.0~35.97°N |
| 어선 현황 (MDIS 2020) | 군산 456 / 부안 409 / 고창 75척 | 총 940척 |

---

## 확인된 이슈

| # | 이슈 | 영향 | 상태 |
|---|------|------|------|
| 1 | 조석 API (1192136) 500 오류 | KHOA TXT 직접 다운으로 우회 완료 | ✅ 해결 |
| 2 | 건물대장 API 응답 빈값 | 노후건물 비율 → 인구밀도 proxy 사용 | ✅ 우회 |
| 3 | 어업통계 API 500 오류 | MDIS 어업총조사 CSV 직접 다운으로 우회 | ✅ 해결 |
| 4 | Node.js 없음 | Python http.server로 프론트엔드 서빙 | ✅ 해결 |
| 5 | 기상 2023년 1월 API 타임아웃 | 분기별 나눠 재수집 완료 | ✅ 해결 |
| 6 | 캘린더 range API 400 오류 | 1100일 제한 → 1500일로 상향 | ✅ 해결 |
| 7 | 3중 취약 간조→만조 오기재 | 논문 오입력 → 전체 6개 파일 수정 완료 | ✅ 해결 |
| 8 | git CRLF 경고 (Windows autocrlf) | `.gitattributes` `eol=lf` + renormalize 적용 | ✅ 해결 |
| 9 | Vercel `PUT /api/assets` 파일 쓰기 불가 | OSError 잡아 HTTP 503 반환 | ✅ 해결 |
| 10 | Vercel 원본 데이터(`data/`) 접근 불가 | `processed/` CSV 생성 → git 포함 | ✅ 해결 |
| 11 | `Path(__file__).parent...` 상대경로 버그 | 모든 loader에 `.resolve()` 추가 | ✅ 해결 |
| 12 | Vercel cron 주기 오류 (Hobby 플랜 제한) | `"0 * * * *"` → `"0 0 * * *"` 수정 | ✅ 해결 |
| 13 | CRON_SECRET 미설정 시 인증 우회 | 기본 차단(deny-by-default)으로 변경 | ✅ 해결 |
| 14 | 7일 예측 레이블 1일 오프셋 | `timedelta(days=i+1)` + 레이블 내일/모레 기준 수정 | ✅ 해결 |
| 15 | ASOS 0°C 반환 시 falsy-zero로 계절값 대체 | `is not None` 조건으로 수정 | ✅ 해결 |
| 16 | 안개 판단 시각 오류 (now.hour vs target.hour) | 관측 시각(target.hour) 기준으로 수정 | ✅ 해결 |
| 17 | app.js UTC 날짜 오프셋 (KST 00~09시) | `fmtDate()` 로컬 날짜 헬퍼 도입 | ✅ 해결 |

---

## API 동작 확인 (2026-07-22 기준)

```
✅ GET /
✅ GET /api/grids                                             (210개, 실 CVI)
✅ GET /api/grids/summary
✅ GET /api/grids/top
✅ GET /api/grids/hotspots
✅ GET /api/grids/forecast?date=YYYY-MM-DD                   (격자별 예측 CVI, 최대 90일)
✅ GET /api/grids/{id}/timeseries?days=90                    (STL 이상탐지 실 데이터)
✅ GET /api/alert/today
✅ GET /api/alert/forecast                                   (7일 예측, 내일 기준 레이블)
✅ GET /api/environment/current                              (ASOS 실측 + 조석수식)
✅ GET /api/assets
✅ GET /api/calendar/range?start=2023-03-01&end=2025-09-04  (918일 실측)
✅ GET /api/calendar/day/2025-09-07                          (시간별 24행)
✅ GET /api/calendar/forecast?days=90                        (90일 예측)
✅ GET /api/calendar/stats                                   (종합 통계)
✅ GET /api/cron/refresh  (CRON_SECRET Bearer 토큰 필수)
🔒 GET /api/cron/status   (CRON_SECRET Bearer 토큰 필수)
```

로컬: http://localhost:8000/docs | 프론트: http://localhost:5173  
배포: https://coast-guard2-*.vercel.app

---

## Phase 3 추천 작업 (다음 단계)

| 우선순위 | 항목 | 설명 |
|---------|------|------|
| High | **Vercel Postgres 도입** | `assets.json` → DB 이전 (PUT 정상화, Phase 2 미완) |
| High | **기상청 단기예보 API** | 7일 예측을 계절통계 → 실 예보 데이터로 교체 |
| Medium | **격자별 노후건물 비율** | SGIS or 건물대장 연동 (현재 인구밀도 proxy) |
| Medium | **전국 확장 데이터 수집** | 충남·경남 등 추가 해안선 격자 |
| Low | **모바일 최적화** | 반응형 레이아웃, 스와이프 제스처 |
