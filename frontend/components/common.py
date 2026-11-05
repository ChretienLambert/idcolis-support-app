from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TypedDict, Any
from pathlib import Path
import base64

import streamlit as st

from services.api import BackendAPI
from services.logging import build_logger

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "logos"


def _logo_data_uri(filename: str) -> str:
    """Return a local agency logo as a compact inline image for centered layouts."""
    path = ASSETS_DIR / filename
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


class SessionData(TypedDict):
    """Type hint for authentication session data."""
    user: dict[str, Any]
    session_id: str
    session_key: str
    access_token: str


class TicketBase(TypedDict):
    """Required fields for ticket data from API."""
    id: str
    subject: str
    description: str
    status: str
    category: str
    priority: str
    team_name: str
    team_id: str
    service_concerne: str
    origine_ticket: str | None
    requester_name: str
    requester_email: str
    requester_user_id: str
    assigned_agent_name: str | None
    assigned_agent_id: str | None
    created_at: str
    comments: list[dict[str, Any]]
    allow_user_edit: bool


class Ticket(TicketBase, total=False):
    """Extended ticket data with optional AI fields."""
    ai_model_name: str
    ai_confidence: float
    ai_team_name: str
    ai_agent_name: str
    ai_notes: str

UI_LOGGER = build_logger("ID Colis.frontend.ui", "frontend.log")


def _role_label() -> str:
    user = st.session_state.active_user
    return user["role"] if user else ""


def _current_user_id() -> str:
    return st.session_state.active_user["id"]


def _backend() -> BackendAPI:
    if "api" not in st.session_state:
        st.session_state.api = BackendAPI()
    return st.session_state.api


def _ticket_created_date(ticket: Ticket) -> date | None:
    raw = ticket.get("created_at")
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, str):
        value = raw.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None
    return None


def _apply_time_filter(tickets: list[Ticket], prefix: str) -> list[Ticket]:
    preset_key = f"{prefix}_time_preset"
    if preset_key not in st.session_state:
        st.session_state[preset_key] = "Tous"

    preset = st.selectbox("Période", ["Tous", "Aujourd’hui", "7 derniers jours", "30 derniers jours"], key=preset_key, label_visibility="collapsed")
    if preset == "Tous":
        return tickets

    today = date.today()
    if preset == "Aujourd’hui":
        start = today
    elif preset == "7 derniers jours":
        start = today - timedelta(days=7)
    else:
        start = today - timedelta(days=30)

    end = today
    filtered = tickets
    filtered = [ticket for ticket in filtered if (created := _ticket_created_date(ticket)) and start <= created <= end]
    return filtered


def _load_tickets() -> list[Ticket]:
    if not st.session_state.auth_session:
        return []
    role = st.session_state.get("active_user", {}).get("role")
    # The regulator is scoped to the agency selected at login.  The value in
    # ``selected_station`` is actually the agency label in this login flow;
    # prefer the authenticated user's agency when available so the API query
    # cannot accidentally filter against a station name.
    agency_scope = None
    if role == "Régulateur_Agence":
        user_name = str(st.session_state.get("active_user", {}).get("full_name", ""))
        agency_scope = (
            st.session_state.get("active_user", {}).get("agency")
            or st.session_state.get("selected_station")
            or ("Trésor Voyages" if "Trésor" in user_name else "Global Voyages" if "Global" in user_name else None)
        )
    UI_LOGGER.info("ticket_queue_scope role=%r agency=%r selected_station=%r", role, agency_scope, st.session_state.get("selected_station"))
    tickets = _backend().list_tickets(st.session_state.auth_session["access_token"], agency=agency_scope)
    if isinstance(tickets, list):
        st.session_state.tickets = tickets
        return tickets  # type: ignore
    return []


def _load_teams() -> list[dict]:  # type: ignore
    if not st.session_state.auth_session:
        return []
    if "teams" not in st.session_state:
        teams = _backend().list_teams(st.session_state.auth_session["access_token"])
        if isinstance(teams, list):
            st.session_state.teams = teams
        else:
            st.session_state.teams = []
    return st.session_state.teams


