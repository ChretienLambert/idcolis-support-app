from __future__ import annotations

import streamlit as st

from i18n import t
from services.api import APIError
from views.layout import metric_card, page_header

from components.common import _backend


def render_diagnostics() -> None:
    """Display backend health, AI suggestion accuracy, and recurring issues."""
    page_header(t("Diagnostics système"), t("État du backend et des services ID Colis"))
    api = _backend()
    try:
        health = api._json(api._request("GET", "/health"))
        st.success(t("Backend disponible - environnement: {env}", env=health.get('env') or t('inconnu')))
    except Exception as exc:
        st.error(t("Backend indisponible: {error}", error=exc))
        return

    token = st.session_state.auth_session["access_token"]

    st.markdown(f'<div class="section-title">{t("Agences possiblement hors ligne")}</div>', unsafe_allow_html=True)
    st.caption(t("Tickets réseau/connectivité ouverts depuis plus de 24h : l'application ID Colis fonctionne hors ligne, donc ce n'est pas juste un inconfort — l'agence risque de ne plus synchroniser ni sauvegarder son travail. Un appel direct vaut mieux qu'attendre que le ticket remonte seul."))
    try:
        risk = api.connectivity_risk(token)
    except APIError as exc:
        st.warning(str(exc))
        risk = []

    if not risk:
        st.success(t("Aucune agence hors ligne depuis plus de 24h."))
    else:
        for item in risk:
            with st.container(border=True):
                days = item["hours_open"] / 24
                duration = t("{days} jour(s)", days=f"{days:.1f}") if days >= 1 else f"{item['hours_open']:.0f}h"
                location = item.get("site") or item.get("agency") or t("Agence inconnue")
                meta = t("{location} · ouvert depuis {duration} · statut : {status}", location=location, duration=duration, status=t(item["status"]))
                st.markdown(
                    f'<div class="idc-ticket-card-title">{item["ticket_id"]} · {item["subject"]}</div>'
                    f'<div class="idc-ticket-card-meta">{meta}</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{t("Fiabilité des suggestions IA")}</div>', unsafe_allow_html=True)
    try:
        performance = api.ai_performance(token)
    except APIError as exc:
        st.warning(str(exc))
        performance = None

    if performance:
        if performance["total_decisions"] == 0:
            st.info(t("Aucune décision enregistrée pour le moment."))
        else:
            cols = st.columns(3)
            with cols[0]:
                st.markdown(metric_card(t("Décisions enregistrées"), str(performance["total_decisions"]), t("Depuis le début"), "#2F80ED"), unsafe_allow_html=True)
            with cols[1]:
                st.markdown(metric_card(t("Suggestions acceptées"), str(performance["accepted"]), t("Validées telles quelles"), "#4B8E37"), unsafe_allow_html=True)
            with cols[2]:
                st.markdown(metric_card(t("Taux d'acceptation"), f"{performance['acceptance_rate']:.0f}%", t("{count} correction(s)", count=performance['corrected']), "#D9A441"), unsafe_allow_html=True)
            if performance["recent_corrections"]:
                with st.expander(t("Dernières corrections apportées par les agents")):
                    for item in performance["recent_corrections"]:
                        st.markdown(
                            f'<div class="idc-list-row"><span>{item["ticket_id"]}</span>'
                            f'<span class="idc-list-value">{t(item.get("ai_suggested_category")) or "?"} → {t(item.get("agent_modified_category")) or "?"}</span></div>',
                            unsafe_allow_html=True,
                        )

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{t("Problèmes récurrents")}</div>', unsafe_allow_html=True)
    st.caption(t("Agence / poste / catégorie avec au moins 3 tickets sur les 30 derniers jours — signe d'un problème sous-jacent à traiter plutôt que de fermer ticket après ticket."))
    try:
        recurring = api.recurring_issues(token)
    except APIError as exc:
        st.warning(str(exc))
        recurring = []

    if not recurring:
        st.info(t("Aucun problème récurrent détecté sur la période."))
    else:
        for issue in recurring:
            with st.container(border=True):
                location = issue.get("site") or issue.get("agency") or t("Agence inconnue")
                meta = t("{location} · {count} tickets récents · dernier le {date}", location=location, count=issue["count"], date=str(issue["latest_created_at"])[:10])
                st.markdown(
                    f'<div class="idc-ticket-card-title">{t(issue["category"])}</div>'
                    f'<div class="idc-ticket-card-meta">{meta}</div>',
                    unsafe_allow_html=True,
                )
