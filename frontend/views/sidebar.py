from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Add parent directory to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from constants import AGENT_PAGES, NAVY, USER_PAGES
from services.session import set_navigation

LOGO_DIR = Path(__file__).resolve().parents[1] / "assets" / "logos"


def render_sidebar(role: str | None) -> None:
    user = st.session_state.get("active_user") or {}

    # Clean display for roles
    role_display_map = {
        "Support_IT": "Agent Support IT",
        "Utilisateur": "Utilisateur final"
    }
    display_role = role_display_map.get(role, role) if role else ""

    st.sidebar.markdown(
        f"""
        <div style="padding:1rem 0 0.8rem 0;">
          <div style="font-weight:900;font-size:1.1rem;color:{NAVY};">ID Colis</div>
          <div style="color:#627D98;font-size:.92rem;margin-top:.15rem;">Support terrain et logistique</div>
          <div style="margin-top:.8rem;padding:.75rem .9rem;border-radius:16px;background:white;border:1px solid rgba(16,42,67,0.08);">
            <div style="font-weight:800;color:{NAVY};">{user.get("full_name","")}</div>
            <div style="color:#627D98;font-size:.9rem;">{display_role}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    selected_station = st.session_state.get("selected_station", "Trésor Voyages")
    logo = "tresor-voyages.jpg" if selected_station.startswith("Trésor") else "global-voyages.png"
    agency_color = "#2F7D4A" if selected_station.startswith("Trésor") else "#246BCE"
    st.sidebar.markdown(
        f"<style>[data-testid='stSidebar']{{border-top:7px solid {agency_color};}} [data-testid='stSidebar'] .stButton > button[kind='primary']{{background:{agency_color} !important;border-color:{agency_color} !important;}}</style>",
        unsafe_allow_html=True,
    )
    st.sidebar.image(str(LOGO_DIR / logo), width=64)
    st.sidebar.markdown(f"<div style='color:{agency_color};font-weight:800;'>{selected_station}</div>", unsafe_allow_html=True)
    pages = AGENT_PAGES if role == "Support_IT" else USER_PAGES
    current = st.session_state.get("page", "login")
    for label, key in pages:
        pressed = st.sidebar.button(label, key=f"nav_{key}", width="stretch", type="primary" if current == key else "secondary")
        if pressed:
            set_navigation(key)
            st.rerun()
    st.sidebar.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    if st.sidebar.button("Déconnexion", key="logout_btn", width="stretch"):
        st.session_state.logout_requested = True
        st.rerun()


