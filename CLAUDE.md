# CLAUDE.md — CGIP 프로젝트 작업 규칙

## 프로젝트 한 줄 요약
해안침투 취약지수(CVI)를 실시간으로 시각화해 군 경계 담당자가 드론·TOD·CCTV를 어디에 집중할지 즉각 판단할 수 있게 하는 웹 앱.

---

## 디렉토리 구조

```
coast-guard/
├── backend/
│   ├── main.py               ← FastAPI 앱 진입점 (5개 라우터 등록)
│   ├── routers/
│   │   ├── grids.py          ← 격자 목록/상세/시계열/핫스팟
│   │   ├── alerts.py         ← 오늘 경보 / 7일 예측
│   │   ├── environment.py    ← 현재 환경 (기상+조위)
│   │   ├── assets.py         ← 감시 자산 목록/수정
│   │   └── calendar.py       ← 위험 캘린더 (range/day/forecast/stats)
│   ├── services/
│   │   ├── data_pipeline.py  ← 조위·기상·인구 전처리 (1회성 실행)
│   │   └── risk_calendar.py  ← 캘린더 서비스 (실측 조회 + 미래 예측)
│   ├── data/
│   │   ├── dummy_grids.py    ← 격자 더미 데이터 (실 데이터 전 사용)
│   │   ├── dummy_environment.py ← 환경 더미 (기상+조위)
│   │   ├── assets.json       ← 감시 자산 위치 (런타임 편집 가능)
│   │   └── processed/        ← 전처리 결과 CSV (git 제외)
│   │       ├── tide_hourly.csv      (25,656행)
│   │       ├── weather_hourly.csv   (26,304행)
│   │       ├── population_grid.csv  (8,575격자)
│   │       ├── daily_risk.csv       (918일)
│   │       └── seasonal_stats.csv   (월별 계절 통계)
│   └── requirements.txt
├── frontend/
│   ├── index.html            ← 단일 HTML 파일 (Node.js 불필요)
│   ├── style.css             ← 다크모드 전용 스타일
│   └── app.js                ← 전체 프론트엔드 로직
└── data/                     ← 수집된 원본 데이터 (git 제외 권장)
    ├── cctv_jeonbuk.csv
    ├── weather_gunsan_2023.csv
    ├── weather_gunsan_2023_2025.csv
    ├── 군산_*.txt             ← KHOA 조위 관측 (월별 TXT)
    └── sgis/                 ← SGIS 격자인구 SHP + CSV
```

---

## 기술 스택

| 계층 | 기술 | 비고 |
|------|------|------|
| Hosting | Vercel | 프론트(CDN) + 백엔드(Serverless) 통합 |
| Backend | Python FastAPI + ASGI | Vercel Python 런타임, `api/index.py` 진입점 |
| Frontend | 순수 HTML/CSS/JS | Node.js 없음, CDN으로 Leaflet + Chart.js |
| 지도 | Leaflet.js 1.9.4 | OpenStreetMap 타일 |
| 차트 | Chart.js 4.4.0 | 시계열 이상탐지 그래프 |
| DB | 없음 (Phase 1) | Phase 2에서 Vercel Postgres 또는 Supabase 도입 예정 |

---

## 로컬 실행 (개발용)

```bash
# 백엔드 (포트 8000)
cd backend
python -m uvicorn main:app --reload --port 8000

# 프론트엔드 (포트 5173)
cd ..
python -m http.server 5173 --directory frontend
```

접속: http://localhost:5173 | API 문서: http://localhost:8000/docs

## 배포 (Vercel)

```
배포 URL: https://{프로젝트}.vercel.app
진입점:   api/index.py  (FastAPI ASGI 래퍼)
설정 파일: vercel.json
```

- `vercel.json` — 프론트엔드 정적 서빙 + `/api/*` 서버리스 라우팅
- `api/index.py` — Vercel Python 런타임용 FastAPI 진입점
- `frontend/app.js` `API` 상수 — 로컬: `http://localhost:8000/api` / 배포: `/api`

---

## data.go.kr API 키
```
51d325a98e467da61d7f9d3be53c299fbc91742fc24fc5a95157148a5a6c3d05
```
코드에 하드코딩하지 말고 `.env` 파일에 `DATA_GO_KR_KEY=...` 형태로 관리할 것.

---

## 코딩 규칙

### 공통
- 한국어 변수명 금지. 변수는 영어 snake_case.
- 주석은 최소화. WHY가 불명확한 경우만 작성.
- 에러 핸들링은 API 경계에서만 (FastAPI HTTPException).

### 백엔드
- 라우터 파일당 역할 하나. 비즈니스 로직은 `services/`에 분리.
- 더미 데이터(`dummy_*.py`)는 실 데이터 서비스와 동일한 함수 시그니처를 유지. 교체 시 라우터 수정 최소화.
- 실 데이터 연동 순서: `dummy_*.py` → `services/실서비스.py` 로 스왑. 라우터 import 한 줄만 바꿀 것.

### 프론트엔드
- 단일 파일(index.html + style.css + app.js) 구조 유지. 컴포넌트 분리 불필요.
- `API` 상수 — `window.location.hostname === "localhost"` 일 때만 `http://localhost:8000/api`, 그 외(Vercel 배포)는 `/api`. 하드코딩 분산 금지.
- `state` 객체에 전역 상태 중앙화. 로컬 변수로 상태 분산 금지.
- CDN 버전 고정: Leaflet 1.9.4, Chart.js 4.4.0.

### CSS
- CSS 변수(`--bg`, `--accent`, `--danger` 등)만 사용. 인라인 색상코드 직접 기입 금지.
- 다크모드 전용. 라이트모드 고려 불필요.

---

## 데이터 규칙

### 격자 ID 형식
`G-{3자리 숫자}` (예: G-001 ~ G-210)

### CVI 등급 기준
| 범위 | 등급 | 색상 변수 |
|------|------|----------|
| ≥ 0.80 | 위험 | `--danger` (#dc2626) |
| 0.65 ~ 0.79 | 경계 | `--warn` (#ea580c) |
| 0.50 ~ 0.64 | 주의 | `--caution` (#ca8a04) |
| < 0.50 | 정상 | `--safe` (#16a34a) |

### LISA 유형
- HH: 고위험 집적 (부안·군산 집중)
- LL: 저위험 집적 (고창 전역)
- HL/LH: 이상 격자
- NS: 통계적으로 유의하지 않음

### 3중 취약 조건
야간(`hour >= 20 or hour < 6`) **AND** 만조(`tide_height_m >= 5.0m`) **AND** 안개(`visibility_km < 1.0`)

> 만조 시 선박이 해안선 깊숙이 진입 가능해 침투 난이도가 낮아진다. 간조는 갯벌 노출로 오히려 접근이 어렵다.

---

## Phase별 작업 흐름

### Phase 0 완료 (2026-06-24)
- FastAPI 백엔드 + 순수 HTML/JS/CSS 프론트엔드 (5탭) — 로컬 실행
- 더미 데이터 기반 전체 UI 구현 확인 (12개 API 엔드포인트)
- `services/data_pipeline.py` — 조위(KHOA TXT) + 기상(ASOS CSV) + 인구(SGIS SHP) 전처리
- `services/risk_calendar.py` — 과거 918일 실측 + 미래 30일 예측 서비스
- `routers/calendar.py` — 4개 캘린더 API 엔드포인트

### Phase 1 — Vercel 배포 + 실 데이터 연동 완성

**1-A. Vercel 배포 환경 (선행):**
1. `vercel.json` 작성 — 정적 프론트엔드 + `/api/*` 서버리스 라우팅
2. `api/index.py` 생성 — Vercel Python 런타임용 FastAPI ASGI 래퍼
3. `frontend/app.js` `API` 상수 → 환경 감지 방식으로 변경 (`/api` 상대 경로)
4. `backend/main.py` CORS — `https://*.vercel.app` 추가
5. `backend/data/processed/` `.gitignore`에서 제외 → git 포함

**1-B. 실 데이터 연동:**
1. `backend/services/cctv_loader.py` — `data/cctv_jeonbuk.csv` → 격자별 CCTV 수 매핑
2. `backend/services/cvi_calculator.py` — SHAP 가중치 기반 실 CVI 산출
3. `backend/routers/environment.py` — `dummy_environment` → 실 데이터 서비스로 교체

### 더미 데이터 폴백 정책
실 데이터 서비스가 미구현·오류·파일 누락 상태일 때는 더미 데이터로 서비스한다. 사용자에게 빈 화면을 보여주는 것보다 더미로라도 동작하는 상태가 우선이다.

```python
# 라우터에서 실 데이터 서비스가 준비됐을 때만 교체
try:
    from services.cvi_calculator import get_grids
except Exception:
    from data.dummy_grids import get_grids  # 실 데이터 불가 시 폴백
```

더미 파일(`dummy_*.py`)은 실 서비스와 동일한 함수 시그니처를 유지해야 한다. 교체 시 라우터 수정 없이 import 한 줄만 바꿀 것.

---

## Vercel 배포 주의사항
- `api/index.py` 진입점에서 `backend/` 모듈 import 시 Python path 설정 필요
- `assets.json` PUT 기능은 Vercel 서버리스 환경에서 파일 쓰기 불가 → Phase 2에서 DB 이전 전까지 읽기 전용
- `data/` 폴더 원본 CSV (군사 위치 정보)는 git 제외 유지; `backend/data/processed/` 는 git 포함
- 환경변수 `DATA_GO_KR_KEY`는 Vercel 프로젝트 설정 > Environment Variables에 등록
- CORS: 로컬(localhost:5173, 3000) + 배포(*.vercel.app) 모두 허용
- 기상청 ASOS API는 대량 요청 시 타임아웃 발생 → 분기별(3개월) 단위로 나눠 요청
