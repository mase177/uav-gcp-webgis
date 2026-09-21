"""Streaming intersection checks against the supplied Vietnamese administrative KML.

The national source file is intentionally kept on the server (~280 MB).  The browser
receives only the communes that intersect the user's proposed flight boundary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.etree import ElementTree


Coordinate = tuple[float, float]


def _tag_name(element: ElementTree.Element) -> str:
    return element.tag.rsplit("}", maxsplit=1)[-1]


def _text(element: ElementTree.Element, tag: str) -> str:
    for child in element.iter():
        if _tag_name(child) == tag and child.text:
            return child.text.strip()
    return ""


def _coordinates(value: str) -> list[Coordinate]:
    coordinates: list[Coordinate] = []
    for item in value.split():
        parts = item.split(",")
        if len(parts) < 2:
            continue
        try:
            coordinates.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue
    if len(coordinates) >= 3 and coordinates[0] != coordinates[-1]:
        coordinates.append(coordinates[0])
    return coordinates


def _rings(geometry: dict[str, Any]) -> list[list[Coordinate]]:
    geometry_type = geometry.get("type")
    if geometry_type == "Polygon":
        polygons = [geometry.get("coordinates", [])]
    elif geometry_type == "MultiPolygon":
        polygons = geometry.get("coordinates", [])
    else:
        return []
    return [[(float(lon), float(lat)) for lon, lat, *_ in polygon[0]] for polygon in polygons if polygon and polygon[0]]


def _bounds(ring: list[Coordinate]) -> tuple[float, float, float, float]:
    longitudes, latitudes = zip(*ring)
    return min(longitudes), min(latitudes), max(longitudes), max(latitudes)


def _bounds_overlap(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> bool:
    return first[0] <= second[2] and first[2] >= second[0] and first[1] <= second[3] and first[3] >= second[1]


def _orientation(first: Coordinate, second: Coordinate, third: Coordinate) -> float:
    return (second[0] - first[0]) * (third[1] - first[1]) - (second[1] - first[1]) * (third[0] - first[0])


def _on_segment(point: Coordinate, start: Coordinate, end: Coordinate) -> bool:
    tolerance = 1e-10
    if abs(_orientation(start, end, point)) > tolerance:
        return False
    return min(start[0], end[0]) - tolerance <= point[0] <= max(start[0], end[0]) + tolerance and min(start[1], end[1]) - tolerance <= point[1] <= max(start[1], end[1]) + tolerance


def _segments_intersect(first_start: Coordinate, first_end: Coordinate, second_start: Coordinate, second_end: Coordinate) -> bool:
    first = _orientation(first_start, first_end, second_start)
    second = _orientation(first_start, first_end, second_end)
    third = _orientation(second_start, second_end, first_start)
    fourth = _orientation(second_start, second_end, first_end)
    if ((first > 0 > second) or (first < 0 < second)) and ((third > 0 > fourth) or (third < 0 < fourth)):
        return True
    return (abs(first) < 1e-10 and _on_segment(second_start, first_start, first_end)) or (abs(second) < 1e-10 and _on_segment(second_end, first_start, first_end)) or (abs(third) < 1e-10 and _on_segment(first_start, second_start, second_end)) or (abs(fourth) < 1e-10 and _on_segment(first_end, second_start, second_end))


def _point_in_ring(point: Coordinate, ring: list[Coordinate]) -> bool:
    inside = False
    for current, previous in zip(ring, [ring[-1], *ring[:-1]]):
        if _on_segment(point, current, previous):
            return True
        if (current[1] > point[1]) != (previous[1] > point[1]):
            x_intersection = (previous[0] - current[0]) * (point[1] - current[1]) / (previous[1] - current[1]) + current[0]
            if point[0] < x_intersection:
                inside = not inside
    return inside


def _rings_intersect(first: list[Coordinate], second: list[Coordinate]) -> bool:
    if len(first) < 4 or len(second) < 4 or not _bounds_overlap(_bounds(first), _bounds(second)):
        return False
    for first_start, first_end in zip(first, first[1:]):
        for second_start, second_end in zip(second, second[1:]):
            if _segments_intersect(first_start, first_end, second_start, second_end):
                return True
    return _point_in_ring(first[0], second) or _point_in_ring(second[0], first)


def _placemark_properties(placemark: ElementTree.Element, index: int) -> dict[str, str]:
    properties: dict[str, str] = {"name": _text(placemark, "name") or f"Xã/Phường {index}"}
    for element in placemark.iter():
        if _tag_name(element) != "Data" or not element.get("name"):
            continue
        properties[element.get("name", "")] = _text(element, "value")
    properties["name"] = properties.get("ten_xa") or properties["name"]
    return properties


def _placemark_rings(placemark: ElementTree.Element) -> list[list[Coordinate]]:
    rings: list[list[Coordinate]] = []
    for polygon in (element for element in placemark.iter() if _tag_name(element) == "Polygon"):
        outer_boundary = next((element for element in polygon.iter() if _tag_name(element) == "outerBoundaryIs"), polygon)
        ring = _coordinates(_text(outer_boundary, "coordinates"))
        if len(ring) >= 4:
            rings.append(ring)
    return rings


def find_administrative_matches(aoi: dict[str, Any], boundary_path: Path) -> dict[str, Any]:
    """Stream the provided national KML and return only administrative polygons meeting AOI."""
    if not boundary_path.is_file():
        raise FileNotFoundError(f"Administrative boundary KML was not found: {boundary_path}")
    aoi_geometry = aoi.get("geometry", aoi)
    aoi_rings = _rings(aoi_geometry)
    if not aoi_rings:
        raise ValueError("AOI must be a GeoJSON Polygon or MultiPolygon")

    matches: list[dict[str, Any]] = []
    index = 0
    for _event, placemark in ElementTree.iterparse(boundary_path, events=("end",)):
        if _tag_name(placemark) != "Placemark":
            continue
        index += 1
        rings = _placemark_rings(placemark)
        if rings and any(_rings_intersect(aoi_ring, boundary_ring) for aoi_ring in aoi_rings for boundary_ring in rings):
            properties = _placemark_properties(placemark, index)
            geometry_type = "Polygon" if len(rings) == 1 else "MultiPolygon"
            coordinates: Any = [rings[0]] if len(rings) == 1 else [[ring] for ring in rings]
            matches.append({"type": "Feature", "id": f"admin-{properties.get('ma_xa') or index}", "properties": properties, "geometry": {"type": geometry_type, "coordinates": coordinates}})
        placemark.clear()
    return {"source": boundary_path.name, "scanned_count": index, "match_count": len(matches), "matches": {"type": "FeatureCollection", "features": matches}}
