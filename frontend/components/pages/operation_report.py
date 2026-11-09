from __future__ import annotations

import html
from datetime import datetime, timezone

import streamlit as st

from services.api import APIError
from services.session import set_navigation

from components.common import _backend, _role_label


def _fmt(value: str | None) -> str:
    return html.escape(value) if value else "—"


def _fmt_date(value: str | None) -> str:
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%d/%m/%Y à %H:%M")
    except ValueError:
        return str(value)[:16].replace("T", " à ")


def render_operation_report() -> None:
    ticket_id = st.session_state.selected_ticket_id or st.session_state.nav_ticket_id
    if not ticket_id:
        set_navigation("user_home" if _role_label() == "Utilisateur" else "agent_dashboard", None)
        st.rerun()

    st.session_state.selected_ticket_id = ticket_id
    try:
        ticket = _backend().get_ticket(st.session_state.auth_session["access_token"], ticket_id)
        interventions = _backend().list_interventions(st.session_state.auth_session["access_token"], ticket_id)
    except APIError as exc:
        st.error(str(exc))
        return

    if st.button("← Retour au ticket", width="stretch"):
        set_navigation("ticket_detail", ticket_id)
        st.rerun()

    latest = interventions[-1] if interventions else None
    fully_validated = (
        ticket["status"] in {"Résolu", "Clôturé"}
        and latest is not None
        and latest.get("review_status") == "Approuvée"
        and latest.get("user_validated_at")
    )
    if not fully_validated:
        st.info(
            "Le rapport d'opération n'est disponible qu'une fois le ticket entièrement validé : "
            "intervention du technicien, approbation du régulateur, puis confirmation du demandeur."
        )
        return

    # Scoped to this page: makes the document legible with the browser's own
    # Ctrl+P / print-to-PDF, without adding an in-app print button yet.
    st.markdown(
        """
        <style>
        @media print {
          [data-testid="stSidebar"], [data-testid="stHeader"], .stButton { display: none !important; }
          .report-sheet { box-shadow: none !important; }
        }
        .report-sheet {
          background: var(--idc-card, #fff);
          border: 1px solid var(--idc-border, #DCE5EC);
          border-radius: 12px;
          padding: 2rem 2.25rem;
          margin-top: .5rem;
        }
        .report-title { font-size: 1.6rem; font-weight: 900; color: var(--idc-navy, #102A43); }
        .report-sub { color: var(--idc-muted, #627D98); margin-top: .15rem; }
        .report-section-title {
          font-weight: 800; color: var(--idc-navy, #102A43); margin: 1.4rem 0 .6rem;
          border-bottom: 2px solid var(--idc-border, #DCE5EC); padding-bottom: .3rem;
        }
        .report-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem 1.5rem; }
        .report-field-label { font-size: .78rem; text-transform: uppercase; letter-spacing: .03em; color: var(--idc-muted, #627D98); }
        .report-field-value { font-weight: 600; color: var(--idc-navy, #102A43); }
        .report-prose { white-space: pre-wrap; color: var(--idc-navy, #102A43); line-height: 1.5; }
        .signoff-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.25rem; margin-top: .5rem; }
        .signoff-card { border: 1px solid var(--idc-border, #DCE5EC); border-radius: 10px; padding: 1rem; }
        .signoff-role { font-size: .78rem; text-transform: uppercase; letter-spacing: .03em; color: var(--idc-muted, #627D98); }
        .signoff-name { font-weight: 800; color: var(--idc-navy, #102A43); margin: .25rem 0; }
        .signoff-date { color: var(--idc-muted, #627D98); font-size: .85rem; }
        .signoff-line { margin-top: 2.2rem; border-top: 1px solid var(--idc-navy, #102A43); padding-top: .25rem; font-size: .78rem; color: var(--idc-muted, #627D98); text-align: center; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y à %H:%M UTC")

    st.markdown(
        f"""
        <div class="report-sheet">
          <div class="report-title">Rapport d'opération — ID Colis Support</div>
          <div class="report-sub">Ticket {_fmt(ticket['id'])} · Généré le {generated_at}</div>

          <div class="report-section-title">Résumé du ticket</div>
          <div class="report-grid">
            <div><div class="report-field-label">Sujet</div><div class="report-field-value">{_fmt(ticket.get('subject'))}</div></div>
            <div><div class="report-field-label">Catégorie</div><div class="report-field-value">{_fmt(ticket.get('category'))}</div></div>
            <div><div class="report-field-label">Agence</div><div class="report-field-value">{_fmt(ticket.get('agency'))}</div></div>
            <div><div class="report-field-label">Poste / agence locale</div><div class="report-field-value">{_fmt(ticket.get('site'))}</div></div>
            <div><div class="report-field-label">Priorité</div><div class="report-field-value">{_fmt(ticket.get('priority'))}</div></div>
            <div><div class="report-field-label">Équipe assignée</div><div class="report-field-value">{_fmt(ticket.get('team_name'))}</div></div>
            <div><div class="report-field-label">Ouvert le</div><div class="report-field-value">{_fmt_date(ticket.get('created_at'))}</div></div>
            <div><div class="report-field-label">Résolu le</div><div class="report-field-value">{_fmt_date(ticket.get('resolved_at'))}</div></div>
          </div>

          <div class="report-section-title">Description de l'incident</div>
          <div class="report-prose">{_fmt(ticket.get('description'))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    details = (
        ("Diagnostic", latest.get("diagnosis")),
        ("Travail réalisé", latest.get("actions_performed")),
        ("Équipement concerné", latest.get("equipment_involved")),
        ("Pièces / temps passé", latest.get("materials_used")),
        ("Tests effectués", latest.get("tests_performed")),
        ("Résultat", latest.get("result")),
        ("Notes de résolution", latest.get("resolution_notes")),
    )
    detail_rows = "".join(
        f'<div><div class="report-field-label">{label}</div><div class="report-prose">{_fmt(value)}</div></div>'
        for label, value in details
        if value
    )
    st.markdown(
        f"""
        <div class="report-sheet">
          <div class="report-title" style="font-size:1.2rem;">Détail de l'intervention — {_fmt(latest.get('intervention_number'))}</div>
          <div class="report-grid" style="margin-top:.75rem;">{detail_rows}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="report-sheet">
          <div class="report-title" style="font-size:1.2rem;">Validation à trois parties</div>
          <div class="report-sub">Cette opération a été réalisée, contrôlée et confirmée par les personnes suivantes.</div>
          <div class="signoff-grid">
            <div class="signoff-card">
              <div class="signoff-role">Technicien (exécution)</div>
              <div class="signoff-name">{_fmt(latest.get('technician_name'))}</div>
              <div class="signoff-date">Intervention du {_fmt_date(latest.get('started_at') or latest.get('created_at'))}</div>
              <div class="signoff-line">Signature</div>
            </div>
            <div class="signoff-card">
              <div class="signoff-role">Régulateur (approbation)</div>
              <div class="signoff-name">{_fmt(latest.get('reviewed_by_name'))}</div>
              <div class="signoff-date">Approuvé le {_fmt_date(latest.get('reviewed_at'))}</div>
              <div class="signoff-line">Signature</div>
            </div>
            <div class="signoff-card">
              <div class="signoff-role">Demandeur (confirmation)</div>
              <div class="signoff-name">{_fmt(ticket.get('requester_name'))}</div>
              <div class="signoff-date">Confirmé le {_fmt_date(latest.get('user_validated_at'))}</div>
              <div class="signoff-line">Signature</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
