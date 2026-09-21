"""Survey-profile rules used to make the GCP optimizer transparent to operators.

These are planning recommendations, not a replacement for independent check points
or a photogrammetric accuracy assessment.
"""

from __future__ import annotations

from math import ceil
from typing import Any

from .spatial import meters_per_degree, polygon_ring


def approximate_aoi_area_ha(aoi: dict[str, Any]) -> float:
    """Return a local planar AOI area estimate in hectares for small UAV AOIs."""
    ring = polygon_ring(aoi)
    latitude = sum(point[1] for point in ring[:-1]) / max(len(ring) - 1, 1)
    lon_factor, lat_factor = meters_per_degree(latitude)
    projected = [(lon * lon_factor, lat * lat_factor) for lon, lat in ring]
    double_area = sum(
        first[0] * second[1] - second[0] * first[1]
        for first, second in zip(projected, projected[1:])
    )
    return abs(double_area) / 20_000


def recommend_survey_profile(request: Any) -> dict[str, Any]:
    """Derive explicit, conservative planning hints from the selected flight setup."""
    area_ha = max(approximate_aoi_area_ha(request.aoi), 0.01)
    method = request.positioning_method
    labels = {"rtk": "RTK", "ppk": "PPK", "non_rtk": "Không RTK/PPK"}
    method_factor = {"rtk": 0.72, "ppk": 0.84, "non_rtk": 1.0}[method]
    candidate_spacing = {"rtk": 45, "ppk": 35, "non_rtk": 25}[method]
    weights = {
        "rtk": {"coverage": 0.32, "uniformity": 0.23, "edge_interior": 0.18, "accessibility": 0.27},
        "ppk": {"coverage": 0.35, "uniformity": 0.25, "edge_interior": 0.20, "accessibility": 0.20},
        "non_rtk": {"coverage": 0.40, "uniformity": 0.28, "edge_interior": 0.20, "accessibility": 0.12},
    }[method].copy()
    terrain_factor = {"flat": 1.0, "rolling": 1.18, "complex": 1.40}[request.terrain_complexity]
    terrain_labels = {"flat": "Bằng phẳng", "rolling": "Đồi dốc nhẹ", "complex": "Phức tạp / công trình cao"}
    accuracy_factor = 1.25 if request.required_accuracy_cm <= 3 else 1.0 if request.required_accuracy_cm <= 5 else 0.85
    if request.terrain_complexity == "complex":
        weights["edge_interior"] += 0.05
        weights["accessibility"] -= 0.05
        candidate_spacing *= 0.8
    elif request.terrain_complexity == "rolling":
        candidate_spacing *= 0.9
    if request.required_accuracy_cm <= 3:
        candidate_spacing *= 0.85
        weights["coverage"] += 0.03
        weights["accessibility"] -= 0.03

    image_geometry_factor = 1.0
    if request.gsd_cm <= 2:
        image_geometry_factor *= 1.08
        candidate_spacing *= 0.9
    if request.forward_overlap_pct < 80 or request.side_overlap_pct < 70:
        image_geometry_factor *= 1.12
        candidate_spacing *= 0.9
        weights["coverage"] += 0.02
        weights["accessibility"] -= 0.02
    elif request.forward_overlap_pct >= 85 and request.side_overlap_pct >= 75:
        image_geometry_factor *= 0.95

    recommended_gcps = max(5, ceil((4 + area_ha / 1.5) * method_factor * terrain_factor * accuracy_factor * image_geometry_factor))
    recommended_gcps = min(recommended_gcps, 40)
    recommended_cps = max(3, ceil(recommended_gcps * 0.25))
    recommended_spacing = max(10, round(candidate_spacing / 5) * 5)
    return {
        "area_ha": round(area_ha, 2),
        "positioning_label": labels[method],
        "terrain_label": terrain_labels[request.terrain_complexity],
        "recommended_gcp_count": recommended_gcps,
        "recommended_cp_count": recommended_cps,
        "recommended_candidate_spacing_m": recommended_spacing,
        "effective_weights": {key: round(value, 2) for key, value in weights.items()},
        "flight_summary": f"Cao {request.flight_altitude_m:g} m · GSD {request.gsd_cm:g} cm · chồng phủ {request.forward_overlap_pct}/{request.side_overlap_pct}%",
        "notice": "Khuyến nghị lập kế hoạch. RTK/PPK vẫn cần Check Point độc lập để đánh giá độ chính xác.",
    }
