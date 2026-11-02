from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TypedDict, Any
import sys
import base64
from pathlib import Path

import streamlit as st

# Add parent directory to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from constants import AGENCY_STATIONS, DEMO_AGENT_NAMES, BLUE, GREEN, YELLOW, ORANGE
from services.logging import build_logger
from services.api import APIError, BackendAPI
from services.session import set_navigation, set_session
from views.layout import metric_card, page_header, status_badge

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

    preset = st.selectbox("📅 Période", ["Tous", "Aujourd’hui", "7 derniers jours", "30 derniers jours"], key=preset_key, label_visibility="collapsed")
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
    if st.button("← Retour aux agences", key="back_to_agencies", type="secondary"):
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
            name_default = "Support IT" if use_support else (selected_agent if selected_agent != "Choisir un compte" else "")
            password_default = "Support123!" if use_support else ("IDColis2024!" if selected_agent != "Choisir un compte" else "")
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
                    set_navigation("agent_dashboard" if session["user"]["role"] == "Support_IT" else "user_home")
                    st.query_params["sid"] = session["session_id"]
                    st.query_params["sk"] = session["session_key"]
                    st.rerun()
                except APIError as exc:
                    UI_LOGGER.warning("login_failed name=%s error=%s", name_value, exc)
                    st.error(str(exc))


def _load_tickets() -> list[Ticket]:
    if not st.session_state.auth_session:
        return []
    tickets = _backend().list_tickets(st.session_state.auth_session["access_token"])
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


def render_directory() -> None:
    """Display agency locations, assigned posts, and the selected user's tickets."""
    agency = st.session_state.get("selected_station", "Agence sélectionnée")
    page_header("Agences et postes", f"Annuaire opérationnel de {agency}.", f'<span class="badge station-chip">{agency}</span>')
    token = st.session_state.auth_session["access_token"]
    try:
        stations = _backend().directory(token)
    except APIError as exc:
        st.error(str(exc))
        return
    if not stations:
        st.info("Aucune station n'est encore enregistrée pour cette agence.")
        return
    st.caption(f"{len(stations)} agence(s) dans la file {agency}. Chaque agence possède deux postes et seuls ses utilisateurs sont affichés.")
    for station in stations:
        with st.container(border=True):
            head = st.columns([0.55, 0.45])
            with head[0]:
                st.markdown(f"### {station['name']}")
                st.write(f"{station['city']} · {station['address']}")
            with head[1]:
                if station.get("phone"):
                    st.markdown(f"**Contact station**  \n{station['phone']}")
            post_cols = st.columns(2)
            for col, post in zip(post_cols, station.get("posts", [])):
                with col:
                    assigned = post.get("assigned_user") or "Poste à affecter"
                    st.markdown(f"**{post['name']}**")
                    st.caption(assigned)
                    if post.get("user_id") and st.button("Voir les tickets", key=f"directory_user_{post['user_id']}", width="stretch"):
                        st.session_state.directory_user_id = post["user_id"]
                        st.session_state.directory_user_name = assigned
                        st.session_state.directory_user_email = post.get("email")
                        set_navigation("directory_user_tickets")
                        st.rerun()


def render_directory_user_tickets() -> None:
    """Show a dedicated support page for one agency post and its ticket history."""
    user_name = st.session_state.get("directory_user_name", "Utilisateur")
    page_header(f"Tickets de {user_name}", "Historique et suivi du poste sélectionné")
    if st.button("← Retour aux agences", key="back_directory"):
        set_navigation("directory")
        st.rerun()
    selected_user_id = st.session_state.get("directory_user_id")
    tickets = [ticket for ticket in _load_tickets() if ticket.get("requester_user_id") == selected_user_id]
    if not tickets:
        st.info("Aucun ticket enregistré pour ce poste.")
        return
    for ticket in tickets:
        row = st.columns([0.18, 0.42, 0.18, 0.22])
        with row[0]:
            if st.button(ticket["id"], key=f"user_ticket_{ticket['id']}", width="stretch"):
                st.session_state.selected_ticket_id = ticket["id"]
                set_navigation("ticket_detail", ticket["id"])
                st.rerun()
        with row[1]:
            st.write(ticket["subject"])
        with row[2]:
            st.write(ticket.get("priority") or "À qualifier")
        with row[3]:
            st.markdown(status_badge(ticket["status"]), unsafe_allow_html=True)


def render_directory_ticket_tail() -> None:
    """Compatibility placeholder for older navigation state."""
    return


def _render_directory_selected_user_legacy() -> None:
    """Deprecated; retained only to avoid breaking old sessions."""
    selected_user_id = st.session_state.get("directory_user_id")
    if selected_user_id:
        st.divider()
        st.markdown(f"### Tickets de {st.session_state.get('directory_user_name', 'l’utilisateur')}")
        tickets = [ticket for ticket in _load_tickets() if ticket.get("requester_user_id") == selected_user_id]
        if not tickets:
            st.info("Aucun ticket enregistré pour ce poste.")
        for ticket in tickets:
            row = st.columns([0.18, 0.42, 0.18, 0.22])
            with row[0]:
                if st.button(ticket["id"], key=f"directory_ticket_{ticket['id']}", width="stretch"):
                    st.session_state.selected_ticket_id = ticket["id"]
                    set_navigation("ticket_detail", ticket["id"])
                    st.rerun()
            with row[1]:
                st.write(ticket["subject"])
            with row[2]:
                st.write(ticket.get("priority") or "À qualifier")
            with row[3]:
                st.markdown(status_badge(ticket["status"]), unsafe_allow_html=True)


def render_user_home() -> None:
    page_header("Accueil", "Espace utilisateur")
    tickets = _load_tickets()
    mine = [ticket for ticket in tickets if ticket["requester_user_id"] == _current_user_id()]
    category_filter = st.selectbox("Catégorie", ["Toutes"] + sorted({ticket["category"] for ticket in mine}), key="user_home_category_filter")
    if category_filter != "Toutes":
        mine = [ticket for ticket in mine if ticket["category"] == category_filter]
    mine = _apply_time_filter(mine, "user_home")

    total = len(mine)
    open_count = sum(1 for ticket in mine if ticket["status"] == "En attente")
    in_progress = sum(1 for ticket in mine if ticket["status"] == "En cours")
    resolved = sum(1 for ticket in mine if ticket["status"] in {"Résolu", "Clôturé"})
    cols = st.columns(3)
    for col, payload in zip(
        cols,
        [
            ("Mes tickets", str(total), "Demandes créées", BLUE),
            ("Actifs", str(open_count + in_progress), "Tickets ouverts et en cours", GREEN),
            ("Résolus", str(resolved), "Tickets clôturés", ORANGE),
        ],
    ):
        with col:
            st.markdown(metric_card(*payload), unsafe_allow_html=True)

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="panel"><div class="section-title">Derniers tickets</div>', unsafe_allow_html=True)
    for ticket in mine[:8]:
        row = st.columns([0.18, 0.34, 0.16, 0.17, 0.15])
        with row[0]:
            if st.button(ticket["id"], key=f"user_open_{ticket['id']}", width="stretch"):
                st.session_state.selected_ticket_id = ticket["id"]
                set_navigation("ticket_detail", ticket["id"])
                st.rerun()
        with row[1]:
            if st.button(ticket["subject"], key=f"user_subject_{ticket['id']}", width="stretch"):
                st.session_state.selected_ticket_id = ticket["id"]
                set_navigation("ticket_detail", ticket["id"])
                st.rerun()
        with row[2]:
            st.write(ticket["category"])
        with row[3]:
            st.markdown(status_badge(ticket["status"]), unsafe_allow_html=True)
        with row[4]:
            st.write(ticket["team_name"])
    st.markdown("</div>", unsafe_allow_html=True)


def render_ticket_create() -> None:
    # Initialize wizard step
    if "wizard_step" not in st.session_state:
        st.session_state.wizard_step = 1
    
    page_header("Nouveau ticket", "Création de demande de support")
    
    # For regular users: Simple form (no wizard)
    if _role_label() == "Utilisateur":
        st.markdown('<div class="section-title">Informations générales</div>', unsafe_allow_html=True)
        subject = st.text_input("Sujet", key="create_subject")
        description = st.text_area("Description détaillée", key="create_description", height=180, max_chars=2000)
        char_count = len(description)
        st.caption(f"Caractères: {char_count}/2000")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Annuler", width="stretch"):
                set_navigation("user_home", None)
                st.rerun()
        with col2:
            if st.button("Créer le ticket", type="primary", width="stretch", disabled=not (subject.strip() and description.strip())):
                try:
                    ticket = _backend().create_ticket(
                        st.session_state.auth_session["access_token"],
                        subject,
                        description,
                        metadata={
                            "agency": st.session_state.get("selected_station"),
                            "site": st.session_state.get("login_agency_site"),
                            "operational_impact": "Individuel",
                        },
                    )
                    st.session_state.flash_message = "Ticket créé avec succès. Statut: En attente."
                    st.session_state.selected_ticket_id = ticket["id"]
                    set_navigation("ticket_detail", ticket["id"])
                    st.rerun()
                except APIError as exc:
                    st.error(str(exc))
    
    # For agents: Multi-step wizard
    else:
        # STEP 1: General Info & Description
        if st.session_state.wizard_step == 1:
            st.markdown('<div class="section-title">Étape 1/3 : Informations générales</div>', unsafe_allow_html=True)
            subject = st.text_input("Sujet", key="create_subject")
            description = st.text_area("Description détaillée", key="create_description", height=180, max_chars=2000)
            char_count = len(description)
            st.caption(f"Caractères: {char_count}/2000")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Annuler", width="stretch"):
                    st.session_state.wizard_step = 1
                    set_navigation("agent_dashboard", None)
                    st.rerun()
            with col2:
                if st.button("Suivant →", type="primary", width="stretch", disabled=not (subject.strip() and description.strip())):
                    # Store form data
                    st.session_state.wizard_subject = subject
                    st.session_state.wizard_description = description
                    st.session_state.wizard_step = 2
                    st.rerun()
        
        # STEP 2: AI Classification
        elif st.session_state.wizard_step == 2:
            st.markdown('<div class="section-title">Étape 2/3 : Classification IA</div>', unsafe_allow_html=True)
            
            # Show AI banner
            st.markdown(
                """
                <div class="ai-suggestion-box">
                  <div class="ai-suggestion-title">💡 Suggestions générées par le modèle d'intelligence artificielle. Vérifiez et ajustez si nécessaire avant de valider.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            # Get AI prediction
            try:
                prediction = _backend().classify(
                    st.session_state.auth_session["access_token"],
                    st.session_state.wizard_subject,
                    st.session_state.wizard_description
                )
                teams = _load_teams()
                
                # Display suggestions with interactive selectors
                st.markdown(
                    f"""
                    <div class="ai-suggestion-box">
                      <div class="ai-suggestion-title">💡 Suggestions IA basées sur l'origine et le contenu</div>
                      <div class="ai-suggestion-item">
                        <div class="ai-suggestion-label">Provenance détectée:</div>
                        <div class="ai-suggestion-value">{prediction.get('origine_ticket', 'Inconnue')}</div>
                      </div>
                      <div class="ai-suggestion-item">
                        <div class="ai-suggestion-label">Service concerné:</div>
                        <div class="ai-suggestion-value">{prediction.get('service_concerne', 'Inconnu')}</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                col1, col2 = st.columns(2)
                with col1:
                    category = st.selectbox("Catégorie suggérée", ["Outlook", "Réseau", "Logiciels", "Matériel", "Autre"], 
                                          index=["Outlook", "Réseau", "Logiciels", "Matériel", "Autre"].index(prediction["category"]) if prediction["category"] in ["Outlook", "Réseau", "Logiciels", "Matériel", "Autre"] else 0)
                    priority = st.selectbox("Priorité suggérée", ["Faible", "Moyenne", "Élevée", "Critique"],
                                         index=["Faible", "Moyenne", "Élevée", "Critique"].index(prediction["priority"]) if prediction["priority"] in ["Faible", "Moyenne", "Élevée", "Critique"] else 1)
                with col2:
                    team_options = [(t["slug"], t["name"]) for t in teams]
                    team_index = next((i for i, (slug, name) in enumerate(team_options) if slug == prediction["team_slug"]), 0)
                    selected_team = st.selectbox("Équipe cible", team_options, index=team_index, format_func=lambda x: x[1])
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("← Précédent", width="stretch"):
                        st.session_state.wizard_step = 1
                        st.rerun()
                with col2:
                    if st.button("Suivant →", type="primary", width="stretch"):
                        st.session_state.wizard_category = category
                        st.session_state.wizard_priority = priority
                        st.session_state.wizard_team = selected_team[0]
                        st.session_state.wizard_service_concerne = prediction.get("service_concerne")
                        st.session_state.wizard_step = 3
                        st.rerun()
            except APIError:
                st.warning("Impossible d'obtenir les suggestions IA.")
                if st.button("← Précédent", width="stretch"):
                    st.session_state.wizard_step = 1
                    st.rerun()
        
        # STEP 3: Confirmation
        elif st.session_state.wizard_step == 3:
            st.markdown('<div class="section-title">Étape 3/3 : Confirmation</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="panel"><div class="section-title">Résumé du ticket</div>', unsafe_allow_html=True)
            st.write(f"**Sujet :** {st.session_state.wizard_subject}")
            st.write(f"**Description :** {st.session_state.wizard_description}")
            st.write(f"**Catégorie :** {st.session_state.wizard_category}")
            st.write(f"**Priorité :** {st.session_state.wizard_priority}")
            st.write(f"**Équipe :** {st.session_state.wizard_team}")
            st.markdown('</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("← Précédent", width="stretch"):
                    st.session_state.wizard_step = 2
                    st.rerun()
            with col2:
                if st.button("Créer le ticket", type="primary", width="stretch"):
                    try:
                        ticket = _backend().create_ticket(st.session_state.auth_session["access_token"], 
                                                        st.session_state.wizard_subject, 
                                                        st.session_state.wizard_description)
                        
                        # Auto-approve with wizard selections
                        _backend().approve_ai_suggestions(
                            st.session_state.auth_session["access_token"],
                            ticket["id"],
                            st.session_state.wizard_category,
                            st.session_state.wizard_priority,
                            st.session_state.wizard_team,
                            corrected=True,
                            service_concerne=st.session_state.get("wizard_service_concerne")
                        )
                        st.session_state.flash_message = "Ticket créé et routé vers l'équipe."
                        
                        # Reset wizard
                        st.session_state.wizard_step = 1
                        st.session_state.selected_ticket_id = ticket["id"]
                        set_navigation("ticket_detail", ticket["id"])
                        st.rerun()
                    except APIError as exc:
                        st.error(str(exc))


def render_user_tickets() -> None:
    page_header("Mes tickets", "Suivi personnel")
    tickets = _load_tickets()
    mine = [ticket for ticket in tickets if ticket["requester_user_id"] == _current_user_id()]
    category_filter = st.selectbox("Catégorie", ["Toutes"] + sorted({ticket["category"] for ticket in mine}), key="user_tickets_category_filter")
    if category_filter != "Toutes":
        mine = [ticket for ticket in mine if ticket["category"] == category_filter]
    mine = _apply_time_filter(mine, "user_tickets")
    for ticket in mine:
        row = st.columns([0.18, 0.34, 0.16, 0.17, 0.15])
        with row[0]:
            if st.button(ticket["id"], key=f"open_mine_{ticket['id']}", width="stretch"):
                st.session_state.selected_ticket_id = ticket["id"]
                set_navigation("ticket_detail", ticket["id"])
                st.rerun()
        with row[1]:
            if st.button(ticket["subject"], key=f"open_mine_subject_{ticket['id']}", width="stretch"):
                st.session_state.selected_ticket_id = ticket["id"]
                set_navigation("ticket_detail", ticket["id"])
                st.rerun()
        with row[2]:
            st.write(ticket["category"])
        with row[3]:
            st.markdown(status_badge(ticket["status"]), unsafe_allow_html=True)
        with row[4]:
            st.write(ticket["team_name"])
    if st.button("Retour", width="stretch"):
        set_navigation("user_home", None)
        st.rerun()


def render_agent_dashboard() -> None:
    page_header("Tableau de bord", "Vue agent")
    tickets = _load_tickets()

    # Header filters
    f1, f2, f3 = st.columns([0.5, 0.25, 0.25], vertical_alignment="bottom")
    with f1:
        st.markdown(f"**{len(tickets)}** tickets au total")
    with f2:
        # Time filter integrated
        tickets = _apply_time_filter(tickets, "agent_dashboard")
    with f3:
        if st.button("🔄 Actualiser", width="stretch"):
            st.rerun()

    if not tickets:
        st.info("Aucun ticket trouvé pour la période sélectionnée.")
        return

    cols = st.columns(3)
    counts = {
        "open": sum(1 for ticket in tickets if ticket["status"] == "En attente"),
        "progress": sum(1 for ticket in tickets if ticket["status"] == "En cours"),
        "resolved": sum(1 for ticket in tickets if ticket["status"] in {"Résolu", "Clôturé"}),
    }
    data = [
        ("En attente", str(counts["open"]), "À traiter", YELLOW),
        ("En cours", str(counts["progress"]), "En traitement", BLUE),
        ("Résolus", str(counts["resolved"]), "Clôturés", GREEN),
    ]
    for col, item in zip(cols, data):
        with col:
            st.markdown(metric_card(*item), unsafe_allow_html=True)

    st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="panel"><div class="section-title">Tickets par équipe</div>', unsafe_allow_html=True)
        group: dict[str, int] = {}
        for ticket in tickets:
            group[ticket["team_name"]] = group.get(ticket["team_name"], 0) + 1
        st.dataframe([{"Équipe": key, "Tickets": value} for key, value in sorted(group.items(), key=lambda item: item[1], reverse=True)], hide_index=True, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="panel"><div class="section-title">Statut</div>', unsafe_allow_html=True)
        status_group: dict[str, int] = {}
        for ticket in tickets:
            status_group[ticket["status"]] = status_group.get(ticket["status"], 0) + 1
        st.dataframe([{"Statut": key, "Tickets": value} for key, value in sorted(status_group.items(), key=lambda item: item[1], reverse=True)], hide_index=True, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="panel"><div class="section-title">Tickets récents</div>', unsafe_allow_html=True)
    for ticket in tickets[:8]:
        row = st.columns([0.18, 0.34, 0.16, 0.17, 0.15])
        with row[0]:
            if st.button(ticket["id"], key=f"agent_recent_{ticket['id']}", width="stretch"):
                st.session_state.selected_ticket_id = ticket["id"]
                set_navigation("ticket_detail", ticket["id"])
                st.rerun()
        with row[1]:
            if st.button(ticket["subject"], key=f"agent_recent_subject_{ticket['id']}", width="stretch"):
                st.session_state.selected_ticket_id = ticket["id"]
                set_navigation("ticket_detail", ticket["id"])
                st.rerun()
        with row[2]:
            st.write(ticket["category"])
        with row[3]:
            st.markdown(status_badge(ticket["status"]), unsafe_allow_html=True)
        with row[4]:
            st.write(ticket["assigned_agent_name"] or "Non attribué")
    st.markdown("</div>", unsafe_allow_html=True)


def render_agent_queue() -> None:
    c1, c2 = st.columns([0.85, 0.15])
    with c1:
        page_header("Tous les tickets", "File opérationnelle")
    with c2:
        if st.button("⬅️ Retour", key="back_to_dash", width="stretch"):
            set_navigation("agent_dashboard", None)
            st.rerun()

    tickets = _load_tickets()

    # Compact Filters Row
    st.markdown("---")
    f1, f2, f3, f4, f5 = st.columns([0.28, 0.17, 0.17, 0.17, 0.21], vertical_alignment="bottom")
    with f1:
        st.caption("🔍 Recherche")
        search = st.text_input("Recherche", key="ticket_filter_search", placeholder="Sujet, ID...", label_visibility="collapsed")
    with f2:
        st.caption("🚦 Statut")
        status_filter = st.selectbox("Statut", ["Tous", "En attente", "En cours", "Résolu", "Clôturé"], key="ticket_filter_status", label_visibility="collapsed")
    with f3:
        st.caption("🔥 Priorité")
        priority_filter = st.selectbox("Priorité", ["Toutes", "Critique", "Élevée", "Moyenne", "Faible"], key="ticket_filter_priority", label_visibility="collapsed")
    with f4:
        st.caption("📁 Catégorie")
        category_filter = st.selectbox("Catégorie", ["Toutes"] + sorted({ticket["category"] for ticket in tickets}), key="ticket_filter_category", label_visibility="collapsed")
    with f5:
        st.caption("📅 Période")
        filtered_tickets_temp = _apply_time_filter(tickets, "agent_queue")

    st.markdown("<br>", unsafe_allow_html=True)
    filtered = filtered_tickets_temp
    if search:
        query = search.lower()
        filtered = [ticket for ticket in filtered if query in ticket["id"].lower() or query in ticket["subject"].lower() or query in ticket["team_name"].lower()]
    if status_filter != "Tous":
        filtered = [ticket for ticket in filtered if ticket["status"] == status_filter]
    if priority_filter != "Toutes":
        filtered = [ticket for ticket in filtered if ticket["priority"] == priority_filter]
    if category_filter != "Toutes":
        filtered = [ticket for ticket in filtered if ticket["category"] == category_filter]

    for ticket in filtered:
        row = st.columns([0.18, 0.28, 0.16, 0.16, 0.14, 0.10])
        with row[0]:
            if st.button(ticket["id"], key=f"queue_{ticket['id']}", width="stretch"):
                st.session_state.selected_ticket_id = ticket["id"]
                set_navigation("ticket_detail", ticket["id"])
                st.rerun()
        with row[1]:
            if st.button(ticket["subject"], key=f"queue_subject_{ticket['id']}", width="stretch"):
                st.session_state.selected_ticket_id = ticket["id"]
                set_navigation("ticket_detail", ticket["id"])
                st.rerun()
        with row[2]:
            st.write(ticket["category"])
        with row[3]:
            st.write(ticket["team_name"])
        with row[4]:
            st.markdown(status_badge(ticket["status"]), unsafe_allow_html=True)
        with row[5]:
            st.write(ticket["assigned_agent_name"] or "Non attribué")


def render_ticket_detail() -> None:
    ticket_id = st.session_state.selected_ticket_id or st.session_state.nav_ticket_id
    if not ticket_id:
        set_navigation("user_home" if _role_label() == "Utilisateur" else "agent_dashboard", None)
        st.rerun()

    st.session_state.selected_ticket_id = ticket_id
    try:
        ticket = _backend().get_ticket(st.session_state.auth_session["access_token"], ticket_id)
    except APIError as exc:
        # Handle Forbidden (403) by redirecting to the appropriate ticket list
        msg = str(exc)
        UI_LOGGER.warning("ticket_access_failed ticket=%s error=%s", ticket_id, msg)
        if "Forbidden" in msg or "403" in msg:
            st.error("Accès refusé pour ce ticket. Si votre session a expiré, reconnectez-vous ci-dessous.")
            with st.form("relogin_form", clear_on_submit=False):
                relogin_email = st.text_input("Email", value=(st.session_state.get("login_email") or ""))
                relogin_password = st.text_input("Mot de passe", type="password")
                relogin_submit = st.form_submit_button("Se reconnecter")
            if relogin_submit:
                try:
                    session = _backend().login(relogin_email.strip().lower(), relogin_password)
                    st.session_state.auth_session = session
                    st.session_state.active_user = session["user"]
                    st.success("Reconnecté avec succès.")
                    st.rerun()
                except APIError as login_exc:
                    st.error(str(login_exc))
            # Allow manual navigation back to lists if user prefers
            if st.button("Retour à la liste des tickets"):
                if _role_label() == "Utilisateur":
                    set_navigation("user_tickets", None)
                else:
                    set_navigation("agent_queue", None)
                st.rerun()
        # For other API errors show the message and stop rendering the detail view
        st.error(msg)
        return
    page_header(ticket["id"], ticket["subject"], right_badge=status_badge(ticket["status"]))
    if st.button("Retour", width="stretch"):
        if _role_label() == "Utilisateur":
            set_navigation("user_tickets", None)
        else:
            set_navigation("agent_queue", None)
        st.rerun()

    if st.session_state.get("flash_message"):
        st.success(st.session_state.flash_message)
        st.session_state.flash_message = ""

    # AI Classification Counter for agents when ticket is "En attente"
    if _role_label() == "Support_IT" and ticket["status"] == "En attente":
        st.markdown(
            """
            <div class="ai-suggestion-box">
              <div class="ai-suggestion-title">💡 Suggestions générées par le modèle d'intelligence artificielle. Vérifiez et ajustez si nécessaire avant de valider.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        # Get AI prediction
        try:
            prediction = _backend().classify(
                st.session_state.auth_session["access_token"],
                ticket["subject"],
                ticket["description"],
                ticket.get("agency"),
            )
            teams = _load_teams()
            
            st.markdown(
                f"""
                <div class="ai-suggestion-box">
                  <div class="ai-suggestion-title">💡 Suggestions IA</div>
                  <div class="ai-suggestion-item">
                    <div class="ai-suggestion-label">Provenance:</div>
                    <div class="ai-suggestion-value">{prediction.get('origine_ticket', 'Inconnue')}</div>
                  </div>
                  <div class="ai-suggestion-item">
                    <div class="ai-suggestion-label">Service concerné:</div>
                    <div class="ai-suggestion-value">{prediction.get('service_concerne', 'Inconnu')}</div>
                  </div>
                  <div class="ai-suggestion-item">
                    <div class="ai-suggestion-label">Équipe suggérée:</div>
                    <div class="ai-suggestion-value">{prediction.get('equipe_cible_suggeree', 'Inconnue')}</div>
                  </div>
                  <div class="ai-suggestion-item">
                    <div class="ai-suggestion-label">Catégorie suggérée:</div>
                    <div class="ai-suggestion-value">{prediction['category']}</div>
                  </div>
                  <div class="ai-suggestion-item">
                    <div class="ai-suggestion-label">Priorité suggérée:</div>
                    <div class="ai-suggestion-value">{prediction['priority']}</div>
                  </div>
                  <div class="ai-suggestion-item">
                    <div class="ai-suggestion-label">Équipe cible:</div>
                    <div class="ai-suggestion-value">{prediction['team_name']}</div>
                  </div>
                  <div class="ai-suggestion-item">
                    <div class="ai-suggestion-label">Confiance:</div>
                    <div class="ai-suggestion-value">{prediction['confidence']:.0%}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            # Agent can accept or correct
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Accepter les suggestions", type="primary", width="stretch"):
                    try:
                        _backend().approve_ai_suggestions(
                            st.session_state.auth_session["access_token"],
                            ticket_id,
                            prediction["category"],
                            prediction["priority"],
                            prediction["team_slug"],
                            corrected=False,
                            service_concerne=prediction.get("service_concerne")
                        )
                        st.session_state.flash_message = "Suggestions IA acceptées. Ticket routé vers l'équipe et mis en cours."
                        st.rerun()
                    except APIError as exc:
                        st.error(str(exc))
            
            with col2:
                with st.expander("Corriger et mettre à jour"):
                    corrected_category = st.selectbox("Catégorie", ["Outlook", "Réseau", "Logiciels", "Matériel", "Autre"])
                    corrected_priority = st.selectbox("Priorité", ["Faible", "Moyenne", "Élevée", "Critique"])
                    corrected_team = st.selectbox("Équipe", [(t["slug"], t["name"]) for t in teams], format_func=lambda x: x[1])
                    if st.button("Confirmer et Mettre à jour", type="primary", width="stretch"):
                        try:
                            _backend().approve_ai_suggestions(
                                st.session_state.auth_session["access_token"],
                                ticket_id,
                                corrected_category,
                                corrected_priority,
                                corrected_team[0],
                                corrected=True
                            )
                            st.session_state.flash_message = "Correction appliquée. Ticket routé et IA retrainée avec les nouvelles données."
                            st.rerun()
                        except APIError as exc:
                            st.error(str(exc))
        except APIError:
            st.warning("Impossible d'obtenir les suggestions IA.")

    left, right = st.columns([0.58, 0.42])
    with left:
        st.markdown('<div class="panel"><div class="section-title">Détails</div>', unsafe_allow_html=True)
        st.write(f"**Auteur :** {ticket['requester_name']}")
        if ticket.get("origine_ticket"):
            st.write(f"**Provenance :** {ticket['origine_ticket']}")
        st.write(f"**Date :** {ticket['created_at']}")
        st.write(f"**Statut :** {ticket['status']}")
        if ticket['category']:
            st.write(f"**Catégorie :** {ticket['category']}")
        if ticket['priority']:
            st.write(f"**Priorité :** {ticket['priority']}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel"><div class="section-title">Description du ticket</div>', unsafe_allow_html=True)
        st.write(ticket['description'])
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.active_user['role'] == 'Utilisateur' and ticket['status'] not in {'Résolu', 'Clôturé'} and ticket['allow_user_edit']:
            with st.form('user_ticket_edit', border=False):
                subject = st.text_input('Sujet', value=ticket['subject'])
                description = st.text_area('Description', value=ticket['description'], height=160)
                submitted = st.form_submit_button('Sauvegarder')
            if submitted:
                updated = _backend().update_ticket(
                    st.session_state.auth_session['access_token'],
                    ticket['id'],
                    {'subject': subject, 'description': description},
                )
                st.session_state.selected_ticket_id = updated['id']
                st.rerun()

        if ticket['status'] == 'Clôturé':
            st.info("Ticket clôturé. Les commentaires restent disponibles, mais aucune modification n'est autorisée.")

    with right:
        st.markdown('<div class="panel"><div class="section-title">Fil de discussion</div>', unsafe_allow_html=True)
        for comment in ticket['comments']:
            st.write(f"{comment['created_at']}: {comment['author_name']} ({comment['author_role']}) - {comment['body']}")
        st.markdown('</div>', unsafe_allow_html=True)

        # Show audit logs for support agents
        if _role_label() == 'Support_IT':
            st.markdown('<div class="panel"><div class="section-title">Journal d\'audit</div>', unsafe_allow_html=True)
            try:
                audit_logs = _backend().get_ticket_audit_logs(st.session_state.auth_session['access_token'], ticket_id)
                if audit_logs:
                    for log in audit_logs:
                        with st.expander(f"{log['created_at']}: {log['action']}", expanded=False):
                            st.write(f"**Acteur ID:** {log['actor_user_id'] or 'Système'}")
                            st.write(f"**Entité:** {log['entity_type']} ({log['entity_id']})")
                            st.write(f"**Action:** {log['action']}")
                            st.json(log['payload_json'])
                else:
                    st.caption("Aucun journal d'audit disponible.")
            except APIError:
                st.caption("Impossible de charger le journal d'audit.")
            st.markdown('</div>', unsafe_allow_html=True)

        with st.form('comment_form', border=False, clear_on_submit=True):
            comment_text = st.text_area('Ajouter un commentaire', height=100)
            submitted_comment = st.form_submit_button('Envoyer')
        if submitted_comment and comment_text.strip():
            updated = _backend().add_comment(
                st.session_state.auth_session['access_token'],
                ticket['id'],
                comment_text.strip(),
                is_internal=_role_label() == 'Support_IT',
            )
            st.session_state.selected_ticket_id = updated['id']
            st.rerun()

        if _role_label() == 'Support_IT':
            st.markdown('<div class="panel"><div class="section-title">Gestion du ticket</div>', unsafe_allow_html=True)
            if ticket['status'] != 'Clôturé':
                new_status = st.selectbox(
                    'Statut',
                    ['Ouvert', 'En cours', 'En attente', 'Résolu', 'Clôturé'],
                    index=['Ouvert', 'En cours', 'En attente', 'Résolu', 'Clôturé'].index(ticket['status']),
                    label_visibility='collapsed',
                )
                resolution = st.text_area('Note de résolution', height=100)
                if st.button('Appliquer le statut', width='stretch'):
                    updated = _backend().change_status(st.session_state.auth_session['access_token'], ticket['id'], new_status)
                    if resolution.strip():
                        _backend().add_comment(
                            st.session_state.auth_session['access_token'],
                            ticket['id'],
                            f"Résolution: {resolution.strip()}",
                            is_internal=True,
                        )
                    st.session_state.selected_ticket_id = updated['id']
                    st.rerun()
            else:
                st.caption('Statut verrouillé pour un ticket clôturé.')
            st.markdown('</div>', unsafe_allow_html=True)

            if ticket['status'] != 'Clôturé':
                with st.expander('Corriger l’attribution IA', expanded=False):
                    st.markdown('**Corriger l’attribution IA**')
                    st.caption('Réattribuez ce ticket si le modèle a choisi le mauvais département ou le mauvais agent.')
                    teams = _load_teams()
                    if teams:
                        team_ids = [team['id'] for team in teams]
                        team_by_id = {team['id']: team for team in teams}
                        current_team_index = next((idx for idx, team_id in enumerate(team_ids) if team_id == ticket['team_id']), 0)
                        selected_team_id = st.selectbox(
                            'Département cible',
                            team_ids,
                            index=current_team_index,
                            format_func=lambda team_id: team_by_id[team_id]['name'],
                            key=f"reassign_team_{ticket['id']}",
                        )
                        agents = _backend().list_agents(st.session_state.auth_session['access_token'], team_id=selected_team_id)
                        agent_ids = [agent['id'] for agent in agents]
                        if agent_ids:
                            current_agent_index = next((idx for idx, agent_id in enumerate(agent_ids) if agent_id == ticket.get('assigned_agent_id')), 0)
                            agent_names = {
                                agent['id']: f"{agent['user_name']}{' - ' + agent['title'] if agent.get('title') else ''}"
                                for agent in agents
                            }
                            selected_agent_id = st.selectbox(
                                'Agent cible',
                                agent_ids,
                                index=current_agent_index,
                                format_func=lambda agent_id: agent_names[agent_id],
                                key=f"reassign_agent_{ticket['id']}",
                            )
                        else:
                            selected_agent_id = None
                            st.warning("Aucun agent actif n'est disponible dans ce département.")
                        reason = st.text_area(
                            'Motif de correction',
                            key=f"reassign_reason_{ticket['id']}",
                            height=90,
                            placeholder='Ex: le ticket a été routé vers le mauvais département.',
                        )
                        if st.button('Réattribuer', type='primary', width='stretch', disabled=not agent_ids):
                            try:
                                updated = _backend().assign_ticket(
                                    st.session_state.auth_session['access_token'],
                                    ticket['id'],
                                    to_team_id=selected_team_id,
                                    to_agent_id=selected_agent_id,
                                    reason=reason.strip(),
                                )
                                st.session_state.selected_ticket_id = updated['id']
                                st.session_state.flash_message = 'Attribution corrigée avec succès.'
                                # Redirect back to the agent queue so the agent sees the updated list
                                set_navigation('agent_queue', None)
                                st.rerun()
                            except APIError as exc:
                                msg = str(exc)
                                UI_LOGGER.warning("assign_ticket_failed ticket=%s error=%s", ticket['id'], msg)
                                # If Forbidden, try to restore session using existing session keys and retry once
                                if 'Forbidden' in msg or '403' in msg:
                                    sess = st.session_state.get('auth_session') or {}
                                    sid = sess.get('session_id')
                                    sk = sess.get('session_key')
                                    if sid and sk:
                                        try:
                                            restored = _backend().restore(sid, sk)
                                            set_session(restored)
                                            # Retry assignment once
                                            updated = _backend().assign_ticket(
                                                st.session_state.auth_session['access_token'],
                                                ticket['id'],
                                                to_team_id=selected_team_id,
                                                to_agent_id=selected_agent_id,
                                                reason=reason.strip(),
                                            )
                                            st.session_state.selected_ticket_id = updated['id']
                                            st.session_state.flash_message = 'Attribution corrigée avec succès.'
                                            set_navigation('agent_queue', None)
                                            st.rerun()
                                        except APIError as exc2:
                                            st.error(str(exc2))
                                            # fallback: redirect to agent queue
                                            set_navigation('agent_queue', None)
                                            st.rerun()
                                    else:
                                        st.error('Accès refusé et aucune session de restauration disponible. Veuillez vous reconnecter.')
                                else:
                                    st.error(msg)
                    else:
                        st.warning('Aucune équipe disponible pour la réattribution.')


def render_interventions() -> None:
    """Display the field-intervention workspace for support agents."""
    page_header("Interventions terrain", "Suivi des rapports d'intervention ID Colis")
    tickets = _load_tickets()
    if not tickets:
        st.info("Aucun ticket disponible pour créer une intervention.")
        return
    labels = {f"{t['id']} · {t['subject']}": t for t in tickets}
    selected_label = st.selectbox("Ticket concerné", list(labels), key="intervention_ticket_select")
    ticket = labels[selected_label]
    token = st.session_state.auth_session["access_token"]
    try:
        existing = _backend().list_interventions(token, ticket["id"])
    except APIError as exc:
        st.error(str(exc))
        return
    st.caption(f"Agence : {ticket.get('agency') or 'Non renseignée'} · Agence locale : {ticket.get('site') or 'Non renseignée'}")
    with st.form("field_intervention_form", clear_on_submit=False):
        diagnosis = st.text_area("Diagnostic initial et détaillé")
        actions = st.text_area("Actions réalisées")
        equipment = st.text_input("Systèmes, ordinateurs ou équipements concernés")
        tests = st.text_area("Tests effectués")
        result = st.selectbox("Résultat", ["Brouillon", "Résolu", "Partiellement résolu", "Non résolu", "Escaladé"])
        follow_up = st.text_area("Suivi recommandé / prochaine action")
        notes = st.text_area("Notes du technicien")
        submitted = st.form_submit_button("Enregistrer le rapport", type="primary", width="stretch")
    if submitted:
        payload = {"agency": ticket.get("agency"), "site": ticket.get("site"), "city": ticket.get("city"), "diagnosis": diagnosis, "actions_performed": actions, "equipment_involved": equipment, "tests_performed": tests, "result": result, "follow_up": follow_up, "technician_notes": notes}
        try:
            if existing:
                _backend().update_intervention(token, existing[0]["id"], payload)
            else:
                _backend().create_intervention(token, ticket["id"], payload)
            st.success("Rapport d’intervention enregistré.")
            st.rerun()
        except APIError as exc:
            st.error(str(exc))
    if existing:
        st.markdown("### Rapports existants")
        for report in existing:
            st.write(f"{report['intervention_number']} · {report['result']} · {report.get('updated_at', '')}")


def render_diagnostics() -> None:
    """Display basic backend diagnostics and local application status."""
    page_header("Diagnostics système", "État du backend et des services ID Colis")
    api = _backend()
    try:
        health = api._json(api._request("GET", "/api/health"))
        st.success(f"Backend disponible - environnement: {health.get('env', 'inconnu')}")
    except Exception as exc:
        st.error(f"Backend indisponible: {exc}")


