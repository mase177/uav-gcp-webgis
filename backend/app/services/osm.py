"""Download a compact road network from OpenStreetMap through Overpass."""

from __future__ import annotations

import json
from math import ceil, cos, pi, sqrt
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .spatial import bounding_box, polygon_ring

OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
TARGET_TILE_AREA_KM2 = 8.0
MAX_QUERY_TILES = 25


class OSMDownloadError(ValueError):
    """A recoverable issue while requesting a public OpenStreetMap service."""


def _area_km2(ring: list[tuple[float, float]]) -> float:
    min_lon, min_lat, max_lon, max_lat = bounding_box(ring)
    mean_lat = (min_lat + max_lat) / 2
    width_m = (max_lon - min_lon) * 111_320 * cos(mean_lat * pi / 180)
    height_m = (max_lat - min_lat) * 110_540
    return abs(width_m * height_m) / 1_000_000


def _overpass_query(south: float, west: float, north: float, east: float) -> str:
    # Keep only roads usable by a field team in a vehicle. Footpaths can be
    # supplied separately by the operator when they are relevant to the survey.
    return f"""[out:json][timeout:25];
way[highway~\"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|service|living_street|track)$\"]
({south:.7f},{west:.7f},{north:.7f},{east:.7f});
out geom;"""


def _query_tiles(ring: list[tuple[float, float]], area_km2: float) -> list[tuple[float, float, float, float]]:
    """Split a wide AOI bounding box into safe Overpass query tiles."""
    west, south, east, north = bounding_box(ring)
    requested_tiles = max(1, ceil(area_km2 / TARGET_TILE_AREA_KM2))
    if requested_tiles > MAX_QUERY_TILES:
        raise OSMDownloadError(
            f"AOI có phạm vi {area_km2:.2f} km² cần {requested_tiles} lượt tải đường, vượt ngưỡng {MAX_QUERY_TILES} lượt. "
            "Hãy chia dự án thành các đợt khảo sát nhỏ hơn hoặc nạp tệp đường cục bộ."
        )
    width = max(east - west, 1e-12)
    height = max(north - south, 1e-12)
    columns = max(1, ceil(sqrt(requested_tiles * width / height)))
    rows = ceil(requested_tiles / columns)
    lon_step = (east - west) / columns
    lat_step = (north - south) / rows
    return [
        (
            west + column * lon_step,
            south + row * lat_step,
            west + (column + 1) * lon_step,
            south + (row + 1) * lat_step,
        )
        for row in range(rows)
        for column in range(columns)
    ]


def _download_tile(south: float, west: float, north: float, east: float) -> dict:
    request_data = urlencode({"data": _overpass_query(south, west, north, east)}).encode("utf-8")
    failures = []
    for endpoint in OVERPASS_URLS:
        request = Request(endpoint, data=request_data, headers={"User-Agent": "uav-gcp-webgis/0.1"}, method="POST")
        try:
            with urlopen(request, timeout=35) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            failures.append(f"HTTP {error.code}")
        except (URLError, TimeoutError, json.JSONDecodeError):
            failures.append("không kết nối được")
    raise OSMDownloadError(
        "Không thể tải một ô mạng đường OSM (" + ", ".join(failures) + "). Hãy thử lại sau hoặc nạp tệp đường cục bộ."
    )


def overpass_to_geojson(payload: dict, allow_empty: bool = False) -> dict:
    """Convert Overpass ways with geometries to a compact GeoJSON collection."""
    features = []
    for element in payload.get("elements", []):
        geometry = element.get("geometry") or []
        coordinates = [[node["lon"], node["lat"]] for node in geometry if "lon" in node and "lat" in node]
        if len(coordinates) < 2:
            continue
        tags = element.get("tags") or {}
        features.append(
            {
                "type": "Feature",
                "id": f"osm-way-{element.get('id', len(features) + 1)}",
                "properties": {
                    "source": "OpenStreetMap via Overpass",
                    "osm_way_id": element.get("id"),
                    "name": tags.get("name", "Đường OSM"),
                    "highway": tags.get("highway", "unknown"),
                    "surface": tags.get("surface"),
                    "access": tags.get("access"),
                },
                "geometry": {"type": "LineString", "coordinates": coordinates},
            }
        )
    if not features and not allow_empty:
        raise OSMDownloadError("OpenStreetMap không trả về đoạn đường phù hợp trong AOI này.")
    return {"type": "FeatureCollection", "features": features}


def download_osm_roads(aoi: dict) -> dict:
    """Request OSM roads, splitting a wide AOI into safe public-API queries."""
    ring = polygon_ring(aoi)
    area_km2 = _area_km2(ring)
    tiles = _query_tiles(ring, area_km2)
    roads_by_id: dict[str, dict] = {}
    for west, south, east, north in tiles:
        tile_roads = overpass_to_geojson(_download_tile(south, west, north, east), allow_empty=True)
        for feature in tile_roads["features"]:
            feature_id = feature["id"]
            existing = roads_by_id.get(feature_id)
            if existing is None or len(feature["geometry"]["coordinates"]) > len(existing["geometry"]["coordinates"]):
                roads_by_id[feature_id] = feature
    roads = {"type": "FeatureCollection", "features": list(roads_by_id.values())}
    if not roads["features"]:
        raise OSMDownloadError("OpenStreetMap không trả về đoạn đường phù hợp trong AOI này.")
    return {
        "roads": roads,
        "source": "OpenStreetMap via Overpass",
        "way_count": len(roads["features"]),
        "query_area_km2": round(area_km2, 3),
        "query_tile_count": len(tiles),
    }
