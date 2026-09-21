"""Read the locally supplied CAMBAY KMZ as a display-only airspace constraint layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from zipfile import ZipFile


def _tag_name(element: ElementTree.Element) -> str:
    return element.tag.rsplit("}", maxsplit=1)[-1]


def _first_text(element: ElementTree.Element, name: str) -> str:
    for child in element.iter():
        if _tag_name(child) == name and child.text:
            return child.text.strip()
    return ""


def _coordinates(value: str) -> list[list[float]]:
    points: list[list[float]] = []
    for item in value.split():
        values = item.split(",")
        if len(values) < 2:
            continue
        try:
            points.append([float(values[0]), float(values[1])])
        except ValueError:
            continue
    if len(points) >= 3 and points[0] != points[-1]:
        points.append(points[0])
    return points


def _zone_type(name: str) -> tuple[str, str]:
    if "CAMBAY" in name.upper().replace(" ", ""):
        return "prohibited", "Khu vực cấm bay"
    return "restricted", "Khu vực hạn chế bay"


def load_no_fly_zones(kmz_path: Path) -> dict[str, Any]:
    """Convert Polygon Placemarks in a KMZ/KML file to a GeoJSON collection."""
    if not kmz_path.is_file():
        raise FileNotFoundError(f"No-fly KMZ file was not found: {kmz_path}")

    with ZipFile(kmz_path) as archive:
        kml_name = next((entry.filename for entry in archive.infolist() if entry.filename.lower().endswith(".kml")), None)
        if not kml_name:
            raise ValueError("KMZ does not contain a KML document")
        root = ElementTree.fromstring(archive.read(kml_name))

    features: list[dict[str, Any]] = []
    for placemark in (element for element in root.iter() if _tag_name(element) == "Placemark"):
        name = _first_text(placemark, "name") or "Khu vực bay"
        style_url = _first_text(placemark, "styleUrl")
        zone_type, label = _zone_type(name)
        for polygon in (element for element in placemark.iter() if _tag_name(element) == "Polygon"):
            coordinate_text = _first_text(polygon, "coordinates")
            ring = _coordinates(coordinate_text)
            if len(ring) < 4:
                continue
            features.append(
                {
                    "type": "Feature",
                    "id": f"airspace-{len(features) + 1}",
                    "properties": {"name": name, "zone_type": zone_type, "label": label, "style_url": style_url},
                    "geometry": {"type": "Polygon", "coordinates": [ring]},
                }
            )
    if not features:
        raise ValueError("No Polygon no-fly zones were found in the KMZ")
    return {"type": "FeatureCollection", "features": features}
