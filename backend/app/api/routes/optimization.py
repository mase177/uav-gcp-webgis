from fastapi import APIRouter, HTTPException

from ...core.config import MAX_CANDIDATES
from ...schemas import OptimizationRequest, OptimizationWeights
from ...services.optimizer import build_baselines, genetic_optimize
from ...services.spatial import generate_candidates, geojson_points
from ...services.survey_profile import recommend_survey_profile

router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.post("/recommendation")
def get_recommendation(request: OptimizationRequest):
    try:
        return recommend_survey_profile(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/run")
def run_optimization(request: OptimizationRequest):
    try:
        survey_profile = recommend_survey_profile(request)
        if request.use_profile_weights:
            request.weights = OptimizationWeights(**survey_profile["effective_weights"])
        candidates, ring = generate_candidates(
            request.aoi,
            request.roads,
            request.candidate_spacing_m,
            request.access_radius_m,
            MAX_CANDIDATES,
        )
        if request.gcp_count > len(candidates):
            raise ValueError(f"Only {len(candidates)} accessible candidates are available")
        selected, score = genetic_optimize(candidates, ring, request)
        baselines = build_baselines(candidates, ring, request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return {
        "algorithm": "genetic_algorithm",
        "candidate_count": len(candidates),
        "gcp_count": len(selected),
        "survey_profile": survey_profile,
        "metrics": score,
        "baselines": baselines,
        "selected_gcps": geojson_points(selected, kind="selected_gcp"),
    }
