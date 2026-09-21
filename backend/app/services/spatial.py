"""Dependency-light GeoJSON utilities used by the GCP optimization service.

The project intentionally avoids a database and heavy geospatial stack for the first
research prototype. All coordinates are WGS84; local meter estimates are adequate for
small UAV survey areas and can later be replaced with projected PostGIS operations.
"""

from __future__ import annotations

from math import cos, hypot, pi
from statistics import mean, pstdev
from typing import Any, Iterable

Coordinate = tuple[float, float]  # (longitude, latitude)


def _geometry(geojson: dict[str, Any]) -> dict[str, Any]:
    return geojson.get("geometry", geojson)


def polygon_ring(aoi: dict[str, Any]) -> list[Coordinate]:
    geometry = _geometry(aoi)
    if geometry.get("type") == "Polygon":
        ring = geometry["coordinates"][0]
    elif geometry.get("type") == "MultiPolygon":
        ring = geometry["coordinates"][0][0]
    else:
        raise ValueError("AOI must contain a Polygon or MultiPolygon geometry")
    if len(ring) < 4:
        raise ValueError("AOI polygon requires at least three vertices")
    points = [(float(lon), float(lat)) for lon, lat in ring]
    return points if points[0] == points[-1] else points + [points[0]]


def road_segments(roads: dict[str, Any]) -> list[tuple[Coordinate, Coordinate]]:
    def iter_geometries(value: dict[str, Any]) -> Iterable[dict[str, Any]]:
        geo_type = value.get("type")
        if geo_type == "FeatureCollection":
            for feature in value.get("features", []):
                yield from iter_geometries(feature)
        elif geo_type == "Feature":
            geometry = value.get("geometry")
            if geometry:
                yield geometry
        else:
            yield value

    segments: list[tuple[Coordinate, Coordinate]] = []
    for geometry in iter_geometries(roads):
        geo_type = geometry.get("type")
        lines = [geometry.get("coordinates", [])] if geo_type == "LineString" else geometry.get("coordinates", [])
        if geo_type not in {"LineString", "MultiLineString"}:
            continue
        for line in lines:
            coordinates = [(float(lon), float(lat)) for lon, lat in line]
            segments.extend(zip(coordinates, coordinates[1:]))
    if not segments:
        raise ValueError("At least one LineString road is required")
    return segments


def meters_per_degree(latitude: float) -> tuple[float, float]:
    return 111_320 * cos(latitude * pi / 180), 110_540


def distance_m(a: Coordinate, b: Coordinate) -> float:
    lon_factor, lat_factor = meters_per_degree((a[1] + b[1]) / 2)
    return hypot((a[0] - b[0]) * lon_factor, (a[1] - b[1]) * lat_factor)


def distance_to_segment_m(point: Coordinate, start: Coordinate, end: Coordinate) -> float:
    lon_factor, lat_factor = meters_per_degree(point[1])
    px, py = point[0] * lon_factor, point[1] * lat_factor
    ax, ay = start[0] * lon_factor, start[1] * lat_factor
    bx, by = end[0] * lon_factor, end[1] * lat_factor
    dx, dy = bx - ax, by - ay
    denominator = dx * dx + dy * dy
    if denominator == 0:
        return hypot(px - ax, py - ay)
    ratio = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denominator))
    return hypot(px - (ax + ratio * dx), py - (ay + ratio * dy))


def point_in_polygon(point: Coordinate, ring: list[Coordinate]) -> bool:
    lon, lat = point
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        crosses = (y1 > lat) != (y2 > lat)
        if crosses and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def bounding_box(ring: list[Coordinate]) -> tuple[float, float, float, float]:
    longitudes, latitudes = zip(*ring)
    return min(longitudes), min(latitudes), max(longitudes), max(latitudes)


def generate_candidates(
    aoi: dict[str, Any], roads: dict[str, Any], spacing_m: float, access_radius_m: float, max_candidates: int
) -> tuple[list[dict[str, Any]], list[Coordinate]]:
    ring = polygon_ring(aoi)
    segments = road_segments(roads)
    min_lon, min_lat, max_lon, max_lat = bounding_box(ring)
    lon_factor, lat_factor = meters_per_degree((min_lat + max_lat) / 2)
    lon_step = spacing_m / lon_factor
    lat_step = spacing_m / lat_factor
    candidates: list[dict[str, Any]] = []

    latitude = min_lat + lat_step / 2
    while latitude <= max_lat and len(candidates) < max_candidates:
        longitude = min_lon + lon_step / 2
        while longitude <= max_lon and len(candidates) < max_candidates:
            coordinate = (longitude, latitude)
            if point_in_polygon(coordinate, ring):
                access_distance = min(distance_to_segment_m(coordinate, start, end) for start, end in segments)
                if access_distance <= access_radius_m:
                    candidates.append(
                        {
                            "id": f"candidate-{len(candidates) + 1}",
                            "coordinate": [round(longitude, 7), round(latitude, 7)],
                            "access_distance_m": round(access_distance, 1),
                        }
                    )
            longitude += lon_step
        latitude += lat_step

    if not candidates:
        raise ValueError("No candidate GCPs were found. Increase access radius or check AOI and roads.")
    return candidates, ring


def geojson_points(candidates: list[dict[str, Any]], kind: str = "candidate") -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": candidate["id"],
                "properties": {"kind": kind, "access_distance_m": candidate.get("access_distance_m")},
                "geometry": {"type": "Point", "coordinates": candidate["coordinate"]},
            }
            for candidate in candidates
        ],
    }


def _sample_points(ring: list[Coordinate], density: int = 9) -> list[Coordinate]:
    min_lon, min_lat, max_lon, max_lat = bounding_box(ring)
    points: list[Coordinate] = []
    for row in range(density):
        for column in range(density):
            point = (
                min_lon + (column + 0.5) * (max_lon - min_lon) / density,
                min_lat + (row + 0.5) * (max_lat - min_lat) / density,
            )
            if point_in_polygon(point, ring):
                points.append(point)
    return points


def score_selection(
    selected: list[dict[str, Any]], ring: list[Coordinate], spacing_m: float, access_radius_m: float, weights: dict[str, float]
) -> dict[str, float]:
    points = [tuple(item["coordinate"]) for item in selected]
    sample_points = _sample_points(ring)
    coverage_radius = max(spacing_m * 1.25, 45)
    coverage = mean(float(min(distance_m(sample, point) for point in points) <= coverage_radius) for sample in sample_points)

    nearest_distances = [min(distance_m(point, other) for other in points if other != point) for point in points] if len(points) > 1 else [spacing_m]
    uniformity = 1 / (1 + (pstdev(nearest_distances) / max(mean(nearest_distances), 1)))

    boundary_segments = list(zip(ring, ring[1:]))
    boundary_distances = [min(distance_to_segment_m(point, start, end) for start, end in boundary_segments) for point in points]
    edge_share = sum(distance <= max(spacing_m * 1.4, 65) for distance in boundary_distances) / len(points)
    edge_interior = max(0.0, 1 - abs(edge_share - 0.35) / 0.35)

    accessibility = mean(max(0.0, 1 - item["access_distance_m"] / access_radius_m) for item in selected)
    components = {
        "coverage": coverage,
        "uniformity": uniformity,
        "edge_interior": edge_interior,
        "accessibility": accessibility,
    }
    total_weight = sum(weights.values()) or 1
    components["fitness"] = sum(components[key] * weights.get(key, 0) for key in components if key != "fitness") / total_weight
    return {key: round(value, 4) for key, value in components.items()}

