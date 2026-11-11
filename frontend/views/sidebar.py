from __future__ import annotations

import base64
import mimetypes
import sys
from pathlib import Path

import streamlit as st

# Add parent directory to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from constants import AGENT_PAGES, NAVY, REGULATOR_PAGES, USER_PAGES
from i18n import t
from services.session import set_navigation

LOGO_DIR = Path(__file__).resolve().parents[1] / "assets" / "logos"


def _logo_data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def render_sidebar(role: str | None) -> None:
    user = st.session_state.get("active_user") or {}

    # Clean display for roles
    role_display_map = {
        "Support_IT": "Agent Support IT",
        "Régulateur_Agence": "Régulateur agence",
        "Utilisateur": "Utilisateur final"
    }
    display_role = t(role_display_map.get(role, role)) if role else ""
    tagline = t("Support terrain et logistique")

    st.sidebar.markdown(
        f"""
        <div style="padding:1rem 0 0.8rem 0;">
          <div style="font-weight:900;font-size:1.1rem;color:var(--idc-navy);">ID Colis</div>
          <div style="color:var(--idc-muted);font-size:.92rem;margin-top:.15rem;">{tagline}</div>
          <div style="margin-top:.8rem;padding:.75rem .9rem;border-radius:16px;background:var(--idc-card);border:1px solid var(--idc-border);">
            <div style="font-weight:800;color:var(--idc-navy);">{user.get("full_name","")}</div>
            <div style="color:var(--idc-muted);font-size:.9rem;">{display_role}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    selected_station = st.session_state.get("selected_station", "Trésor Voyages")
    logo = "tresor-voyages.jpg" if selected_station.startswith("Trésor") else "global-voyages.png"
    agency_color = "#2F7D4A" if selected_station.startswith("Trésor") else "#246BCE"
    st.sidebar.markdown(
        f"<style>:root{{--idc-agency:{agency_color};}} [data-testid='stSidebar']{{border-top:7px solid {agency_color};}} [data-testid='stSidebar'] .stButton > button[kind='primary']{{background:{agency_color} !important;border-color:{agency_color} !important;}}</style>",
        unsafe_allow_html=True,
    )
    logo_uri = _logo_data_uri(LOGO_DIR / logo)
    st.sidebar.markdown(
        f"<div class='sidebar-logo-wrap'><img class='sidebar-logo' src='{logo_uri}' alt='{selected_station} logo'></div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(f"<div class='sidebar-agency' style='color:{agency_color};'>{selected_station}</div>", unsafe_allow_html=True)
    # ID Colis uses a clear light operational interface. Dark mode was removed
    # because it reduced contrast and did not add value for field workflows.
    st.session_state.dark_mode = False
    pages = AGENT_PAGES if role == "Support_IT" else REGULATOR_PAGES if role == "Régulateur_Agence" else USER_PAGES
    if role == "Support_IT":
        st.sidebar.markdown("<div class='idc-eyebrow' style='margin:.8rem 0 .45rem;'>Support</div>", unsafe_allow_html=True)
    current = st.session_state.get("page", "login")
    for label, key in pages:
        if role == "Support_IT" and key == "interventions":
            st.sidebar.markdown(f"<div class='idc-eyebrow' style='margin:.8rem 0 .45rem;'>{t('Opérations')}</div>", unsafe_allow_html=True)
        if role == "Support_IT" and key == "diagnostics":
            st.sidebar.markdown(f"<div class='idc-eyebrow' style='margin:.8rem 0 .45rem;'>{t('Administration')}</div>", unsafe_allow_html=True)
        pressed = st.sidebar.button(t(label), key=f"nav_{key}", width="stretch", type="primary" if current == key else "secondary")
        if pressed:
            set_navigation(key)
            st.rerun()
    st.sidebar.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    if st.sidebar.button(t("Déconnexion"), key="logout_btn", width="stretch"):
        st.session_state.logout_requested = True
        st.rerun()


