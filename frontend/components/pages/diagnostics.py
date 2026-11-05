from __future__ import annotations

import streamlit as st

from views.layout import page_header

from components.common import _backend

def render_diagnostics() -> None:
    """Display basic backend diagnostics and local application status."""
    page_header("Diagnostics système", "État du backend et des services ID Colis")
    api = _backend()
    try:
        health = api._json(api._request("GET", "/api/health"))
        st.success(f"Backend disponible - environnement: {health.get('env', 'inconnu')}")
    except Exception as exc:
        st.error(f"Backend indisponible: {exc}")


