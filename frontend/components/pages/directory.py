from __future__ import annotations

import streamlit as st

from i18n import t
from services.api import APIError
from services.session import set_navigation
from views.layout import page_header, ticket_card

from components.common import _backend, _load_tickets

def render_directory() -> None:
    """Display agency locations, assigned posts, and the selected user's tickets."""
    agency = st.session_state.get("selected_station") or t("Agence sélectionnée")
    page_header(t("Agences et postes"), t("Annuaire opérationnel de {agency}.", agency=agency), f'<span class="badge station-chip">{agency}</span>')
    token = st.session_state.auth_session["access_token"]
    try:
        stations = _backend().directory(token)
    except APIError as exc:
        st.error(str(exc))
        return
    if not stations:
        st.info(t("Aucune station n'est encore enregistrée pour cette agence."))
        return
    st.caption(t("{count} agence(s) dans la file {agency}. Chaque agence possède deux postes et seuls ses utilisateurs sont affichés.", count=len(stations), agency=agency))
    for station in stations:
        with st.container(border=True):
            head = st.columns([0.55, 0.45])
            with head[0]:
                st.markdown(f"### {station['name']}")
                st.write(f"{station['city']} · {station['address']}")
            with head[1]:
                if station.get("phone"):
                    st.markdown(f"**{t('Contact station')}**  \n{station['phone']}")
            post_cols = st.columns(2)
            for col, post in zip(post_cols, station.get("posts", [])):
                with col:
                    assigned = post.get("assigned_user") or t("Poste à affecter")
                    st.markdown(f"**{t(post['name'])}**")
                    st.caption(assigned)
                    if post.get("user_id") and st.button(t("Voir les tickets"), key=f"directory_user_{post['user_id']}", width="stretch"):
                        st.session_state.directory_user_id = post["user_id"]
                        st.session_state.directory_user_name = assigned
                        st.session_state.directory_user_email = post.get("email")
                        set_navigation("directory_user_tickets")
                        st.rerun()


def render_directory_user_tickets() -> None:
    """Show a dedicated support page for one agency post and its ticket history."""
    user_name = st.session_state.get("directory_user_name") or t("Utilisateur")
    page_header(t("Tickets de {name}", name=user_name), t("Historique et suivi du poste sélectionné"))
    if st.button(t("← Retour aux agences"), key="back_directory"):
        set_navigation("directory")
        st.rerun()
    selected_user_id = st.session_state.get("directory_user_id")
    tickets = [ticket for ticket in _load_tickets() if ticket.get("requester_user_id") == selected_user_id]
    if not tickets:
        st.info(t("Aucun ticket enregistré pour ce poste."))
        return
    for ticket in tickets:
        meta = t(ticket.get("priority")) or t("À qualifier")
        if ticket_card(ticket, "directory_user_ticket", meta):
            st.session_state.selected_ticket_id = ticket["id"]
            set_navigation("ticket_detail", ticket["id"])
            st.rerun()


def render_directory_ticket_tail() -> None:
    """Compatibility placeholder for older navigation state."""
    return
