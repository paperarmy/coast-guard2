from fastapi import APIRouter
from data.dummy_environment import get_current_environment, get_7day_forecast

router = APIRouter()


@router.get("/current")
def current_environment():
    return get_current_environment()


@router.get("/forecast")
def environment_forecast():
    return {"days": get_7day_forecast()}
