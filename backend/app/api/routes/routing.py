from fastapi import APIRouter, HTTPException

from ...schemas import RouteRequest
from ...services.routing import plan_route

router = APIRouter(prefix="/routing", tags=["routing"])


@router.post("/plan")
def build_route(request: RouteRequest):
    try:
        coordinates = [item["geometry"]["coordinates"] for item in request.gcps]
        route, total_distance = plan_route(coordinates, request.start, request.return_to_start)
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail="GCPs must be GeoJSON Point features") from error
    return {
        "type": "Feature",
        "properties": {
            "method": "nearest_neighbour_2opt",
            "distance_m": round(total_distance, 1),
            "stops": len(coordinates),
            "note": "Route order is a lightweight field-planning heuristic; replace with a road-graph shortest path when OSM data is available.",
        },
        "geometry": {"type": "LineString", "coordinates": route},
    }

