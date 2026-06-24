# CGIP — 해안경계 취약구간 모니터링

> **CoastGuard Intelligence Platform**  
> CVI(해안침투 취약지수) 기반 실시간 해안경계 의사결정 지원 시스템

---

## 소개

전북 서해안(군산·부안·고창) 해안선을 3km×3km 격자 **210개**로 나누고, 야간·만조·안개 등 8종 데이터를 결합해 **침투 취약지수(CVI)**를 산출합니다.  
경계 담당자는 매일 이 시스템에 접속해 **"오늘 어디에 드론과 TOD를 집중할지"** 를 데이터로 결정합니다.

### 실증 결과
- RandomForest CVI 모델 AUC **0.963**
- 실제 침투사건 3건 사후검증 공간 적중률 **100%** (CVI 상위 20% 이내)
- 균등 배치 대비 드론 집중도 **10배**, 탐지 정밀도 **5배** 향상 추정

### 3중 취약 조건 (핵심 경보 로직)
> **야간(20~06시) + 만조(조위 ≥ 500cm) + 안개(시정 < 1km)** 동시 발생 시 최고 경보  
> 만조 시 선박이 해안선 깊숙이 진입 가능 → 침투 난이도 최저  
> 실 데이터 분석 결과: 918일 중 **330일(35.9%)** 에서 3중 취약 발생

---

## 화면 구성 (5개 탭)

| 탭 | 내용 |
|----|------|
| 대시보드 | CVI 히트맵 지도, 오늘의 경계 중점, 3중 취약 경보 배너, 7일 예측 |
| 격자 분석 | 210개 격자 테이블 (정렬/필터/CSV 내보내기), 격자 상세 SHAP 패널 |
| 감시 자산 | 드론·TOD·CCTV·해경 배치 현황 지도 |
| 이상탐지 | 격자별 야간 이상 지수 시계열 그래프 (STL 분해) |
| **위험 캘린더** | 월간 위험 히트맵, 날짜별 시간별 조건 분해, 30일 예측, 트렌드 차트 |

---

## 설치 및 실행

### 사전 요구사항
- Python 3.10 이상
- Node.js 불필요 (순수 HTML/CSS/JS + CDN)

### 1단계 — 패키지 설치

```bash
cd coast-guard/backend
pip install fastapi uvicorn pydantic httpx pandas numpy python-dotenv geopandas
```

### 2단계 — 백엔드 실행

```bash
# coast-guard/backend 디렉토리에서
python -m uvicorn main:app --reload --port 8000
```

### 3단계 — 프론트엔드 실행

```bash
# coast-guard/ 루트 디렉토리에서
python -m http.server 5173 --directory frontend
```

### 4단계 — 접속

| 주소 | 내용 |
|------|------|
| http://localhost:5173 | 메인 화면 |
| http://localhost:8000/docs | API 문서 (Swagger UI) |

---

## 데이터 현황

### 수집 및 전처리 완료

| 데이터 | 규모 | 파일 위치 | 상태 |
|--------|------|----------|------|
| 전북 CCTV 위치 (행안부) | 8,284개 | `data/cctv_jeonbuk.csv` | ✅ |
| 기상 관측 군산 2023~2025 | 26,304행 | `data/weather_gunsan_*.csv` | ✅ |
| KHOA 조위 관측 (군산항) | 25,656행 | `data/군산_*.txt` → `processed/tide_hourly.csv` | ✅ |
| SGIS 인구격자 (500m) | 8,575격자 | `data/sgis/` → `processed/population_grid.csv` | ✅ |
| 일별 위험 점수 | 918일 | `data/processed/daily_risk.csv` | ✅ |
| 월별 계절 통계 | 12개월 | `data/processed/seasonal_stats.csv` | ✅ |

### 연동 예정 (Phase 1 잔여)

| 데이터 | 출처 | 용도 |
|--------|------|------|
| 격자별 CCTV 수 매핑 | `cctv_jeonbuk.csv` | CVI 변수 (감시 커버리지) |
| 실 CVI 재산출 | 위 모든 실 데이터 | SHAP 가중치 적용 |

---

## 프로젝트 구조

```
coast-guard/
├── backend/
│   ├── main.py               ← FastAPI 앱 (5개 라우터 등록)
│   ├── routers/
│   │   ├── grids.py          ← 격자 목록/상세/시계열/핫스팟
│   │   ├── alerts.py         ← 오늘 경보 / 7일 예측
│   │   ├── environment.py    ← 현재 환경 (기상+조위)
│   │   ├── assets.py         ← 감시 자산 목록/수정
│   │   └── calendar.py       ← 위험 캘린더 4개 엔드포인트
│   ├── services/
│   │   ├── data_pipeline.py  ← 조위·기상·인구 전처리 (1회성)
│   │   └── risk_calendar.py  ← 실측 조회 + 미래 예측
│   └── data/
│       ├── dummy_grids.py    ← 격자 더미 (Phase 1 잔여)
│       ├── dummy_environment.py ← 환경 더미 (Phase 1 잔여)
│       ├── assets.json       ← 자산 위치 (런타임 편집)
│       └── processed/        ← 전처리 결과 CSV (git 제외)
├── frontend/
│   ├── index.html            ← 단일 HTML (5탭 레이아웃)
│   ├── style.css             ← 군용 다크모드 스타일
│   └── app.js                ← 전체 프론트엔드 로직
└── data/                     ← 원본 수집 파일 (git 제외)
    ├── cctv_jeonbuk.csv
    ├── weather_gunsan_*.csv
    ├── 군산_*.txt             ← KHOA 조위 월별 TXT
    └── sgis/                 ← SGIS SHP + CSV
```

---

## 주요 API

```
GET /api/grids                  전체 격자 목록 (필터: region, lisa, cvi)
GET /api/grids/summary          통계 요약
GET /api/grids/{id}             격자 상세 + SHAP 기여도
GET /api/grids/{id}/timeseries  야간 이상 지수 시계열
GET /api/alert/today            오늘 3중 취약 경보 상태
GET /api/alert/forecast         7일 예측 캘린더
GET /api/environment/current    현재 기상 + 조위
GET /api/assets                 감시 자산 목록
PUT /api/assets/{id}            자산 위치·상태 수정
GET /api/calendar/range         기간별 일별 위험 점수 (최대 1500일)
GET /api/calendar/day/{date}    특정일 시간별 24행 상세
GET /api/calendar/forecast      미래 N일 예측 (최대 90일)
GET /api/calendar/stats         전체 통계 요약
```

---

## 개발 단계

| 단계 | 내용 | 상태 |
|------|------|------|
| Phase 0 | 프로토타입 — 더미 데이터 기반 전체 UI | ✅ 완료 |
| Phase 1 | 실 데이터 연동 — KHOA·ASOS·SGIS 전처리 + 위험 캘린더 | 🔄 65% 진행 |
| Phase 2 | 자동화 — 1시간 주기 갱신, 리포트 PDF | 🔲 예정 |
| Phase 3 | 전국 확장 — 충남 → 전국 2,600격자 | 🔲 예정 |

---

## 참고 논문

- 본 시스템은 「데이터로 찾는 해안경계 취약구간 (2026, 김태옥)」 연구를 기반으로 구현
- CVI 방법론: XGBoost/RandomForest + SHAP + Moran's I + DBSCAN 공간군집 분석
