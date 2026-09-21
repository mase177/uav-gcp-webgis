from os import getenv
from pathlib import Path

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_DIR / ".env")
FRONTEND_DIR = PROJECT_DIR / "frontend"
NO_FLY_KMZ_PATH = PROJECT_DIR / "data" / "cambay" / "CAMBAY.kmz"
ADMIN_BOUNDARY_KML_PATH = PROJECT_DIR / "data" / "Ranh_Vietnam" / "Việt Nam (phường xã) - 34.kml"
DATABASE_URL = getenv("DATABASE_URL", "")
MAX_CANDIDATES = 750
MAX_GCP_COUNT = 40
MAX_POPULATION = 160
MAX_GENERATIONS = 240
