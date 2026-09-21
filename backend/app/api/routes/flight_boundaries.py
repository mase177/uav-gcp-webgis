from fastapi import APIRouter, HTTPException

from ...core.config import ADMIN_BOUNDARY_KML_PATH
from ...services.administrative_boundaries import find_administrative_matches


router = APIRouter(prefix="/flight-boundaries", tags=["flight boundaries"])


@router.post("/administrative-match")
def administrative_match(payload: dict):
    """Find only the communes intersecting a proposed GeoJSON flight boundary."""
    try:
        return find_administrative_matches(payload.get("aoi", payload), ADMIN_BOUNDARY_KML_PATH)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        # Surface a concise diagnostic in the local WebGIS instead of a blank 500 response.
        raise HTTPException(status_code=500, detail=f"Administrative-boundary analysis failed: {error}") from error
