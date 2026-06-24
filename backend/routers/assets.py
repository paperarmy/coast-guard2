from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json, os

router = APIRouter()

ASSETS_FILE = os.path.join(os.path.dirname(__file__), "../data/assets.json")

# 초기 더미 자산 데이터
DEFAULT_ASSETS = [
    {"id": "D-001", "type": "drone", "label": "드론-1", "lat": 35.82, "lon": 126.55, "region": "부안", "active": True, "range_km": 5.0},
    {"id": "D-002", "type": "drone", "label": "드론-2", "lat": 35.71, "lon": 126.61, "region": "부안", "active": True, "range_km": 5.0},
    {"id": "D-003", "type": "drone", "label": "드론-3", "lat": 35.91, "lon": 126.52, "region": "군산", "active": False, "range_km": 5.0},
    {"id": "T-001", "type": "tod", "label": "TOD-1", "lat": 35.85, "lon": 126.50, "region": "부안", "active": True, "range_km": 3.0},
    {"id": "T-002", "type": "tod", "label": "TOD-2", "lat": 35.75, "lon": 126.58, "region": "부안", "active": True, "range_km": 3.0},
    {"id": "T-003", "type": "tod", "label": "TOD-3", "lat": 35.65, "lon": 126.52, "region": "군산", "active": True, "range_km": 3.0},
    {"id": "C-001", "type": "cctv", "label": "CCTV-군산항", "lat": 35.97, "lon": 126.71, "region": "군산", "active": True, "range_km": 0.5},
    {"id": "C-002", "type": "cctv", "label": "CCTV-부안방파제", "lat": 35.72, "lon": 126.49, "region": "부안", "active": True, "range_km": 0.5},
    {"id": "C-003", "type": "cctv", "label": "CCTV-고창해수욕장", "lat": 35.42, "lon": 126.48, "region": "고창", "active": True, "range_km": 0.5},
    {"id": "P-001", "type": "patrol", "label": "해경순찰-군산", "lat": 35.96, "lon": 126.69, "region": "군산", "active": True, "range_km": 10.0},
]


def _load():
    if os.path.exists(ASSETS_FILE):
        with open(ASSETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_ASSETS


def _save(data):
    try:
        with open(ASSETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        raise OSError("read-only")


class AssetUpdate(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    active: Optional[bool] = None
    label: Optional[str] = None


@router.get("")
def list_assets(asset_type: Optional[str] = None):
    assets = _load()
    if asset_type:
        assets = [a for a in assets if a["type"] == asset_type]
    return {"count": len(assets), "assets": assets}


@router.put("/{asset_id}")
def update_asset(asset_id: str, body: AssetUpdate):
    assets = _load()
    asset = next((a for a in assets if a["id"] == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="자산 없음")
    if body.lat is not None: asset["lat"] = body.lat
    if body.lon is not None: asset["lon"] = body.lon
    if body.active is not None: asset["active"] = body.active
    if body.label is not None: asset["label"] = body.label
    try:
        _save(assets)
    except OSError:
        raise HTTPException(status_code=503, detail="자산 위치 편집은 Phase 2(DB 연동) 이후 지원됩니다.")
    return asset
