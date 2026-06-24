from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import grids, alerts, environment, assets, calendar

app = FastAPI(
    title="해안경계 취약구간 모니터링 API",
    description="CVI 기반 실시간 해안경계 의사결정 지원 시스템",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(grids.router, prefix="/api/grids", tags=["격자"])
app.include_router(alerts.router, prefix="/api/alert", tags=["경보"])
app.include_router(environment.router, prefix="/api/environment", tags=["환경"])
app.include_router(assets.router, prefix="/api/assets", tags=["감시자산"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["위험캘린더"])


@app.get("/")
def root():
    return {"service": "CGIP API", "status": "running", "docs": "/docs"}
