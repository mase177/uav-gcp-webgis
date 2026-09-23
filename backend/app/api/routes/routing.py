from fastapi import APIRouter, HTTPException

from ...schemas import RouteRequest
from ...services.routing import plan_route

router = APIRouter(prefix="/routing", tags=["routing"])


@router.post("/plan")
def build_route(request: RouteRequest):
    try:
        coordinates = []
        access_waypoint_count = 0
        for item in request.gcps:
            gcp_coordinate = item["geometry"]["coordinates"]
            access_coordinate = item.get("properties", {}).get("access_point")
            if isinstance(access_coordinate, list) and len(access_coordinate) == 2:
                coordinates.append(access_coordinate)
                access_waypoint_count += 1
            else:
                coordinates.append(gcp_coordinate)
        route = plan_route(coordinates, request.start, request.return_to_start, request.vehicle)
        stop_order = route["properties"].get("stop_order", [])
        route["properties"]["survey_order"] = [
            str(request.gcps[index].get("id", f"GCP {index + 1}"))
            for index in stop_order
            if isinstance(index, int) and 0 <= index < len(request.gcps)
        ]
        if access_waypoint_count:
            route["properties"]["access_waypoint_count"] = access_waypoint_count
            route["properties"]["note"] += (
                f" Tuyến đi qua {access_waypoint_count} điểm tiếp cận gần đường; "
                "đoạn từ đường đến vị trí GCP cần được kiểm tra khi khảo sát thực địa."
            )
        return route
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail="GCPs must be GeoJSON Point features") from error
