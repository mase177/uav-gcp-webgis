from fastapi import APIRouter, HTTPException

from ...core.config import MAX_CANDIDATES
from ...schemas import CandidateRequest
from ...services.spatial import generate_candidates, geojson_points

router = APIRouter(prefix="/gcps", tags=["gcps"])


@router.post("/candidates")
def create_candidates(request: CandidateRequest):
    try:
        candidates, _ = generate_candidates(
            request.aoi,
            request.roads,
            request.candidate_spacing_m,
            request.access_radius_m,
            MAX_CANDIDATES,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"count": len(candidates), "candidates": geojson_points(candidates)}

