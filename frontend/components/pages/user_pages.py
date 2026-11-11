from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from constants import LOGISTICS_CATEGORIES, PRIORITY_LEVELS, BLUE, GREEN, ORANGE
from i18n import lang_key, t
from services.api import APIError
from services.session import set_navigation
from views.layout import metric_card, page_header, ticket_card

from components.common import _apply_time_filter, _backend, _current_user_id, _load_teams, _load_tickets, _role_label, _ticket_created_date

def render_user_home() -> None:
    page_header(t("Accueil"), t("Espace utilisateur"))
    tickets = _load_tickets()
    mine = [ticket for ticket in tickets if ticket["requester_user_id"] == _current_user_id()]
    categories = ["Toutes"] + sorted({ticket["category"] for ticket in mine})
    current_category = st.session_state.get("user_home_category_filter", "Toutes")
    st.markdown(f"<div class='idc-eyebrow'>{t('Filtrer mes tickets')}</div>", unsafe_allow_html=True)
    category_cols = st.columns(min(4, len(categories)))
    for index, category in enumerate(categories):
        with category_cols[index % len(category_cols)]:
            if st.button(t(category), key=f"home_category_{index}", width="stretch", type="primary" if current_category == category else "secondary"):
                st.session_state.user_home_category_filter = category
                st.rerun()
    category_filter = st.session_state.get("user_home_category_filter", "Toutes")
    if category_filter != "Toutes":
        mine = [ticket for ticket in mine if ticket["category"] == category_filter]
    period_options = ["Tous", "Aujourd’hui", "7 derniers jours", "30 derniers jours"]
    current_period = st.session_state.get("user_home_time_preset", "Tous")
    period_cols = st.columns(len(period_options))
    for index, period in enumerate(period_options):
        with period_cols[index]:
            if st.button(t(period), key=f"home_period_{index}", width="stretch", type="primary" if current_period == period else "secondary"):
                st.session_state.user_home_time_preset = period
                st.rerun()
    if current_period != "Tous":
        today = date.today()
        start = today if current_period == "Aujourd’hui" else today - timedelta(days=7 if current_period.startswith("7") else 30)
        mine = [ticket for ticket in mine if (created := _ticket_created_date(ticket)) and start <= created <= today]

    total = len(mine)
    open_count = sum(1 for ticket in mine if ticket["status"] == "En attente")
    in_progress = sum(1 for ticket in mine if ticket["status"] == "En cours")
    resolved = sum(1 for ticket in mine if ticket["status"] in {"Résolu", "Clôturé"})
    cols = st.columns(3)
    for col, payload in zip(
        cols,
        [
            (t("Mes tickets"), str(total), t("Demandes créées"), BLUE),
            (t("Actifs"), str(open_count + in_progress), t("Tickets ouverts et en cours"), GREEN),
            (t("Résolus"), str(resolved), t("Tickets clôturés"), ORANGE),
        ],
    ):
        with col:
            st.markdown(metric_card(*payload), unsafe_allow_html=True)

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{t("Derniers tickets")}</div>', unsafe_allow_html=True)
    if not mine:
        st.info(t("Aucun ticket pour le moment."))
    for ticket in mine[:8]:
        meta = f"{t(ticket['category'])} · {t(ticket['team_name'])}"
        if ticket_card(ticket, "user_open", meta):
            st.session_state.selected_ticket_id = ticket["id"]
            set_navigation("ticket_detail", ticket["id"])
            st.rerun()


def render_ticket_create() -> None:
    # Initialize wizard step
    if "wizard_step" not in st.session_state:
        st.session_state.wizard_step = 1

    page_header(t("Nouveau ticket"), t("Création de demande de support"))

    # For regular users: Simple form (no wizard)
    if _role_label() == "Utilisateur":
        st.markdown(f'<div class="section-title">{t("Informations générales")}</div>', unsafe_allow_html=True)
        subject = st.text_input(t("Sujet"), key="create_subject")
        description = st.text_area(t("Description détaillée"), key="create_description", height=180, max_chars=2000)
        char_count = len(description)
        st.caption(t("Caractères: {count}/2000", count=char_count))
        if description.strip() and len(description.strip()) < 25:
            st.info(t("Description un peu courte : précisez par exemple l'appareil concerné, depuis quand, et ce qui s'affiche à l'écran. Cela aide l'équipe à traiter votre ticket plus vite."))

        if subject.strip() and description.strip() and st.button(t("Vérifier une solution rapide"), width="stretch"):
            try:
                result = _backend().self_help(st.session_state.auth_session["access_token"], subject, description)
            except APIError:
                result = {"matched": False}
            st.session_state.self_help_result = result

        self_help_result = st.session_state.get("self_help_result")
        if self_help_result and self_help_result.get("matched"):
            with st.container(border=True):
                st.markdown(f'<div class="idc-card-title">{t(self_help_result["title"])}</div>', unsafe_allow_html=True)
                st.caption(t("Essayez ces étapes avant de créer un ticket — cela résout souvent le problème en quelques minutes."))
                for index, step in enumerate(self_help_result["steps"], start=1):
                    st.markdown(f"**{index}.** {t(step)}")
                help_col1, help_col2 = st.columns(2)
                with help_col1:
                    if st.button(t("C'est résolu, merci"), type="primary", width="stretch"):
                        st.session_state.pop("self_help_result", None)
                        set_navigation("user_home", None)
                        st.rerun()
                with help_col2:
                    if st.button(t("Toujours un problème, créer le ticket"), width="stretch"):
                        st.session_state.pop("self_help_result", None)
                        st.rerun()

        col1, col2 = st.columns(2)
        with col1:
            if st.button(t("Annuler"), width="stretch"):
                set_navigation("user_home", None)
                st.rerun()
        with col2:
            if st.button(t("Créer le ticket"), type="primary", width="stretch", disabled=not (subject.strip() and description.strip())):
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
                    st.session_state.flash_message = t("Ticket créé avec succès. Statut: En attente.")
                    st.session_state.selected_ticket_id = ticket["id"]
                    st.session_state.pop("self_help_result", None)
                    set_navigation("ticket_detail", ticket["id"])
                    st.rerun()
                except APIError as exc:
                    st.error(str(exc))

    # For agents: Multi-step wizard
    else:
        # STEP 1: General Info & Description
        if st.session_state.wizard_step == 1:
            st.markdown(f'<div class="section-title">{t("Étape 1/3 : Informations générales")}</div>', unsafe_allow_html=True)
            subject = st.text_input(t("Sujet"), key="create_subject")
            description = st.text_area(t("Description détaillée"), key="create_description", height=180, max_chars=2000)
            char_count = len(description)
            st.caption(t("Caractères: {count}/2000", count=char_count))

            col1, col2 = st.columns(2)
            with col1:
                if st.button(t("Annuler"), width="stretch"):
                    st.session_state.wizard_step = 1
                    set_navigation("agent_dashboard", None)
                    st.rerun()
            with col2:
                if st.button(t("Suivant →"), type="primary", width="stretch", disabled=not (subject.strip() and description.strip())):
                    # Store form data
                    st.session_state.wizard_subject = subject
                    st.session_state.wizard_description = description
                    st.session_state.wizard_step = 2
                    st.rerun()

        # STEP 2: AI Classification
        elif st.session_state.wizard_step == 2:
            st.markdown(f'<div class="section-title">{t("Étape 2/3 : Classification IA")}</div>', unsafe_allow_html=True)

            # Show AI banner
            banner = t("Suggestions générées par le modèle. Vérifiez et ajustez si nécessaire avant de valider.")
            st.markdown(
                f"""
                <div class="ai-suggestion-box">
                  <div class="ai-suggestion-title">{banner}</div>
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
                suggestion_title = t("Suggestions IA basées sur l’origine et le contenu")
                origin_label = t("Provenance détectée:")
                origin_value = prediction.get("origine_ticket") or t("Inconnue")
                service_label = t("Service concerné:")
                service_value = prediction.get("service_concerne") or t("Inconnu")
                st.markdown(
                    f"""
                    <div class="ai-suggestion-box">
                      <div class="ai-suggestion-title">{suggestion_title}</div>
                      <div class="ai-suggestion-item">
                        <div class="ai-suggestion-label">{origin_label}</div>
                        <div class="ai-suggestion-value">{origin_value}</div>
                      </div>
                      <div class="ai-suggestion-item">
                        <div class="ai-suggestion-label">{service_label}</div>
                        <div class="ai-suggestion-value">{service_value}</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                col1, col2 = st.columns(2)
                with col1:
                    category = st.selectbox(t("Catégorie suggérée"), LOGISTICS_CATEGORIES, format_func=t,
                                          index=LOGISTICS_CATEGORIES.index(prediction["category"]) if prediction["category"] in LOGISTICS_CATEGORIES else 0)
                    priority = st.selectbox(t("Priorité suggérée"), PRIORITY_LEVELS, format_func=t,
                                         index=PRIORITY_LEVELS.index(prediction["priority"]) if prediction["priority"] in PRIORITY_LEVELS else 1)
                with col2:
                    team_options = [(team["slug"], team["name"]) for team in teams]
                    team_index = next((i for i, (slug, name) in enumerate(team_options) if slug == prediction["team_slug"]), 0)
                    selected_team = st.selectbox(t("Équipe cible"), team_options, index=team_index, format_func=lambda x: t(x[1]))

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(t("← Précédent"), width="stretch"):
                        st.session_state.wizard_step = 1
                        st.rerun()
                with col2:
                    if st.button(t("Suivant →"), type="primary", width="stretch"):
                        st.session_state.wizard_category = category
                        st.session_state.wizard_priority = priority
                        st.session_state.wizard_team = selected_team[0]
                        st.session_state.wizard_service_concerne = prediction.get("service_concerne")
                        st.session_state.wizard_step = 3
                        st.rerun()
            except APIError:
                st.warning(t("Impossible d'obtenir les suggestions IA."))
                if st.button(t("← Précédent"), width="stretch"):
                    st.session_state.wizard_step = 1
                    st.rerun()

        # STEP 3: Confirmation
        elif st.session_state.wizard_step == 3:
            st.markdown(f'<div class="section-title">{t("Étape 3/3 : Confirmation")}</div>', unsafe_allow_html=True)

            st.markdown(f'<div class="panel"><div class="section-title">{t("Résumé du ticket")}</div>', unsafe_allow_html=True)
            st.write(f"**{t('Sujet')} :** {st.session_state.wizard_subject}")
            st.write(f"**{t('Description')} :** {st.session_state.wizard_description}")
            st.write(f"**{t('Catégorie')} :** {t(st.session_state.wizard_category)}")
            st.write(f"**{t('Priorité')} :** {t(st.session_state.wizard_priority)}")
            st.write(f"**{t('Équipe')} :** {st.session_state.wizard_team}")
            st.markdown('</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button(t("← Précédent"), width="stretch"):
                    st.session_state.wizard_step = 2
                    st.rerun()
            with col2:
                if st.button(t("Créer le ticket"), type="primary", width="stretch"):
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
                        st.session_state.flash_message = t("Ticket créé et routé vers l'équipe.")

                        # Reset wizard
                        st.session_state.wizard_step = 1
                        st.session_state.selected_ticket_id = ticket["id"]
                        set_navigation("ticket_detail", ticket["id"])
                        st.rerun()
                    except APIError as exc:
                        st.error(str(exc))


def render_user_tickets() -> None:
    page_header(t("Mes tickets"), t("Suivi personnel"))
    tickets = _load_tickets()
    mine = [ticket for ticket in tickets if ticket["requester_user_id"] == _current_user_id()]
    category_filter = st.selectbox(t("Catégorie"), ["Toutes"] + sorted({ticket["category"] for ticket in mine}), key=lang_key("user_tickets_category_filter"), format_func=t)
    if category_filter != "Toutes":
        mine = [ticket for ticket in mine if ticket["category"] == category_filter]
    mine = _apply_time_filter(mine, "user_tickets")
    if not mine:
        st.info(t("Aucun ticket ne correspond à ces filtres."))
    for ticket in mine:
        meta = f"{t(ticket['category'])} · {t(ticket['team_name'])}"
        if ticket_card(ticket, "open_mine", meta):
            st.session_state.selected_ticket_id = ticket["id"]
            set_navigation("ticket_detail", ticket["id"])
            st.rerun()
    if st.button(t("Retour"), width="stretch"):
        set_navigation("user_home", None)
        st.rerun()
