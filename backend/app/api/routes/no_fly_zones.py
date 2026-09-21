from fastapi import APIRouter, HTTPException

from ...core.database import load_airspace_geojson
from ...core.config import NO_FLY_KMZ_PATH
from ...services.no_fly_zones import load_no_fly_zones

router = APIRouter(prefix="/no-fly-zones", tags=["airspace"])


@router.get("")
def get_no_fly_zones():
    """Return airspace GeoJSON from PostGIS, falling back to the supplied KMZ."""
    try:
        zones = load_airspace_geojson()
    except Exception:
        zones = None
    if zones:
        return {"source": "PostGIS: uav.airspace_zones", "zone_count": len(zones["features"]), "zones": zones}
    try:
        zones = load_no_fly_zones(NO_FLY_KMZ_PATH)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return {"source": "data/cambay/CAMBAY.kmz", "zone_count": len(zones["features"]), "zones": zones}
