from __future__ import annotations

import html
from datetime import date

import streamlit as st

from i18n import t
from services.api import APIError
from services.session import set_navigation
from views.layout import page_header

from components.common import _backend, _group_identical_reports, _load_tickets


def _draft_report_text(ticket: dict) -> tuple[str, str]:
    """Build a starting diagnosis/actions draft from the ticket itself, so the
    technician edits a pre-filled report instead of starting from a blank
    page. This is a template, not generated prose — it only reuses what the
    ticket already says."""
    category = t(ticket.get("category")) or t("le problème signalé")
    diagnosis = (
        t("Incident de type « {category} » signalé le {date}.", category=category, date=str(ticket.get('created_at', ''))[:10]) + "\n"
        + t("Description initiale du demandeur : {description}", description=ticket.get('description', '').strip())
    )
    actions = t("Diagnostic sur place à compléter : vérification du matériel, des connexions et reproduction du problème avec l'utilisateur.")
    return diagnosis, actions

def render_interventions() -> None:
    """Display interventions attached to tickets; creation starts from a ticket."""
    page_header(t("Interventions"), t("Rapports liés aux tickets ID Colis"))
    if st.session_state.get("flash_message"):
        st.success(st.session_state.flash_message)
        st.session_state.flash_message = ""
    tickets = _load_tickets()
    if not tickets:
        st.info(t("Aucun ticket disponible pour créer une intervention."))
        return
    labels = {f"{item['id']} · {item['subject']}": item for item in tickets}
    selected_ticket_id = st.session_state.get("intervention_ticket_id")
    if not selected_ticket_id:
        st.caption(t("Les interventions sont toujours rattachées à un ticket."))
        for label, linked_ticket in labels.items():
            existing = _backend().list_interventions(st.session_state.auth_session["access_token"], linked_ticket["id"])
            with st.container(border=True):
                row = st.columns([0.62, 0.20, 0.18], vertical_alignment="center")
                with row[0]:
                    st.markdown(f'<div class="idc-ticket-card-title">{label}</div>', unsafe_allow_html=True)
                    if existing:
                        latest = existing[-1]
                        st.markdown(f'<div class="idc-ticket-card-meta">{len(existing)} intervention(s) · {t(latest.get("review_status", "En attente de validation"))}</div>', unsafe_allow_html=True)
                        if latest.get('review_feedback'):
                            st.caption(t("Retour régulateur : {feedback}", feedback=latest['review_feedback']))
                    else:
                        st.markdown(f'<div class="idc-ticket-card-meta">{t("Aucune intervention")}</div>', unsafe_allow_html=True)
                with row[1]:
                    if st.button(t("Voir le ticket"), key=f"ticket_link_interventions_{linked_ticket['id']}", width="stretch"):
                        set_navigation("ticket_detail", linked_ticket["id"])
                        st.rerun()
                with row[2]:
                    if st.button(t("Ouvrir →"), key=f"open_interventions_{linked_ticket['id']}", width="stretch"):
                        st.session_state.intervention_ticket_id = linked_ticket["id"]
                        st.session_state.intervention_create_mode = False
                        st.rerun()
        return
    selected_label = next((label for label, item in labels.items() if item["id"] == selected_ticket_id), None)
    if not selected_label:
        st.session_state.pop("intervention_ticket_id", None)
        st.rerun()
    if st.button(t("Retour à la liste des interventions"), key="back_to_intervention_list"):
        st.session_state.pop("intervention_ticket_id", None)
        st.session_state.pop("intervention_create_mode", None)
        st.rerun()
    token = st.session_state.auth_session["access_token"]
    try:
        # The ticket list only carries summaries (no description), so fetch
        # the full record here — the draft-assist button and the initial
        # description field below both need the actual incident text.
        ticket = _backend().get_ticket(token, labels[selected_label]["id"])
        existing = _backend().list_interventions(token, ticket["id"])
    except APIError as exc:
        st.error(str(exc))
        return
    st.caption(t("Agence : {agency} · Agence locale : {site}", agency=ticket.get('agency') or t('Non renseignée'), site=ticket.get('site') or t('Non renseignée')))
    if existing and not st.session_state.get("intervention_create_mode"):
        st.markdown(f"### {t('Historique des interventions')}")
        for group in _group_identical_reports(existing):
            report = group["report"]
            duplicate_tag = t(" · {count} rapports identiques", count=group["count"]) if group["count"] > 1 else ""
            title = f"{report['intervention_number']} · {t(report.get('result', ''))} · {t(report.get('review_status', 'En attente de validation'))}{duplicate_tag}"
            with st.expander(title, expanded=False):
                intervention_date = str(report.get("started_at") or report.get("created_at") or "—")[:10]
                st.caption(t("Date d'intervention : {date} · Enregistrée le {created} · Mise à jour {updated}", date=intervention_date, created=report.get('created_at', '—'), updated=report.get('updated_at', '—')))
                if group["count"] > 1:
                    st.caption(t("Soumis {count} fois à l'identique, entre {first} et {last}.", count=group['count'], first=str(group['first_created_at'])[:10], last=str(group['last_created_at'])[:10]))
                for label, value in (("Diagnostic", report.get('diagnosis')), ("Travail réalisé", report.get('actions_performed')), ("Tests", report.get('tests_performed')), ("Résultat", report.get('result')), ("Retour régulateur", report.get('review_feedback'))):
                    if value:
                        shown = t(value) if label == "Résultat" else value
                        st.markdown(f"**{t(label)}**\n\n{html.escape(str(shown))}")
        if ticket.get("status") in {"Résolu", "Clôturé"} or any(item.get("review_status") == "Approuvée" and item.get("user_validated_at") for item in existing):
            st.info(t("Cette intervention est clôturée et ne peut plus être modifiée. Créez un nouveau ticket pour un nouveau problème."))
        else:
            if st.button(t("Nouvelle intervention"), type="primary", key=f"new_intervention_{ticket['id']}"):
                st.session_state.intervention_create_mode = True
                st.rerun()
        return
    draft_diagnosis_key = f"intervention_draft_diagnosis_{ticket['id']}"
    draft_actions_key = f"intervention_draft_actions_{ticket['id']}"
    if st.button(t("Générer un brouillon de rapport à partir du ticket"), key=f"draft_report_{ticket['id']}"):
        st.session_state[draft_diagnosis_key], st.session_state[draft_actions_key] = _draft_report_text(ticket)
        st.rerun()

    with st.form("field_intervention_form", clear_on_submit=False):
        st.caption(t("Fiche d'intervention maintenance"))
        intervention_date = st.date_input(t("Date de l'intervention"), value=date.today())
        contact_name = st.text_input(t("Intervenant / contact client"))
        client_information = st.text_area(t("Informations sur le client"))
        initial_description = st.text_area(t("Description de la demande initiale / du dysfonctionnement"), value=ticket.get("description", ""))
        diagnosis = st.text_area(t("Diagnostic initial et détaillé"), value=st.session_state.get(draft_diagnosis_key, ""))
        actions = st.text_area(t("Rapport d'intervention / difficultés rencontrées *(obligatoire : décrivez ce qui a été fait)"), value=st.session_state.get(draft_actions_key, ""))
        equipment = st.text_input(t("Systèmes, ordinateurs ou équipements concernés"))
        tests = st.text_area(t("Tests effectués"))
        time_spent = st.text_input(t("Temps passé"))
        materials = st.text_area(t("Pièces de rechange et consommables"))
        follow_up = st.text_area(t("Suivi recommandé / prochaine action"))
        notes = st.text_area(t("Notes du technicien"))
        submitted = st.form_submit_button(t("Enregistrer le rapport"), type="primary", width="stretch")
    if submitted:
        if not actions.strip() or len(actions.strip()) < 3:
            # Client details and diagnosis can be thin or revised later; the
            # record of what was actually done cannot be skipped.
            st.error(t("Le rapport d'intervention (ce qui a été fait) est obligatoire avant d'enregistrer."))
        else:
            payload = {"agency": ticket.get("agency"), "site": ticket.get("site"), "city": ticket.get("city"), "started_at": intervention_date.isoformat(), "contact_name": contact_name, "agency_comments": client_information, "diagnosis": f"{initial_description}\n\n{diagnosis}".strip(), "actions_performed": actions, "equipment_involved": equipment, "tests_performed": tests, "materials_used": f"{t('Temps passé')}: {time_spent}\n{materials}".strip(), "result": "En cours", "follow_up": follow_up, "technician_notes": notes}
            try:
                _backend().create_intervention(token, ticket["id"], payload)
                st.session_state.pop(draft_diagnosis_key, None)
                st.session_state.pop(draft_actions_key, None)
                st.session_state.pop("intervention_create_mode", None)
                st.session_state.flash_message = t("Rapport d’intervention enregistré avec succès.")
                st.rerun()
            except APIError as exc:
                st.error(str(exc))
    if existing:
        st.markdown(f"### {t('Rapports existants')}")
        for report in existing:
            st.write(f"{report['intervention_number']} · {t(report['result'])} · {report.get('updated_at', '')}")
