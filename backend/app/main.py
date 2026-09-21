from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import areas, flight_boundaries, gcps, no_fly_zones, optimization, routing
from .core.config import FRONTEND_DIR
from .core.database import database_status

app = FastAPI(
    title="UAV GCP WebGIS",
    version="0.1.0",
    description="Accessibility-aware genetic optimization for UAV ground control point placement.",
)

app.include_router(areas.router, prefix="/api")
app.include_router(flight_boundaries.router, prefix="/api")
app.include_router(gcps.router, prefix="/api")
app.include_router(no_fly_zones.router, prefix="/api")
app.include_router(optimization.router, prefix="/api")
app.include_router(routing.router, prefix="/api")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "ok", "storage": "postgresql_postgis", "focus": "ga_accessibility_optimization", "database": database_status()}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


# Also serve relative frontend assets at the root. This lets index.html work
# both through FastAPI and when a user opens it directly from the folder.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
