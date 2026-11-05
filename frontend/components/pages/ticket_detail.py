from __future__ import annotations

import html

import streamlit as st

from constants import LOGISTICS_CATEGORIES, PRIORITY_LEVELS
from services.api import APIError
from services.session import set_navigation
from views.layout import status_badge

from components.common import UI_LOGGER, _backend, _group_identical_reports, _load_teams, _role_label

def _render_ticket_activity(ticket: dict) -> None:
    st.markdown('<div class="panel"><div class="section-title">Activité et échanges</div>', unsafe_allow_html=True)
    for comment in ticket['comments']:
        st.markdown(
            f'''<div class="comment-card"><div class="comment-author">{comment['author_name']} <span class="comment-time">· {comment['author_role']}</span></div>
            <div class="comment-time">{comment['created_at']}</div><div style="margin-top:.4rem;color:var(--idc-navy);">{comment['body']}</div></div>''',
            unsafe_allow_html=True,
        )
    if not ticket['comments']:
        st.caption("Aucune activité pour le moment.")
    st.markdown('</div>', unsafe_allow_html=True)


@st.dialog("Validation de la suggestion IA", width="large")
def _render_ai_validation_dialog(ticket: dict, ticket_id: str) -> None:
    """Block the rest of the ticket page until the agent accepts or rejects
    the AI's classification. The decision (as-is or corrected) is fed back
    to the model, so skipping it silently would starve its retraining data."""
    st.caption("Vérifiez la suggestion générée par le modèle avant de continuer. Votre décision permet aussi de réentraîner l’IA.")
    try:
        prediction = _backend().classify(
            st.session_state.auth_session["access_token"],
            ticket["subject"],
            ticket["description"],
            ticket.get("agency"),
        )
    except APIError:
        st.warning("Impossible d'obtenir les suggestions IA.")
        if st.button("Fermer", width="stretch"):
            st.session_state[f"ai_dismissed_{ticket_id}"] = True
            st.rerun()
        return

    if prediction["confidence"] < 0.6:
        st.warning(f"Confiance faible ({prediction['confidence']:.0%}) — vérifiez attentivement avant de valider.")

    st.markdown(
        f"""
        <div class="ai-suggestion-box">
          <div class="ai-suggestion-title">Analyse ID Colis</div>
          <div class="ai-suggestion-item">
            <div class="ai-suggestion-label">Catégorie logistique:</div>
            <div class="ai-suggestion-value">{prediction['category']}</div>
          </div>
          <div class="ai-suggestion-item">
            <div class="ai-suggestion-label">Priorité opérationnelle:</div>
            <div class="ai-suggestion-value">{prediction['priority']}</div>
          </div>
          <div class="ai-suggestion-item">
            <div class="ai-suggestion-label">Équipe de routage:</div>
            <div class="ai-suggestion-value">{prediction['team_name']}</div>
          </div>
          <div class="ai-suggestion-item">
            <div class="ai-suggestion-label">Intervention terrain:</div>
            <div class="ai-suggestion-value">À confirmer par l’agent selon l’impact et le matériel concerné</div>
          </div>
          <div class="ai-suggestion-item">
            <div class="ai-suggestion-label">Fiabilité et justification:</div>
            <div class="ai-suggestion-value">{prediction['confidence']:.0%} · {prediction.get('notes', 'Analyse automatique')}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        similar = _backend().similar_tickets(st.session_state.auth_session["access_token"], ticket_id)
    except APIError:
        similar = {"possible_duplicates": [], "similar_resolved": []}

    if similar.get("possible_duplicates"):
        st.warning("Ce ticket ressemble à d'autres tickets déjà ouverts pour cette agence — vérifiez qu'il ne s'agit pas d'un doublon.")
        for dup in similar["possible_duplicates"]:
            st.markdown(
                f'<div class="idc-list-row"><span>{dup["id"]} · {dup["subject"]}</span><span class="idc-list-value">{dup["similarity"]:.0%}</span></div>',
                unsafe_allow_html=True,
            )

    if similar.get("similar_resolved"):
        with st.expander("Tickets similaires déjà résolus (référence rapide)"):
            for ref in similar["similar_resolved"]:
                st.markdown(
                    f'<div class="idc-list-row"><span>{ref["id"]} · {ref["subject"]}</span><span class="idc-list-value">{ref["similarity"]:.0%}</span></div>',
                    unsafe_allow_html=True,
                )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Accepter la suggestion", type="primary", width="stretch", key=f"ai_accept_{ticket_id}"):
            try:
                _backend().approve_ai_suggestions(
                    st.session_state.auth_session["access_token"],
                    ticket_id,
                    prediction["category"],
                    prediction["priority"],
                    prediction["team_slug"],
                    corrected=False,
                    service_concerne=prediction.get("service_concerne"),
                )
                st.session_state.flash_message = "Suggestions IA acceptées. Ticket routé vers l'équipe et mis en cours."
                st.session_state[f"ai_accepted_{ticket_id}"] = True
                st.rerun()
            except APIError as exc:
                st.error(str(exc))
    with col2:
        if st.button("Rejeter et corriger", width="stretch", key=f"ai_reject_{ticket_id}"):
            st.session_state[f"ai_rejecting_{ticket_id}"] = True
            st.rerun()

    if st.session_state.get(f"ai_rejecting_{ticket_id}"):
        st.divider()
        st.markdown("**Corriger la classification**")
        teams = _load_teams()
        corrected_category = st.selectbox("Catégorie logistique", LOGISTICS_CATEGORIES, key=f"ai_reject_category_{ticket_id}")
        corrected_priority = st.selectbox("Priorité opérationnelle", PRIORITY_LEVELS, key=f"ai_reject_priority_{ticket_id}")
        corrected_team = st.selectbox("Équipe", [(t["slug"], t["name"]) for t in teams], format_func=lambda x: x[1], key=f"ai_reject_team_{ticket_id}")
        if st.button("Confirmer la correction", type="primary", width="stretch", key=f"ai_reject_confirm_{ticket_id}"):
            try:
                _backend().approve_ai_suggestions(
                    st.session_state.auth_session["access_token"],
                    ticket_id,
                    corrected_category,
                    corrected_priority,
                    corrected_team[0],
                    corrected=True,
                )
                st.session_state.flash_message = "Suggestion IA rejetée. Correction appliquée et IA réentraînée avec les nouvelles données."
                st.session_state[f"ai_accepted_{ticket_id}"] = True
                st.rerun()
            except APIError as exc:
                st.error(str(exc))


def _render_ticket_audit(ticket_id: str) -> None:
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
    top_left, top_right = st.columns([0.82, 0.18])
    with top_left:
        st.markdown(
            f'''<div class="ticket-hero">
              <div class="ticket-id">{ticket["id"]}</div>
              <div class="ticket-title">{ticket["subject"]}</div>
              <div class="ticket-meta">{ticket.get("agency") or "ID Colis"} · {ticket.get("site") or "Localisation non renseignée"} · {ticket.get("created_at", "")}</div>
            </div>''',
            unsafe_allow_html=True,
        )
    with top_right:
        st.markdown(f'<div style="padding-top:1.25rem;text-align:right;">{status_badge(ticket["status"])}</div>', unsafe_allow_html=True)
    if st.button("← Retour à la file", width="stretch"):
        if _role_label() == "Utilisateur":
            set_navigation("user_tickets", None)
        else:
            set_navigation("agent_queue", None)
        st.rerun()

    if st.session_state.get("flash_message"):
        st.success(st.session_state.flash_message)
        st.session_state.flash_message = ""

    # A newly created ticket must be classified by the agent before they can
    # do anything else with it: the validation dialog below is a blocking
    # modal (st.dialog), not an inline panel the agent could scroll past.
    show_ai_suggestion = (
        _role_label() == "Support_IT"
        and ticket["status"] in {"Créé", "En attente"}
        and not st.session_state.get(f"ai_accepted_{ticket_id}")
        and not st.session_state.get(f"ai_dismissed_{ticket_id}")
    )
    if show_ai_suggestion:
        _render_ai_validation_dialog(ticket, ticket_id)

    # Ticket information uses the full content width. Role-specific controls
    # follow below it, keeping the operational record readable and separated
    # from the audit/activity area.
    left, right = st.container(), st.container()
    with left:
        st.markdown('<div class="panel"><div class="section-title">Résumé opérationnel</div>', unsafe_allow_html=True)
        st.markdown(
            f'''<div class="ticket-info-grid">
              <div class="ticket-info"><div class="ticket-info-label">Demandeur</div><div class="ticket-info-value">{ticket['requester_name']}</div></div>
              <div class="ticket-info"><div class="ticket-info-label">Agence</div><div class="ticket-info-value">{ticket.get('agency') or 'Non renseignée'}</div></div>
              <div class="ticket-info"><div class="ticket-info-label">Catégorie</div><div class="ticket-info-value">{ticket.get('category') or 'À qualifier'}</div></div>
              <div class="ticket-info"><div class="ticket-info-label">Priorité</div><div class="ticket-info-value">{ticket.get('priority') or 'À évaluer'}</div></div>
              <div class="ticket-info"><div class="ticket-info-label">Poste / agence locale</div><div class="ticket-info-value">{ticket.get('site') or 'Non renseigné'}</div></div>
              <div class="ticket-info"><div class="ticket-info-label">Équipe assignée</div><div class="ticket-info-value">{ticket.get('team_name') or 'Non attribuée'}</div></div>
            </div>''',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="panel"><div class="section-title">Description de l’incident</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ticket-description">{html.escape(ticket["description"] or "Aucune description fournie.")}</div>', unsafe_allow_html=True)
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
        if _role_label() == 'Utilisateur' and ticket['status'] == 'En attente de validation':
            st.info('Le régulateur a approuvé le rapport. Vérifiez avec le support que le problème est bien résolu, puis validez le ticket.')
            if st.button('Valider que le problème est résolu', type='primary', key=f"validate_ticket_{ticket_id}", width='stretch'):
                try:
                    _backend().validate_ticket(st.session_state.auth_session['access_token'], ticket_id)
                    st.rerun()
                except APIError as exc:
                    st.error(str(exc))

    with right:
        if _role_label() == 'Support_IT':
            with st.container(border=True):
                st.markdown('<div class="section-title">Gestion du ticket</div>', unsafe_allow_html=True)
                if ticket['status'] in {'Résolu', 'Clôturé'}:
                    st.caption('Ticket clôturé : une nouvelle demande nécessite un nouveau ticket.')
                elif st.button('Démarrer une intervention', key=f"start_intervention_{ticket_id}", width='stretch'):
                    st.session_state.intervention_ticket_id = ticket_id
                    st.session_state.intervention_create_mode = True
                    set_navigation('interventions', None)
                    st.rerun()

        if _role_label() == 'Régulateur_Agence':
            with st.container(border=True):
                st.markdown('<div class="section-title">Validation du rapport d’intervention</div>', unsafe_allow_html=True)
                try:
                    interventions = _backend().list_interventions(st.session_state.auth_session['access_token'], ticket_id)
                except APIError:
                    interventions = []
                if not interventions:
                    st.info('Aucun rapport d’intervention à valider.')
                for group in _group_identical_reports(interventions):
                    report = group['report']
                    duplicate_tag = f" · {group['count']} rapports identiques" if group['count'] > 1 else ""
                    title = f"{report.get('intervention_number', 'Intervention')} · {report.get('result', '')} · {report.get('review_status', 'En attente de validation')}{duplicate_tag}"
                    with st.expander(title, expanded=report.get('review_status') != 'Approuvée'):
                        intervention_date = str(report.get('started_at') or report.get('created_at') or '—')[:10]
                        st.caption(f"Date d'intervention : {intervention_date} · Dernière mise à jour {report.get('updated_at', '—')}")
                        if group['count'] > 1:
                            st.caption(f"Soumis {group['count']} fois à l'identique, entre {str(group['first_created_at'])[:10]} et {str(group['last_created_at'])[:10]}.")
                        details = (
                            ('Intervenant / contact client', report.get('contact_name')),
                            ('Diagnostic', report.get('diagnosis')),
                            ('Travail réalisé', report.get('actions_performed')),
                            ('Équipement concerné', report.get('equipment_involved')),
                            ('Tests effectués', report.get('tests_performed')),
                            ('Pièces / temps passé', report.get('materials_used')),
                            ('Résultat', report.get('result')),
                            ('Prochaine action', report.get('follow_up')),
                            ('Notes du technicien', report.get('technician_notes')),
                        )
                        for label, value in details:
                            if value:
                                st.markdown(f"**{label}**\n\n{html.escape(str(value))}")
                        if report.get('review_feedback'):
                            st.warning(f"Retour précédent : {report['review_feedback']}")
                        if report.get('review_status') != 'Approuvée' and report['id'] == interventions[-1]['id']:
                            feedback = st.text_area('Retour du régulateur', key=f"review_feedback_{report['id']}")
                            review_col1, review_col2 = st.columns(2)
                            with review_col1:
                                if st.button('Demander une correction', key=f"review_correction_{report['id']}", width='stretch'):
                                    try:
                                        _backend().review_intervention(st.session_state.auth_session['access_token'], report['id'], 'correction_required', feedback)
                                        st.rerun()
                                    except APIError as exc:
                                        st.error(str(exc))
                            with review_col2:
                                if st.button('Approuver le rapport', key=f"review_approve_{report['id']}", width='stretch'):
                                    try:
                                        _backend().review_intervention(st.session_state.auth_session['access_token'], report['id'], 'approved', feedback)
                                        st.rerun()
                                    except APIError as exc:
                                        st.error(str(exc))

    # These two operational views intentionally sit below the description and
    # management area, using the complete page width instead of competing with
    # the ticket summary for vertical space.
    if _role_label() == 'Support_IT':
        audit_col, activity_col = st.columns(2, gap="large")
        with audit_col:
            _render_ticket_audit(ticket_id)
        with activity_col:
            _render_ticket_activity(ticket)

        with st.expander('Corriger l’attribution IA', expanded=False):
            st.markdown('**Corriger l’attribution IA**')
            st.caption('Réattribuez ce ticket si le modèle a choisi le mauvais département ou le mauvais agent.')
            teams = _load_teams()
            if teams:
                team_ids = [team['id'] for team in teams]
                team_by_id = {team['id']: team for team in teams}
                current_team_index = next((idx for idx, team_id in enumerate(team_ids) if team_id == ticket['team_id']), 0)
                selected_team_id = st.selectbox(
                    'Département cible', team_ids, index=current_team_index,
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
                        'Agent cible', agent_ids,
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
                        set_navigation('agent_queue', None)
                        st.rerun()
                    except APIError as exc:
                        msg = str(exc)
                        UI_LOGGER.warning("assign_ticket_failed ticket=%s error=%s", ticket['id'], msg)
                        st.error(msg)
                    else:
                        st.warning('Aucune équipe disponible pour la réattribution.')


