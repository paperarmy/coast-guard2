from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from data.dummy_grids import get_all_grids, get_grid_by_id, get_top_grids, get_hh_grids
from data.dummy_environment import get_timeseries_anomaly

router = APIRouter()


@router.get("")
def list_grids(
    region: Optional[str] = Query(None, description="군산|부안|고창"),
    lisa: Optional[str] = Query(None, description="HH|LL|HL|LH|NS"),
    min_cvi: float = Query(0.0, ge=0.0, le=1.1),
    max_cvi: float = Query(1.1, ge=0.0, le=1.1),
    limit: int = Query(210, le=210),
):
    grids = get_all_grids()
    if region:
        grids = [g for g in grids if g["region"] == region]
    if lisa:
        grids = [g for g in grids if g["lisa"] == lisa]
    grids = [g for g in grids if min_cvi <= g["cvi"] <= max_cvi]
    return {"total": len(grids), "grids": grids[:limit]}


@router.get("/top")
def top_grids(n: int = Query(10, le=50, description="상위 N개")):
    return {"grids": get_top_grids(n)}


@router.get("/hotspots")
def hotspot_grids():
    hh = get_hh_grids()
    return {"count": len(hh), "grids": hh}


@router.get("/summary")
def grid_summary():
    grids = get_all_grids()
    lisa_counts = {}
    region_avg = {}
    for g in grids:
        lisa_counts[g["lisa"]] = lisa_counts.get(g["lisa"], 0) + 1
        r = g["region"]
        if r not in region_avg:
            region_avg[r] = []
        region_avg[r].append(g["cvi"])

    return {
        "total_grids": len(grids),
        "avg_cvi": round(sum(g["cvi"] for g in grids) / len(grids), 3),
        "max_cvi": max(g["cvi"] for g in grids),
        "min_cvi": min(g["cvi"] for g in grids),
        "lisa_distribution": lisa_counts,
        "region_avg_cvi": {r: round(sum(v)/len(v), 3) for r, v in region_avg.items()},
        "danger_count": len([g for g in grids if g["cvi"] >= 0.80]),
        "warning_count": len([g for g in grids if 0.65 <= g["cvi"] < 0.80]),
    }


@router.get("/{grid_id}")
def get_grid(grid_id: str):
    grid = get_grid_by_id(grid_id)
    if not grid:
        raise HTTPException(status_code=404, detail=f"격자 {grid_id} 없음")
    return grid


@router.get("/{grid_id}/timeseries")
def grid_timeseries(grid_id: str, days: int = Query(30, le=365)):
    grid = get_grid_by_id(grid_id)
    if not grid:
        raise HTTPException(status_code=404, detail=f"격자 {grid_id} 없음")
    series = get_timeseries_anomaly(grid_id, days)
    return {"grid_id": grid_id, "region": grid["region"], "series": series}
