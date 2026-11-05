from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Must be set before any `backend.*` module is imported: Settings() reads these
# once at import time, and the FastAPI app creates its tables on import too.
_TEST_DB_PATH = Path(tempfile.gettempdir()) / "idcolis_pytest_runtime.db"
_TEST_DB_PATH.unlink(missing_ok=True)
os.environ["IDCOLIS_DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH.as_posix()}"
os.environ["IDCOLIS_ENV"] = "development"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app import app
from backend.db.session import SessionLocal
from backend.models import User, UserAgency


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, *, email: str | None = None, name: str | None = None, password: str, agency: str | None = None, station: str | None = None) -> dict:
    payload = {"password": password, "agency": agency, "station": station}
    if email:
        payload["email"] = email
    if name:
        payload["name"] = name
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(session: dict) -> dict:
    return {"Authorization": f"Bearer {session['access_token']}"}


@pytest.fixture
def station_assignment():
    """Return (user_full_name, agency, station) for a seeded end-user workstation."""
    with SessionLocal() as db:
        assignment, user = db.execute(
            select(UserAgency, User)
            .join(User, User.id == UserAgency.user_id)
            .where(UserAgency.agency == "Global Voyages", UserAgency.station.is_not(None))
            .order_by(UserAgency.station, UserAgency.post)
        ).first()
        return {"full_name": user.full_name, "agency": assignment.agency, "station": assignment.station}
