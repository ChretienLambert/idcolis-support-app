from __future__ import annotations

import html

import streamlit as st

from services.api import APIError
from services.session import set_navigation
from views.layout import page_header

from components.common import _backend, _load_tickets

def render_interventions() -> None:
    """Display interventions attached to tickets; creation starts from a ticket."""
    page_header("Interventions", "Rapports liés aux tickets ID Colis")
    if st.session_state.get("flash_message"):
        st.success(st.session_state.flash_message)
        st.session_state.flash_message = ""
    tickets = _load_tickets()
    if not tickets:
        st.info("Aucun ticket disponible pour créer une intervention.")
        return
    labels = {f"{t['id']} · {t['subject']}": t for t in tickets}
    selected_ticket_id = st.session_state.get("intervention_ticket_id")
    if not selected_ticket_id:
        st.caption("Les interventions sont toujours rattachées à un ticket.")
        for label, linked_ticket in labels.items():
            existing = _backend().list_interventions(st.session_state.auth_session["access_token"], linked_ticket["id"])
            with st.container(border=True):
                row = st.columns([0.62, 0.20, 0.18], vertical_alignment="center")
                with row[0]:
                    st.markdown(f'<div class="idc-ticket-card-title">{label}</div>', unsafe_allow_html=True)
                    if existing:
                        latest = existing[-1]
                        st.markdown(f'<div class="idc-ticket-card-meta">{len(existing)} intervention(s) · {latest.get("review_status", "En attente de validation")}</div>', unsafe_allow_html=True)
                        if latest.get('review_feedback'):
                            st.caption(f"Retour régulateur : {latest['review_feedback']}")
                    else:
                        st.markdown('<div class="idc-ticket-card-meta">Aucune intervention</div>', unsafe_allow_html=True)
                with row[1]:
                    if st.button("Voir le ticket", key=f"ticket_link_interventions_{linked_ticket['id']}", width="stretch"):
                        set_navigation("ticket_detail", linked_ticket["id"])
                        st.rerun()
                with row[2]:
                    if st.button("Ouvrir →", key=f"open_interventions_{linked_ticket['id']}", width="stretch"):
                        st.session_state.intervention_ticket_id = linked_ticket["id"]
                        st.session_state.intervention_create_mode = False
                        st.rerun()
        return
    selected_label = next((label for label, item in labels.items() if item["id"] == selected_ticket_id), None)
    if not selected_label:
        st.session_state.pop("intervention_ticket_id", None)
        st.rerun()
    if st.button("Retour à la liste des interventions", key="back_to_intervention_list"):
        st.session_state.pop("intervention_ticket_id", None)
        st.session_state.pop("intervention_create_mode", None)
        st.rerun()
    ticket = labels[selected_label]
    token = st.session_state.auth_session["access_token"]
    try:
        existing = _backend().list_interventions(token, ticket["id"])
    except APIError as exc:
        st.error(str(exc))
        return
    st.caption(f"Agence : {ticket.get('agency') or 'Non renseignée'} · Agence locale : {ticket.get('site') or 'Non renseignée'}")
    if existing and not st.session_state.get("intervention_create_mode"):
        st.markdown("### Historique des interventions")
        for report in existing:
            title = f"{report['intervention_number']} · {report.get('result', '')} · {report.get('review_status', 'En attente de validation')}"
            with st.expander(title, expanded=False):
                st.caption(f"Créée le {report.get('created_at', '—')} · Mise à jour {report.get('updated_at', '—')}")
                for label, value in (("Diagnostic", report.get('diagnosis')), ("Travail réalisé", report.get('actions_performed')), ("Tests", report.get('tests_performed')), ("Résultat", report.get('result')), ("Retour régulateur", report.get('review_feedback'))):
                    if value:
                        st.markdown(f"**{label}**\n\n{html.escape(str(value))}")
        if ticket.get("status") in {"Résolu", "Clôturé"} or any(item.get("review_status") == "Approuvée" and item.get("user_validated_at") for item in existing):
            st.info("Cette intervention est clôturée et ne peut plus être modifiée. Créez un nouveau ticket pour un nouveau problème.")
        else:
            if st.button("Nouvelle intervention", type="primary", key=f"new_intervention_{ticket['id']}"):
                st.session_state.intervention_create_mode = True
                st.rerun()
        return
    with st.form("field_intervention_form", clear_on_submit=True):
        st.caption("Fiche d'intervention maintenance")
        contact_name = st.text_input("Intervenant / contact client")
        client_information = st.text_area("Informations sur le client")
        initial_description = st.text_area("Description de la demande initiale / du dysfonctionnement", value=ticket.get("description", ""))
        diagnosis = st.text_area("Diagnostic initial et détaillé")
        actions = st.text_area("Rapport d'intervention / difficultés rencontrées")
        equipment = st.text_input("Systèmes, ordinateurs ou équipements concernés")
        tests = st.text_area("Tests effectués")
        time_spent = st.text_input("Temps passé")
        materials = st.text_area("Pièces de rechange et consommables")
        follow_up = st.text_area("Suivi recommandé / prochaine action")
        notes = st.text_area("Notes du technicien")
        submitted = st.form_submit_button("Enregistrer le rapport", type="primary", width="stretch")
    if submitted:
        payload = {"agency": ticket.get("agency"), "site": ticket.get("site"), "city": ticket.get("city"), "contact_name": contact_name, "agency_comments": client_information, "diagnosis": f"{initial_description}\n\n{diagnosis}".strip(), "actions_performed": actions, "equipment_involved": equipment, "tests_performed": tests, "materials_used": f"Temps passé: {time_spent}\n{materials}".strip(), "result": "En cours", "follow_up": follow_up, "technician_notes": notes}
        try:
            _backend().create_intervention(token, ticket["id"], payload)
            st.session_state.pop("intervention_create_mode", None)
            st.session_state.flash_message = "Rapport d’intervention enregistré avec succès."
            st.rerun()
        except APIError as exc:
            st.error(str(exc))
    if existing:
        st.markdown("### Rapports existants")
        for report in existing:
            st.write(f"{report['intervention_number']} · {report['result']} · {report.get('updated_at', '')}")


