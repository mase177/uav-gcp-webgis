from fastapi import APIRouter, HTTPException

from ...schemas import OSMRoadRequest
from ...services.osm import OSMDownloadError, download_osm_roads

router = APIRouter(prefix="/osm", tags=["openstreetmap"])


@router.post("/roads")
def fetch_osm_roads(request: OSMRoadRequest):
    try:
        return download_osm_roads(request.aoi)
    except (ValueError, OSMDownloadError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
