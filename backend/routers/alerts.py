from fastapi import APIRouter
from data.dummy_environment import get_current_environment, get_7day_forecast
from data.dummy_grids import get_top_grids

router = APIRouter()


@router.get("/today")
def today_alert():
    env = get_current_environment()
    top5 = get_top_grids(5)
    triple = env["triple_risk"]

    return {
        "alert_level": triple["level"],
        "triple_risk": triple,
        "environment_snapshot": {
            "is_night": env["time"]["is_night"],
            "is_fog": env["weather"]["is_fog"],
            "visibility_km": env["weather"]["visibility_km"],
            "is_high_tide": env["tide"]["is_high_tide"],
            "tide_height_m": env["tide"]["height_m"],
        },
        "top_priority_grids": [
            {
                "grid_id": g["grid_id"],
                "region": g["region"],
                "cvi": g["cvi"],
                "cvi_level": g["cvi_level"],
                "lisa": g["lisa"],
                "grid_type": g["grid_type"],
                "actions": g["recommended_actions"][:2],
            }
            for g in top5
        ],
        "message": _build_alert_message(triple, env),
    }


@router.get("/forecast")
def forecast_alert():
    return {"forecast": get_7day_forecast()}


def _build_alert_message(triple: dict, env: dict) -> str:
    components = triple["components"]
    active = [k for k, v in components.items() if v]
    label = {"night": "야간", "high_tide": "만조", "fog": "안개"}
    if triple["active"]:
        return f"3중 취약 조건 동시 충족 ({' + '.join(label[k] for k in active)}) — 즉각 경계 강화 요망"
    elif len(active) == 2:
        return f"2개 취약 조건 충족 ({' + '.join(label[k] for k in active)}) — 경계 강화 권고"
    elif len(active) == 1:
        return f"취약 조건 1개 ({label[active[0]]}) — 주의 유지"
    return "현재 취약 조건 없음 — 정상 경계 유지"
