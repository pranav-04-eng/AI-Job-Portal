"""Central configuration shared by all services.

Every service loads the same .env (backend/.env) so they share GROQ_API_KEY and,
crucially, the same JWT_SECRET — tokens minted by auth-service must validate in
the other services.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# backend/.env regardless of which service's cwd we were launched from
_BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND_DIR / ".env")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# Shared signing secret for JWTs. Override in .env for anything real.
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "720"))  # 12h

# Where each service lives. The gateway (:8000) proxies to these; jobs-service
# calls screening-service directly for the apply orchestration.
# Services live on 90xx to avoid colliding with other local stacks that
# commonly grab 80xx (override any of these via .env if needed).
AUTH_URL = os.environ.get("AUTH_URL", "http://localhost:9001")
JOBS_URL = os.environ.get("JOBS_URL", "http://localhost:9002")
SCREENING_URL = os.environ.get("SCREENING_URL", "http://localhost:9003")
INTERVIEW_URL = os.environ.get("INTERVIEW_URL", "http://localhost:9004")

# Frontend origin allowed through CORS (gateway only — services sit behind it).
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")

# Resume-screening gate: applications scoring below this are auto-rejected and
# never reach the voice interview. Tune per how strict the funnel should be.
SCREEN_PASS_THRESHOLD = int(os.environ.get("SCREEN_PASS_THRESHOLD", "60"))

# Each service keeps its own SQLite file under backend/data/.
DATA_DIR = _BACKEND_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def db_path(name: str) -> str:
    """SQLAlchemy URL for a service-owned SQLite file, e.g. db_path('auth')."""
    return f"sqlite:///{DATA_DIR / (name + '.db')}"
