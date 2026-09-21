"""Optional PostgreSQL/PostGIS connection for the UAV WebGIS."""

from __future__ import annotations

import json
from typing import Any

try:
    from sqlalchemy import create_engine, text
except ModuleNotFoundError:
    create_engine = None
    text = None

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL and create_engine else None


def database_status() -> dict[str, Any]:
    if create_engine is None:
        return {"configured": bool(DATABASE_URL), "connected": False, "detail": "Missing dependency: install requirements.txt"}
    if engine is None:
        return {"configured": False, "connected": False}
    try:
        with engine.connect() as connection:
            row = connection.execute(text("SELECT current_database() AS database, PostGIS_Version() AS postgis_version")).mappings().one()
        return {"configured": True, "connected": True, **dict(row)}
    except Exception as error:  # Connection errors must not stop the map UI.
        return {"configured": True, "connected": False, "detail": str(error)}


def load_airspace_geojson() -> dict[str, Any] | None:
    """Read airspace polygons that were imported into uav.airspace_zones."""
    if engine is None or text is None:
        return None
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT airspace_id, name, zone_type, source_file, properties,
                       ST_AsGeoJSON(geom) AS geometry
                FROM uav.airspace_zones
                ORDER BY zone_type, airspace_id
                """
            )
        ).mappings().all()
    if not rows:
        return None
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": f"airspace-{row['airspace_id']}",
                "properties": {"name": row["name"], "zone_type": row["zone_type"], "source_file": row["source_file"], **(row["properties"] or {})},
                "geometry": json.loads(row["geometry"]),
            }
            for row in rows
        ],
    }
