from __future__ import annotations

import streamlit as st

from constants import AGENCY_STATIONS
from services.api import APIError
from services.session import set_navigation
from views.layout import page_header

from components.common import UI_LOGGER, _backend, _logo_data_uri


def _sync_login_credentials() -> None:
    """Populate login widgets after a demo account or support mode is selected."""
    support_mode = st.session_state.get("demo_support_mode", False)
    selected = st.session_state.get("selected_login_agent", "Choisir un compte")
    if support_mode:
        name, password, source = "Support IT", "Support123!", "support"
    elif selected != "Choisir un compte":
        name, password, source = selected, "IDColis2024!", selected
    else:
        name, password, source = "", "", selected
    st.session_state.login_name_input = name
    st.session_state.login_password_input = password
    st.session_state.login_autofill_source = source


def render_login() -> None:
    agencies = [
        ("Trésor Voyages", "tresor-voyages.jpg", "#2F7D4A", "Support terrain Trésor Voyages"),
        ("Global Voyages", "global-voyages.png", "#246BCE", "Support terrain Global Voyages"),
    ]
    selected_station = st.session_state.get("selected_station")
    if not selected_station:
        st.markdown(
            """
            <style>
            /* The chooser has one button per agency; keep each action aligned
               with the agency color used by its card and logo. */
            [data-testid="stMainBlockContainer"] .stHorizontalBlock > div:nth-child(2) .stButton > button {
                background: #246BCE !important;
                border-color: #246BCE !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        page_header("Choisissez votre agence", "Un espace de support adapté à votre réseau ID Colis.", '<span class="badge station-chip">ID Colis Support</span>')
        agency_cols = st.columns(2, gap="large")
        for col, (name, logo, color, description) in zip(agency_cols, agencies):
            with col:
                st.markdown(
                    f'''<div style="border:2px solid {color}; border-radius:16px; padding:1rem; background:white; min-height:112px;">
                    <div style="font-weight:800;color:{color};font-size:1.2rem;">{name}</div>
                    <div style="color:#5F7184;margin-top:.5rem;">{description}</div></div>''',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='display:flex;justify-content:center;align-items:center;height:82px;margin:.2rem 0 .45rem;'><img src='{_logo_data_uri(logo)}' alt='{name} logo' style='max-width:105px;max-height:76px;object-fit:contain;'></div>",
                    unsafe_allow_html=True,
                )
                if st.button(f"Continuer avec {name}", key=f"choose_{name}", width="stretch", type="primary"):
                    st.session_state.selected_station = name
                    st.session_state.login_demo_choice = "Choisir un compte"
                    st.session_state.login_step = 1
                    st.session_state.login_name = ""
                    st.session_state.login_password = ""
                    st.session_state.login_autofill_source = None
                    st.session_state.demo_support_mode = False
                    st.session_state.selected_login_agent = "Choisir un compte"
                    st.session_state.login_agency_site = None
                    st.rerun()
        return

    selected_color = "#2F7D4A" if selected_station == "Trésor Voyages" else "#246BCE"
    selected_logo = "tresor-voyages.jpg" if selected_station == "Trésor Voyages" else "global-voyages.png"
    st.markdown(f"""
    <style>
      :root {{ --idc-agency:{selected_color}; }}
      [data-testid='stButton'] button[kind='primary'] {{ background:{selected_color} !important; border-color:{selected_color} !important; }}
      .login-shell {{ background:transparent; border-radius:0; padding:.25rem; box-shadow:none; }}
      .login-brand {{ color:{selected_color}; font-size:2.1rem; font-weight:900; }}
      .login-agency {{ color:{selected_color}; font-weight:800; letter-spacing:.02em; }}
    </style>
    """, unsafe_allow_html=True)
    if st.button("← Retour aux agences", key="back_to_agencies", type="primary"):
        st.session_state.pop("selected_station", None)
        st.session_state.pop("selected_site", None)
        st.session_state.pop("login_agency_site", None)
        st.session_state.login_autofill_source = None
        st.session_state.login_step = 1
        st.rerun()
    page_header("Connexion", f"{selected_station} · espace support", f'<span class="badge" style="background:{selected_color};color:white;">{selected_station}</span>')
    left, right = st.columns([0.42, 0.58], vertical_alignment="center")
    login_step = st.session_state.get("login_step", 1)
    if login_step == 3 and not st.session_state.get("login_agency_site"):
        st.session_state.login_step = 1
        st.rerun()
    if login_step == 1:
        st.markdown(f"<div style='text-align:center;margin:1.5rem 0 .5rem;'><img src='data:image/png;base64,' alt='' style='display:none'></div>", unsafe_allow_html=True)
        st.markdown(f"<div style='display:flex;justify-content:center;'><img src='{_logo_data_uri(selected_logo)}' alt='{selected_station} logo' style='max-width:135px;max-height:95px;object-fit:contain;'></div>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:center;color:{selected_color};'>Choisissez votre agence locale</h2><p style='text-align:center;color:#5F7184;'>Sélectionnez l'agence où vous travaillez pour continuer.</p>", unsafe_allow_html=True)
        station_options = ["Choisir une agence"] + AGENCY_STATIONS[selected_station]
        station = st.selectbox("Agence locale", station_options, key="selected_site_picker")
        if st.button("Continuer vers la connexion", type="primary", width="stretch", disabled=station == "Choisir une agence"):
            st.session_state.login_agency_site = station
            st.session_state.login_step = 3
            st.rerun()
        return
    with left:
        st.markdown('<div class="login-shell">', unsafe_allow_html=True)
        st.markdown(f"<div style='display:flex;justify-content:center;'><img src='{_logo_data_uri(selected_logo)}' alt='{selected_station} logo' style='max-width:135px;max-height:95px;object-fit:contain;'></div>", unsafe_allow_html=True)
        st.markdown(f'<div class="login-brand">ID Colis</div><div class="login-agency">Support {selected_station}</div>', unsafe_allow_html=True)
        st.markdown('<p class="hero-muted">Accédez à vos tickets, interventions terrain et demandes de support.</p></div>', unsafe_allow_html=True)
    with right:
        with st.container(border=True):
            st.markdown(f'<div class="login-agency">Connexion {selected_station}</div>', unsafe_allow_html=True)
            st.caption(f"Agence locale : {st.session_state.get('login_agency_site')}")
            use_support = st.session_state.get("demo_support_mode", False)
            with st.expander("Choisir un compte de test"):
                try:
                    local_agents = _backend().public_agents(selected_station, st.session_state.get("login_agency_site"))
                except APIError:
                    local_agents = []
                agent_options = ["Choisir un compte"] + [item["name"] for item in local_agents]
                selected_agent = st.selectbox(
                    "Compte de l’agence",
                    agent_options,
                    key="selected_login_agent",
                    on_change=_sync_login_credentials,
                )
            is_regulator = selected_agent.startswith("Régulateur ")
            name_default = "Support IT" if use_support else (selected_agent if selected_agent != "Choisir un compte" else "")
            password_default = "Support123!" if use_support else ("Regulator123!" if is_regulator else "IDColis2024!" if selected_agent != "Choisir un compte" else "")
            autofill_source = "support" if use_support else selected_agent
            if st.session_state.get("login_autofill_source") != autofill_source:
                st.session_state.login_name_input = name_default
                st.session_state.login_password_input = password_default
                st.session_state.login_autofill_source = autofill_source
            name_key = f"login_name_input_{autofill_source}"
            password_key = f"login_password_input_{autofill_source}"
            name = st.text_input("Nom de l’agent", value=name_default, key=name_key)
            password = st.text_input("Mot de passe", type="password", value=password_default, key=password_key)
            support_col, connect_col = st.columns([0.42, 0.58], vertical_alignment="center")
            with support_col:
                st.checkbox("Compte Support IT", key="demo_support_mode", on_change=_sync_login_credentials)
            with connect_col:
                connect_clicked = st.button("Connexion", type="primary", width="stretch")
            if connect_clicked:
                name_value = name.replace("\u200b", "").replace("\ufeff", "").strip()
                password_value = password.replace("\u200b", "").replace("\ufeff", "").strip()
                if not name_value:
                    st.error("Saisissez le nom de l’agent.")
                    return
                if not password_value:
                    st.error("Please enter your password.")
                    return
                try:
                    UI_LOGGER.info("login_attempt name=%s", name_value)
                    session = _backend().login(name_value, password_value, st.session_state.get("selected_station"), st.session_state.get("login_agency_site"))
                    st.session_state.auth_session = session
                    st.session_state.active_user = session["user"]
                    UI_LOGGER.info("login_success name=%s role=%s", name_value, session["user"]["role"])
                    set_navigation("agent_dashboard" if session["user"]["role"] in {"Support_IT", "Régulateur_Agence"} else "user_home")
                    st.query_params["sid"] = session["session_id"]
                    st.query_params["sk"] = session["session_key"]
                    st.rerun()
                except APIError as exc:
                    UI_LOGGER.warning("login_failed name=%s error=%s", name_value, exc)
                    st.error(str(exc))


