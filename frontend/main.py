from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Add current directory to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from components.pages.agent_pages import render_agent_dashboard, render_agent_queue
from components.pages.diagnostics import render_diagnostics
from components.pages.directory import render_directory, render_directory_user_tickets
from components.pages.interventions import render_interventions
from components.pages.login import render_login
from components.pages.operation_report import render_operation_report
from components.pages.ticket_detail import render_ticket_detail
from components.pages.user_pages import render_ticket_create, render_user_home, render_user_tickets
from services.api import BackendAPI, APIError
from services.session import clear_session, ensure_state, load_query_navigation, load_query_session, set_navigation, set_session
from views.layout import inject_styles
from views.sidebar import render_sidebar


def _api() -> BackendAPI:
    if "api" not in st.session_state:
        st.session_state.api = BackendAPI()
    return st.session_state.api


def _restore_from_query() -> None:
    if st.session_state.get("auth_session"):
        return
    sid, sk = load_query_session()
    if sid and sk:
        try:
            session = _api().restore(sid, sk, st.session_state.get("selected_station"))
            set_session(session)
        except Exception:
            clear_session()


def _restore_navigation_from_query() -> None:
    page, ticket_id = load_query_navigation()
    if page:
        st.session_state.page = page
    if ticket_id:
        st.session_state.nav_ticket_id = ticket_id
        st.session_state.selected_ticket_id = ticket_id


def main() -> None:
    ensure_state()
    st.session_state.dark_mode = False
    st.set_page_config(page_title="ID Colis Support App", page_icon="ID", layout="wide", initial_sidebar_state="expanded")
    inject_styles()
    _restore_from_query()
    _restore_navigation_from_query()
    if st.session_state.get("page") in {"ticket_detail", "operation_report"} and st.session_state.get("nav_ticket_id") and not st.session_state.get("selected_ticket_id"):
        st.session_state.selected_ticket_id = st.session_state.nav_ticket_id
    if st.session_state.get("logout_requested"):
        session = st.session_state.get("auth_session")
        if session:
            try:
                _api().logout(session.get("refresh_token"), session.get("session_id"), session.get("session_key"))
            except Exception:
                pass
        clear_session()
        st.session_state.logout_requested = False
    if not st.session_state.get("auth_session"):
        render_login()
        return
    role = st.session_state.active_user["role"]
    with st.sidebar:
        render_sidebar(role)
    page = st.session_state.get("page", "user_home")
    if page == "ticket_create" and role != "Utilisateur":
        st.session_state.page = "agent_dashboard"
        st.rerun()
    if page == "user_home":
        render_user_home()
    elif page == "ticket_create":
        render_ticket_create()
    elif page == "user_tickets":
        render_user_tickets()
    elif page == "agent_dashboard":
        render_agent_dashboard()
    elif page == "directory":
        render_directory()
    elif page == "directory_user_tickets":
        render_directory_user_tickets()
    elif page == "agent_queue":
        render_agent_queue()
    elif page == "regulator_queue":
        render_agent_queue()
    elif page == "regulator_all_tickets":
        render_agent_queue()
    elif page == "ticket_detail":
        render_ticket_detail()
    elif page == "operation_report":
        render_operation_report()
    elif page == "interventions":
        render_interventions()
    elif page == "diagnostics":
        render_diagnostics()
    else:
        st.session_state.page = "user_home" if role == "Utilisateur" else "agent_dashboard"
        st.rerun()


if __name__ == "__main__":
    main()


