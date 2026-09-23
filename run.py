"""Development entry point for the lightweight UAV GCP WebGIS."""

import uvicorn


if __name__ == "__main__":
    # Windows reload spawns a second interpreter process.  In this local
    # environment that child can be blocked, so use one stable server process.
    # Restart run.py after editing backend code during development.
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8001)
