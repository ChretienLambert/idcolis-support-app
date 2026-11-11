from __future__ import annotations

import html
from datetime import datetime, timezone

import streamlit as st

from i18n import t
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
        return parsed.strftime(t("%d/%m/%Y à %H:%M"))
    except ValueError:
        return str(value)[:16].replace("T", " ")


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

    if st.button(t("← Retour au ticket"), width="stretch"):
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
        st.info(t(
            "Le rapport d'opération n'est disponible qu'une fois le ticket entièrement validé : "
            "intervention du technicien, approbation du régulateur, puis confirmation du demandeur."
        ))
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

    generated_at = datetime.now(timezone.utc).strftime(t("%d/%m/%Y à %H:%M")) + " UTC"

    def field(label: str, value: str) -> str:
        return f'<div><div class="report-field-label">{t(label)}</div><div class="report-field-value">{value}</div></div>'

    summary_fields = "".join([
        field("Sujet", _fmt(ticket.get("subject"))),
        field("Catégorie", _fmt(t(ticket.get("category")))),
        field("Agence", _fmt(ticket.get("agency"))),
        field("Poste / agence locale", _fmt(ticket.get("site"))),
        field("Priorité", _fmt(t(ticket.get("priority")))),
        field("Équipe assignée", _fmt(t(ticket.get("team_name")))),
        field("Ouvert le", _fmt_date(ticket.get("created_at"))),
        field("Résolu le", _fmt_date(ticket.get("resolved_at"))),
    ])
    report_title = t("Rapport d'opération — ID Colis Support")
    report_sub = t("Ticket {id} · Généré le {date}", id=_fmt(ticket["id"]), date=generated_at)
    summary_title = t("Résumé du ticket")
    description_title = t("Description de l'incident")
    description = _fmt(ticket.get("description"))

    st.markdown(
        f"""
        <div class="report-sheet">
          <div class="report-title">{report_title}</div>
          <div class="report-sub">{report_sub}</div>

          <div class="report-section-title">{summary_title}</div>
          <div class="report-grid">{summary_fields}</div>

          <div class="report-section-title">{description_title}</div>
          <div class="report-prose">{description}</div>
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
        ("Résultat", t(latest.get("result"))),
        ("Notes de résolution", latest.get("resolution_notes")),
    )
    detail_rows = "".join(
        f'<div><div class="report-field-label">{t(label)}</div><div class="report-prose">{_fmt(value)}</div></div>'
        for label, value in details
        if value
    )
    detail_title = t("Détail de l'intervention — {number}", number=_fmt(latest.get("intervention_number")))
    st.markdown(
        f"""
        <div class="report-sheet">
          <div class="report-title" style="font-size:1.2rem;">{detail_title}</div>
          <div class="report-grid" style="margin-top:.75rem;">{detail_rows}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    signature_label = t("Signature")

    def signoff(role: str, name: str | None, date_label: str, date_value: str | None) -> str:
        role_label = t(role)
        date_text = t(date_label, date=_fmt_date(date_value))
        return f"""
            <div class="signoff-card">
              <div class="signoff-role">{role_label}</div>
              <div class="signoff-name">{_fmt(name)}</div>
              <div class="signoff-date">{date_text}</div>
              <div class="signoff-line">{signature_label}</div>
            </div>"""

    signoff_cards = "".join([
        signoff("Technicien (exécution)", latest.get("technician_name"), "Intervention du {date}", latest.get("started_at") or latest.get("created_at")),
        signoff("Régulateur (approbation)", latest.get("reviewed_by_name"), "Approuvé le {date}", latest.get("reviewed_at")),
        signoff("Demandeur (confirmation)", ticket.get("requester_name"), "Confirmé le {date}", latest.get("user_validated_at")),
    ])
    signoff_title = t("Validation à trois parties")
    signoff_sub = t("Cette opération a été réalisée, contrôlée et confirmée par les personnes suivantes.")
    st.markdown(
        f"""
        <div class="report-sheet">
          <div class="report-title" style="font-size:1.2rem;">{signoff_title}</div>
          <div class="report-sub">{signoff_sub}</div>
          <div class="signoff-grid">{signoff_cards}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
