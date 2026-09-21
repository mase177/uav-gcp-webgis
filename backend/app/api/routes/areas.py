from fastapi import APIRouter

from ...services.spatial import polygon_ring, road_segments

router = APIRouter(prefix="/areas", tags=["areas"])


@router.post("/validate")
def validate_area(payload: dict):
    ring = polygon_ring(payload["aoi"])
    segments = road_segments(payload["roads"])
    return {"valid": True, "aoi_vertices": len(ring) - 1, "road_segments": len(segments)}
