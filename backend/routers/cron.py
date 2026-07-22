"""
Vercel Cron Job 엔드포인트
/api/cron/refresh — 매시 정각 캐시 워밍 + 오래된 데이터 감지

Vercel 설정 (vercel.json):
  "crons": [{"path": "/api/cron/refresh", "schedule": "0 * * * *"}]

Vercel 서버리스는 프로세스 단위로 lru_cache가 유지되므로
이 엔드포인트가 호출되면 해당 인스턴스의 캐시를 초기화하고
새 데이터로 워밍한다.
"""
import sys
from fastapi import APIRouter, Header, HTTPException
from datetime import datetime
import os

router = APIRouter()

_CRON_SECRET = os.getenv("CRON_SECRET", "")


def _clear_caches():
    """모든 lru_cache 함수 캐시 초기화."""
    targets = [
        "services.cctv_loader",
        "services.vessel_loader",
        "services.population_loader",
        "services.stl_service",
        "services.environment_service",
        "services.cvi_calculator",
        "services.risk_calendar",
    ]
    cleared = []
    for mod_name in targets:
        mod = sys.modules.get(mod_name)
        if not mod:
            continue
        for attr_name in dir(mod):
            fn = getattr(mod, attr_name, None)
            if callable(fn) and hasattr(fn, "cache_clear"):
                fn.cache_clear()
                cleared.append(f"{mod_name}.{attr_name}")
    return cleared


def _warm_caches():
    """캐시 워밍: 핵심 데이터 미리 로드."""
    results = {}
    try:
        from services.cvi_calculator import get_all_grids
        grids = get_all_grids()
        results["grids"] = len(grids)
    except Exception as e:
        results["grids"] = f"ERROR: {e}"

    try:
        from services.environment_service import get_current_environment
        env = get_current_environment()
        results["environment"] = env.get("data_source", "ok")
    except Exception as e:
        results["environment"] = f"ERROR: {e}"

    try:
        from services.stl_service import get_monthly_table
        tbl = get_monthly_table()
        results["stl"] = f"{len(tbl)} months"
    except Exception as e:
        results["stl"] = f"ERROR: {e}"

    return results


@router.get("/refresh")
def cron_refresh(authorization: str = Header(default="")):
    """
    Vercel Cron에서 1시간마다 호출.
    CRON_SECRET 환경변수가 설정된 경우 Bearer 토큰으로 검증.
    """
    if not _CRON_SECRET or authorization != f"Bearer {_CRON_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    cleared = _clear_caches()
    warmed  = _warm_caches()

    return {
        "status":    "ok",
        "timestamp": datetime.now().isoformat(),
        "cleared":   cleared,
        "warmed":    warmed,
    }


@router.get("/status")
def cron_status(authorization: str = Header(default="")):
    """캐시 및 데이터 파일 상태 확인 (디버그용)."""
    if not _CRON_SECRET or authorization != f"Bearer {_CRON_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    from pathlib import Path
    processed = Path(__file__).resolve().parent.parent / "data" / "processed"

    files = {}
    for f in processed.iterdir():
        if f.suffix == ".csv":
            files[f.name] = f.stat().st_size

    return {
        "timestamp": datetime.now().isoformat(),
        "processed_files": files,
    }
