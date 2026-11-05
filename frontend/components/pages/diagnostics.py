from __future__ import annotations

import streamlit as st

from services.api import APIError
from views.layout import metric_card, page_header

from components.common import _backend


def render_diagnostics() -> None:
    """Display backend health, AI suggestion accuracy, and recurring issues."""
    page_header("Diagnostics système", "État du backend et des services ID Colis")
    api = _backend()
    try:
        health = api._json(api._request("GET", "/health"))
        st.success(f"Backend disponible - environnement: {health.get('env', 'inconnu')}")
    except Exception as exc:
        st.error(f"Backend indisponible: {exc}")
        return

    token = st.session_state.auth_session["access_token"]

    st.markdown('<div class="section-title">Agences possiblement hors ligne</div>', unsafe_allow_html=True)
    st.caption("Tickets réseau/connectivité ouverts depuis plus de 24h : l'application ID Colis fonctionne hors ligne, donc ce n'est pas juste un inconfort — l'agence risque de ne plus synchroniser ni sauvegarder son travail. Un appel direct vaut mieux qu'attendre que le ticket remonte seul.")
    try:
        risk = api.connectivity_risk(token)
    except APIError as exc:
        st.warning(str(exc))
        risk = []

    if not risk:
        st.success("Aucune agence hors ligne depuis plus de 24h.")
    else:
        for item in risk:
            with st.container(border=True):
                days = item["hours_open"] / 24
                duration = f"{days:.1f} jour(s)" if days >= 1 else f"{item['hours_open']:.0f}h"
                st.markdown(
                    f'<div class="idc-ticket-card-title">{item["ticket_id"]} · {item["subject"]}</div>'
                    f'<div class="idc-ticket-card-meta">{item.get("site") or item.get("agency") or "Agence inconnue"} · ouvert depuis {duration} · statut : {item["status"]}</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Fiabilité des suggestions IA</div>', unsafe_allow_html=True)
    try:
        performance = api.ai_performance(token)
    except APIError as exc:
        st.warning(str(exc))
        performance = None

    if performance:
        if performance["total_decisions"] == 0:
            st.info("Aucune décision enregistrée pour le moment.")
        else:
            cols = st.columns(3)
            with cols[0]:
                st.markdown(metric_card("Décisions enregistrées", str(performance["total_decisions"]), "Depuis le début", "#2F80ED"), unsafe_allow_html=True)
            with cols[1]:
                st.markdown(metric_card("Suggestions acceptées", str(performance["accepted"]), "Validées telles quelles", "#4B8E37"), unsafe_allow_html=True)
            with cols[2]:
                st.markdown(metric_card("Taux d'acceptation", f"{performance['acceptance_rate']:.0f}%", f"{performance['corrected']} correction(s)", "#D9A441"), unsafe_allow_html=True)
            if performance["recent_corrections"]:
                with st.expander("Dernières corrections apportées par les agents"):
                    for item in performance["recent_corrections"]:
                        st.markdown(
                            f'<div class="idc-list-row"><span>{item["ticket_id"]}</span>'
                            f'<span class="idc-list-value">{item.get("ai_suggested_category") or "?"} → {item.get("agent_modified_category") or "?"}</span></div>',
                            unsafe_allow_html=True,
                        )

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Problèmes récurrents</div>', unsafe_allow_html=True)
    st.caption("Agence / poste / catégorie avec au moins 3 tickets sur les 30 derniers jours — signe d'un problème sous-jacent à traiter plutôt que de fermer ticket après ticket.")
    try:
        recurring = api.recurring_issues(token)
    except APIError as exc:
        st.warning(str(exc))
        recurring = []

    if not recurring:
        st.info("Aucun problème récurrent détecté sur la période.")
    else:
        for issue in recurring:
            with st.container(border=True):
                st.markdown(
                    f'<div class="idc-ticket-card-title">{issue["category"]}</div>'
                    f'<div class="idc-ticket-card-meta">{issue.get("site") or issue.get("agency") or "Agence inconnue"} · {issue["count"]} tickets récents · dernier le {str(issue["latest_created_at"])[:10]}</div>',
                    unsafe_allow_html=True,
                )
