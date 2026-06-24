# PRD: CoastGuard Intelligence Platform (CGIP)
**해안경계 취약구간 실시간 모니터링 웹 시스템**
버전: 0.3 | 최종 수정: 2026-06-24

---

## 1. 배경 및 목적

병역자원 감소(50만 명)로 드론·TOD·CCTV 등 감시 자산이 제한된 상황에서, CVI(해안침투 취약지수) 기반 데이터 의사결정 도구를 현장 경계 인원이 실시간으로 활용할 수 있게 한다.

**핵심 가설**: 야간 + 만조 + 안개 3중 취약 조건 동시 발생 격자에 자산을 집중하면, 균등 배치 대비 탐지 정밀도 5배·드론 집중도 10배 향상이 가능하다 (3건 사후검증, 공간 적중률 100%).

---

## 2. 사용자

| 역할 | 사용 방식 |
|------|----------|
| 해안경계 장교/부사관 | 매일 접속 → 오늘의 경계 중점 확인 → 출력 |
| 대대·연대 지휘관 | 주간 리포트 검토, 자산 재배치 승인 |
| 시스템 관리자 | 자산 위치 편집, 데이터 갱신 트리거 |

---

## 3. 기능 목록

### 3.1 대시보드 (F-01 ~ F-04)

| ID | 기능 | 우선순위 | 상태 |
|----|------|---------|------|
| F-01 | CVI 히트맵 지도 (격자별 색상 + 팝업) | Critical | ✅ 완료 |
| F-02 | 3중 취약일 경보 배너 (야간/만조/안개) | Critical | ✅ 완료 |
| F-03 | 실시간 환경 패널 (기상·조위·시간대) | High | ✅ 완료 (더미) |
| F-04 | 오늘의 경계 중점 카드 + 인쇄 | High | ✅ 완료 |

### 3.2 격자 분석 (F-05 ~ F-07)

| ID | 기능 | 우선순위 | 상태 |
|----|------|---------|------|
| F-05 | 격자 테이블 (정렬·필터·CSV 내보내기) | High | ✅ 완료 |
| F-06 | 격자 상세 패널 (SHAP 기여도 바차트) | High | ✅ 완료 |
| F-07 | STL 시계열 이상탐지 그래프 | Medium | ✅ 완료 (더미) |

### 3.3 감시 자산 (F-08 ~ F-09)

| ID | 기능 | 우선순위 | 상태 |
|----|------|---------|------|
| F-08 | 자산 배치 지도 (드론·TOD·CCTV·해경) | Medium | ✅ 완료 (더미) |
| F-09 | 자산 목록 및 활성/비활성 표시 | Medium | ✅ 완료 |
| F-10 | 자산 위치 편집 (PUT /api/assets) | Low | ✅ API 완료, UI 미구현 |

### 3.4 위험 캘린더 (F-11 ~ F-15)

| ID | 기능 | 우선순위 | 상태 |
|----|------|---------|------|
| F-11 | 월간 히트맵 캘린더 (실측+예측 구분) | High | ✅ 완료 |
| F-12 | 날짜 클릭 → 시간별 위험 분해 (막대) | High | ✅ 완료 |
| F-13 | 90일 실측 + 30일 예측 트렌드 차트 | High | ✅ 완료 |
| F-14 | 미래 예측 (계절통계 + 조석수식) | Medium | ✅ 완료 |
| F-15 | 예측 신뢰도 표시 (일수 경과에 따라 감소) | Medium | ✅ 완료 |

### 3.5 실 데이터 연동 (F-16 ~ F-19)

| ID | 기능 | 우선순위 | 상태 |
|----|------|---------|------|
| F-16 | KHOA 조위 전처리 → 만조 판단 | High | ✅ 완료 (25,656행) |
| F-17 | ASOS 기상 전처리 → 안개/야간 판단 | High | ✅ 완료 (26,304행) |
| F-18 | SGIS 인구격자 → 해안 격자 매핑 | High | ✅ 완료 (8,575격자) |
| F-19 | 실 CVI 재산출 (SHAP 가중치 적용) | Critical | 🔲 미구현 |

### 3.6 Vercel 배포 (F-20 ~ F-24) — Phase 1 핵심

| ID | 기능 | 우선순위 | 상태 |
|----|------|---------|------|
| F-20 | `vercel.json` — 라우팅 구성 (프론트/백엔드 분리) | Critical | 🔲 미구현 |
| F-21 | FastAPI → Vercel Serverless Function 변환 | Critical | 🔲 미구현 |
| F-22 | API URL 환경변수화 (`VITE_API_URL` or `window.ENV`) | Critical | 🔲 미구현 |
| F-23 | CORS 도메인 확장 (Vercel 배포 URL 추가) | High | 🔲 미구현 |
| F-24 | `processed/` CSV git 포함 (서버리스 접근용) | High | 🔲 미구현 |

### 3.7 고도화 (F-25 ~ F-29)

| ID | 기능 | 우선순위 | 상태 |
|----|------|---------|------|
| F-25 | 1시간 주기 자동 데이터 갱신 (Vercel Cron Jobs) | High | 🔲 미구현 |
| F-26 | 주간·월간 리포트 PDF 출력 | Medium | 🔲 미구현 |
| F-27 | 전국 확장 (충남 180격자 → 전국 2,600격자) | Low | 🔲 미구현 |
| F-28 | AIS 선박 실시간 연동 | Low | 🔲 미구현 |
| F-29 | 사용자 로그인 (JWT) | Low | 🔲 미구현 |

---

## 4. 개발 단계

### Phase 0 — 프로토타입 ✅ 완료 (2026-06-24)
- FastAPI 백엔드 + 순수 HTML/JS/CSS 프론트엔드 (5탭)
- 더미 데이터 기반 전체 UI 구현 확인
- 12개 API 엔드포인트 정상 작동 (로컬 환경)
- CCTV 8,284건 / 기상 26,304행 수집 완료
- 실 데이터 전처리 파이프라인 완료 (조위·기상·인구·위험 캘린더)

---

### Phase 1 — Vercel 배포 + 실 데이터 연동 완성 🔲 목표 (현재)

Phase 1의 목표는 **외부에서 접근 가능한 실 서비스 URL 확보**다.  
로컬 환경 의존성을 완전히 제거하고 Vercel에서 프론트·백엔드를 모두 서빙한다.

#### 1-A. Vercel 배포 환경 구성 (선행 작업)

| 항목 | 내용 |
|------|------|
| `vercel.json` 작성 | 프론트엔드(`frontend/`) 정적 서빙 + 백엔드(`/api/*`) 서버리스 라우팅 |
| `api/` 진입점 생성 | Vercel Python 런타임용 `api/index.py` (FastAPI ASGI 래퍼) |
| API URL 환경변수화 | `app.js`의 `API` 상수를 `window.API_BASE_URL` 또는 빌드 시 환경변수로 분리 |
| CORS 업데이트 | `main.py` CORS에 `https://*.vercel.app` 추가 |
| `processed/` CSV git 포함 | `.gitignore`에서 `backend/data/processed/` 제외 → 서버리스 함수 접근 허용 |
| `.env.example` 작성 | `DATA_GO_KR_KEY`, `VERCEL_URL` 등 환경변수 목록 문서화 |

> **주의**: `assets.json`은 Vercel 서버리스 환경에서 파일 쓰기가 불가하므로 PUT `/api/assets` 기능은 Phase 2에서 DB로 이전한다. Phase 1에서는 읽기 전용으로 동작.

#### 1-B. 실 데이터 연동 완성

| 항목 | 파일 | 우선순위 |
|------|------|---------|
| 격자별 CCTV 수 매핑 | `services/cctv_loader.py` | High |
| 실 CVI 재산출 (SHAP) | `services/cvi_calculator.py` | Critical |
| 환경 데이터 실 연동 | `routers/environment.py` → `tide_hourly.csv` 최신 행 | Medium |

#### 1-C. 완료 기준 (Definition of Done)

- [ ] `https://{프로젝트}.vercel.app` 에서 대시보드 정상 로드
- [ ] `/api/grids`, `/api/calendar/stats` 등 핵심 API 응답 1초 이내
- [ ] 더미 CVI가 아닌 실 데이터 기반 격자 점수 표시
- [ ] HTTPS 환경에서 CORS 오류 없음

---

### Phase 2 — 자동화·고도화 (목표: Phase 1 완료 후 4주)
- **Vercel Cron Jobs**: 기상(1h) / 조위(1h) 갱신 (`/api/cron/refresh`)
- **DB 도입**: Vercel Postgres 또는 Supabase → `assets.json` 파일 의존성 제거, 자산 위치 편집 복원
- **STL 시계열 이상탐지** 실 데이터 적용
- **자산 위치** 지도에서 드래그 편집 UI
- **주간 리포트** 자동 생성 (PDF)
- 환경 데이터 누락 시 캐시 fallback

---

### Phase 3 — 전국 확장 (목표: Phase 2 완료 후 8주)
- 충남 서해안 180격자 추가
- config 기반 지역 전환 (`region=충남` 파라미터)
- 전국 2,600격자 일괄 산출 파이프라인

---

## 5. 배포 아키텍처 (Phase 1 목표)

```
[Vercel Edge Network]
│
├── / (정적)     → frontend/index.html, style.css, app.js
│
└── /api/* (서버리스)
      └── api/index.py (FastAPI ASGI)
            ├── routers/grids.py
            ├── routers/alerts.py
            ├── routers/environment.py
            ├── routers/assets.py
            └── routers/calendar.py
                  └── data/processed/*.csv  (git 포함)
```

**Vercel 프로젝트 설정:**
- Framework Preset: `Other`
- Root Directory: `/`
- Build Command: (없음, 정적 파일)
- Output Directory: `frontend`
- Python 런타임: `@vercel/python` (자동 감지)

---

## 6. 기술 스택

| 계층 | 기술 | 비고 |
|------|------|------|
| Hosting | Vercel | 프론트(CDN) + 백엔드(Serverless) 통합 |
| Backend | Python FastAPI + ASGI | Vercel Python 런타임, `api/index.py` 진입점 |
| Frontend | 순수 HTML/CSS/JS | Node.js 없음, CDN으로 Leaflet + Chart.js |
| 지도 | Leaflet.js 1.9.4 | OpenStreetMap 타일 |
| 차트 | Chart.js 4.4.0 | 시계열 이상탐지 그래프 |
| DB | 없음 (Phase 1) | Phase 2에서 Vercel Postgres 또는 Supabase 도입 예정 |

---

## 7. 데이터 수집 현황

| 데이터 | 출처 | 수집 방식 | 상태 | 파일 |
|--------|------|----------|------|------|
| 기상 관측 (군산, 2023) | 기상청 ASOS | API | ✅ | `data/weather_gunsan_2023.csv` |
| 기상 관측 (군산, 2024~25) | 기상청 ASOS | API | ✅ | `data/weather_gunsan_2023_2025.csv` |
| 전북 CCTV 위치 | 행안부 공공데이터 | API | ✅ | `data/cctv_jeonbuk.csv` |
| 조위 관측 (군산항, 2023~2026) | KHOA | 직접 다운 | ✅ | `data/군산_*.txt` → `processed/tide_hourly.csv` |
| 인구 격자 (500m, 전북) | SGIS | 직접 다운 | ✅ | `data/sgis/` → `processed/population_grid.csv` |
| 어선 현황 통계 | MDIS | 수동 | 🔲 | — |
| 행정구역 경계 SHP | 국토정보플랫폼 | 직접 다운 | 🔲 | — |

---

## 8. API 목록

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/grids` | 전체 격자 (필터: region, lisa, cvi 범위) |
| GET | `/api/grids/summary` | 통계 요약 |
| GET | `/api/grids/top` | CVI 상위 N개 |
| GET | `/api/grids/hotspots` | HH 핫스팟 목록 |
| GET | `/api/grids/{id}` | 격자 상세 |
| GET | `/api/grids/{id}/timeseries` | STL 시계열 |
| GET | `/api/alert/today` | 오늘 경보 상태 |
| GET | `/api/alert/forecast` | 7일 예측 |
| GET | `/api/environment/current` | 현재 환경 (기상+조위) |
| GET | `/api/assets` | 감시 자산 목록 |
| PUT | `/api/assets/{id}` | 자산 위치·상태 수정 (Phase 2 이후 DB 기반) |
| GET | `/api/calendar/range` | 기간별 일별 위험 점수 (최대 1500일) |
| GET | `/api/calendar/day/{date}` | 특정일 시간별 24행 상세 |
| GET | `/api/calendar/forecast` | 미래 N일 예측 (최대 90일) |
| GET | `/api/calendar/stats` | 전체 통계 요약 |

---

## 9. 비기능 요구사항

| 항목 | 기준 |
|------|------|
| 배포 환경 | Vercel (프론트+백엔드 통합) |
| 환경 갱신 주기 | 1시간 (Phase 2 Vercel Cron 이후) |
| 지도 로딩 | 3초 이내 |
| API 응답 | 1초 이내 |
| 서버리스 Cold Start | 3초 이내 허용 (첫 요청) |
| 오프라인 대응 | 최근 캐시 데이터 유지 |
| 브라우저 | Chrome 최신 버전 |
| 해상도 | 1920×1080 (지휘소 모니터) |
| 환경변수 | Vercel 프로젝트 설정 → `DATA_GO_KR_KEY` 등록 |
