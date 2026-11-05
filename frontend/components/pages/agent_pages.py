from __future__ import annotations

import streamlit as st

from constants import BLUE, GREEN, YELLOW
from services.session import set_navigation
from views.layout import metric_card, page_header, ticket_card

from components.common import _apply_time_filter, _load_tickets

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
        if st.button("Actualiser", width="stretch"):
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
        team_rows = "".join(
            f'<div class="idc-list-row"><span>{key}</span><span class="idc-list-value">{value}</span></div>'
            for key, value in sorted(group.items(), key=lambda item: item[1], reverse=True)
        )
        st.markdown(f'<div class="idc-list-card">{team_rows}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="panel"><div class="section-title">Statut</div>', unsafe_allow_html=True)
        status_group: dict[str, int] = {}
        for ticket in tickets:
            status_group[ticket["status"]] = status_group.get(ticket["status"], 0) + 1
        status_rows = "".join(
            f'<div class="idc-list-row"><span>{key}</span><span class="idc-list-value">{value}</span></div>'
            for key, value in sorted(status_group.items(), key=lambda item: item[1], reverse=True)
        )
        st.markdown(f'<div class="idc-list-card">{status_rows}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Tickets récents</div>', unsafe_allow_html=True)
    for ticket in tickets[:8]:
        meta = f"{ticket['category']} · {ticket['team_name']} · {ticket['assigned_agent_name'] or 'Non attribué'}"
        if ticket_card(ticket, "agent_recent", meta):
            st.session_state.selected_ticket_id = ticket["id"]
            set_navigation("ticket_detail", ticket["id"])
            st.rerun()


def render_agent_queue() -> None:
    regulator_view = st.session_state.get("active_user", {}).get("role") == "Régulateur_Agence"
    validation_view = regulator_view and st.session_state.get("page") == "regulator_queue"
    c1, c2 = st.columns([0.85, 0.15])
    with c1:
        page_header("Tickets à valider" if validation_view else "Tickets de l’agence" if regulator_view else "Tous les tickets", "Interventions IT en attente de votre décision" if validation_view else "Vue complète de tous les tickets de votre agence" if regulator_view else "File opérationnelle")
    with c2:
        if st.button("Retour", key="back_to_dash", width="stretch"):
            set_navigation("agent_dashboard", None)
            st.rerun()

    tickets = _load_tickets()

    # Compact Filters Row
    st.markdown("---")
    f1, f2, f3, f4, f5 = st.columns([0.28, 0.17, 0.17, 0.17, 0.21], vertical_alignment="bottom")
    with f1:
        st.caption("Recherche")
        search = st.text_input("Recherche", key="ticket_filter_search", placeholder="Sujet, ID...", label_visibility="collapsed")
    with f2:
        st.caption("Statut")
        status_filter = st.selectbox("Statut", ["Tous", "Créé", "Assigné", "En attente", "En cours", "En attente de validation", "À corriger", "Résolu", "Clôturé"], key="ticket_filter_status", label_visibility="collapsed", disabled=regulator_view)
    with f3:
        st.caption("Priorité")
        priority_filter = st.selectbox("Priorité", ["Toutes", "Critique", "Élevée", "Moyenne", "Faible"], key="ticket_filter_priority", label_visibility="collapsed")
    with f4:
        st.caption("Catégorie")
        category_filter = st.selectbox("Catégorie", ["Toutes"] + sorted({ticket["category"] for ticket in tickets}), key="ticket_filter_category", label_visibility="collapsed")
    with f5:
        st.caption("Période")
        filtered_tickets_temp = _apply_time_filter(tickets, "agent_queue")

    st.markdown("<br>", unsafe_allow_html=True)
    filtered = filtered_tickets_temp
    if validation_view:
        filtered = [ticket for ticket in filtered if ticket["status"] == "En attente de validation"]
    if search:
        query = search.lower()
        filtered = [ticket for ticket in filtered if query in ticket["id"].lower() or query in ticket["subject"].lower() or query in ticket["team_name"].lower()]
    if status_filter != "Tous" and not regulator_view:
        filtered = [ticket for ticket in filtered if ticket["status"] == status_filter]
    if priority_filter != "Toutes":
        filtered = [ticket for ticket in filtered if ticket["priority"] == priority_filter]
    if category_filter != "Toutes":
        filtered = [ticket for ticket in filtered if ticket["category"] == category_filter]

    if not filtered:
        st.info("Aucun ticket ne correspond à ces filtres.")
    for ticket in filtered:
        meta = f"{ticket['category']} · {ticket['team_name']} · {ticket['assigned_agent_name'] or 'Non attribué'}"
        if ticket_card(ticket, "queue", meta):
            st.session_state.selected_ticket_id = ticket["id"]
            set_navigation("ticket_detail", ticket["id"])
            st.rerun()


