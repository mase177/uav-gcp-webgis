from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SpatialInput(BaseModel):
    """GeoJSON input shared by candidate generation and optimization."""

    aoi: dict[str, Any]
    roads: dict[str, Any]
    candidate_spacing_m: float = Field(default=45, ge=10, le=500)
    access_radius_m: float = Field(default=80, ge=5, le=1000)

    @field_validator("aoi")
    @classmethod
    def aoi_is_geojson(cls, value: dict[str, Any]) -> dict[str, Any]:
        if value.get("type") not in {"Feature", "Polygon", "MultiPolygon"}:
            raise ValueError("AOI must be a GeoJSON Polygon or Feature")
        return value

    @field_validator("roads")
    @classmethod
    def roads_are_geojson(cls, value: dict[str, Any]) -> dict[str, Any]:
        if value.get("type") not in {"FeatureCollection", "Feature", "LineString", "MultiLineString"}:
            raise ValueError("roads must be GeoJSON line data")
        return value


class CandidateRequest(SpatialInput):
    pass


class OSMRoadRequest(BaseModel):
    aoi: dict[str, Any]

    @field_validator("aoi")
    @classmethod
    def aoi_is_geojson(cls, value: dict[str, Any]) -> dict[str, Any]:
        if value.get("type") not in {"Feature", "Polygon", "MultiPolygon"}:
            raise ValueError("AOI must be a GeoJSON Polygon or Feature")
        return value


class OptimizationWeights(BaseModel):
    coverage: float = Field(default=0.35, ge=0, le=1)
    uniformity: float = Field(default=0.25, ge=0, le=1)
    edge_interior: float = Field(default=0.20, ge=0, le=1)
    accessibility: float = Field(default=0.20, ge=0, le=1)


class OptimizationRequest(SpatialInput):
    gcp_count: int = Field(default=8, ge=3, le=40)
    population_size: int = Field(default=48, ge=12, le=160)
    generations: int = Field(default=80, ge=10, le=240)
    mutation_rate: float = Field(default=0.16, ge=0.01, le=0.8)
    positioning_method: Literal["rtk", "ppk", "non_rtk"] = "non_rtk"
    required_accuracy_cm: float = Field(default=5, ge=1, le=20)
    terrain_complexity: Literal["flat", "rolling", "complex"] = "flat"
    flight_altitude_m: float = Field(default=100, ge=20, le=500)
    gsd_cm: float = Field(default=3, ge=0.5, le=20)
    forward_overlap_pct: int = Field(default=80, ge=60, le=95)
    side_overlap_pct: int = Field(default=70, ge=60, le=95)
    use_profile_weights: bool = True
    seed: int | None = None
    weights: OptimizationWeights = Field(default_factory=OptimizationWeights)


class RouteRequest(BaseModel):
    gcps: list[dict[str, Any]] = Field(min_length=2, max_length=25)
    start: list[float] | None = None
    return_to_start: bool = True
    vehicle: Literal["car", "motorcycle"] = "car"

    @field_validator("start")
    @classmethod
    def valid_start(cls, value: list[float] | None) -> list[float] | None:
        if value is not None and len(value) != 2:
            raise ValueError("start must be [longitude, latitude]")
        return value
