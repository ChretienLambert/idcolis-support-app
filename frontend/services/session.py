from __future__ import annotations

import streamlit as st


def ensure_state() -> None:
    defaults = {
        "page": "login",
        "auth_session": None,
        "active_user": None,
        "tickets": [],
        "selected_ticket_id": None,
        "api_error": "",
        "ticket_filter_status": "Tous",
        "ticket_filter_priority": "Toutes",
        "ticket_filter_search": "",
        "create_subject": "",
        "create_description": "",
        "detail_comment": "",
        "flash_message": "",
        "nav_ticket_id": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def set_session(session: dict) -> None:
    st.session_state.auth_session = session
    st.session_state.active_user = session["user"]
    st.session_state.page = "agent_dashboard" if session["user"]["role"] == "Support_IT" else "user_home"
    st.session_state.nav_ticket_id = None
    st.session_state.selected_ticket_id = None
    try:
        st.query_params["sid"] = session["session_id"]
        st.query_params["sk"] = session["session_key"]
        st.query_params["page"] = st.session_state.page
        st.query_params.pop("tid", None)
    except Exception:
        pass


def clear_session() -> None:
    st.session_state.auth_session = None
    st.session_state.active_user = None
    st.session_state.page = "login"
    st.session_state.nav_ticket_id = None
    st.session_state.selected_ticket_id = None
    try:
        st.query_params.clear()
        if st.session_state.get("lang") == "en":
            st.query_params["lang"] = "en"
    except Exception:
        pass


def set_navigation(page: str, ticket_id: str | None = None) -> None:
    st.session_state.page = page
    st.session_state.nav_ticket_id = ticket_id
    st.session_state.selected_ticket_id = ticket_id
    try:
        st.query_params["page"] = page
        if ticket_id:
            st.query_params["tid"] = ticket_id
        else:
            st.query_params.pop("tid", None)
    except Exception:
        pass


def load_query_session() -> tuple[str | None, str | None]:
    try:
        sid = st.query_params.get("sid")
        sk = st.query_params.get("sk")
        if isinstance(sid, list):
            sid = sid[0] if sid else None
        if isinstance(sk, list):
            sk = sk[0] if sk else None
        return sid, sk
    except Exception:
        return None, None


def load_query_navigation() -> tuple[str | None, str | None]:
    try:
        page = st.query_params.get("page")
        tid = st.query_params.get("tid")
        if isinstance(page, list):
            page = page[0] if page else None
        if isinstance(tid, list):
            tid = tid[0] if tid else None
        return page, tid
    except Exception:
        return None, None


