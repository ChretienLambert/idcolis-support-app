from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Add parent directory to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from constants import NAVY


def inject_styles() -> None:
    css = """
    <style>
    :root { --idc-navy:#16324F; --idc-muted:#5F7184; --idc-border:#DCE5EC; --idc-green:#2F7D4A; --idc-blue:#246BCE; }
    html, body, [class*="css"] { font-family: "Segoe UI", Arial, sans-serif; }
    [data-testid="stSidebar"] {
        background-color: #F7FAFC !important;
        border-right: 1px solid var(--idc-border);
    }
    [data-testid="stSidebar"] .stButton > button {
        border-radius: 14px !important;
        border: 1px solid rgba(16,42,67,0.08) !important;
        text-align: left !important;
        padding: 0.75rem 0.9rem !important;
        margin-bottom: 0.45rem !important;
        background: white !important;
        color: var(--idc-navy) !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: var(--idc-green) !important;
        color: white !important;
        border-color: transparent !important;
    }
    .stButton > button {
        background-color: var(--idc-green) !important;
        color: white !important;
    }
    .hero-card, .panel, .field-card, .detail-sheet, .nav-shell {
        background: white;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(16,42,67,0.08);
        border: 1px solid rgba(16,42,67,0.08);
        padding: 1.1rem 1.2rem;
        margin-bottom: 1rem;
    }
    .panel {
        margin-top: 0.35rem;
    }
    .hero-big { font-size: 2rem; font-weight: 800; color: #102A43; margin: 0; }
    .hero-muted { color: #627D98; margin-top: .35rem; line-height: 1.5; }
    .section-title { font-weight: 800; color: #102A43; font-size: 1.05rem; margin-bottom: .5rem; }
    .metric-card { border-radius: 14px; padding: 1rem; background: #fff; border:1px solid var(--idc-border); }
    .ticket-list-row {
        display: grid;
        gap: 0.65rem;
        padding: 0.65rem 0;
        border-bottom: 1px solid rgba(16,42,67,0.07);
        align-items: center;
    }
    .badge { display:inline-block; padding:.28rem .65rem; border-radius:999px; font-size:.82rem; font-weight:700; }
    .badge-open { background:#E3F2FD; color:#1976D2; }
    .badge-progress { background:#E8F5E9; color:#4B8E37; }
    .badge-wait { background:#FFF3E0; color:#F57C00; }
    .badge-closed { background:#FFEBEE; color:#D32F2F; }
    .soc-nav button, .soc-nav a {
        width: 100%;
        border-radius: 14px !important;
        border: 1px solid rgba(16,42,67,0.08) !important;
        text-align: left !important;
    }
    .stApp { background: #F7FAFC; }
    [data-testid="stHeader"] { background: #F7FAFC; }
    .station-chip { display:inline-block; padding:.35rem .7rem; border-radius:999px; background:#E6F4EA; color:#236B39; font-weight:700; }
    .ai-suggestion-box {
        background: #F1F8F3;
        border: 2px solid #4B8E37;
        border-radius: 16px;
        padding: 1.2rem 1.4rem;
        margin: 1rem 0;
    }
    .ai-suggestion-title {
        font-weight: 800;
        color: #4B8E37;
        font-size: 1.1rem;
        margin-bottom: 0.8rem;
    }
    .ai-suggestion-item {
        background: white;
        border-radius: 12px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
        border: 1px solid rgba(75, 142, 55, 0.2);
    }
    .ai-suggestion-label {
        font-weight: 700;
        color: #102A43;
        font-size: 0.9rem;
    }
    .ai-suggestion-value {
        color: #4B8E37;
        font-weight: 600;
        font-size: 1rem;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", right_badge: str = "") -> None:
    left, right = st.columns([0.82, 0.18])
    with left:
        st.markdown(f"## {title}")
        if subtitle:
            st.caption(subtitle)
    with right:
        if right_badge:
            st.markdown(right_badge, unsafe_allow_html=True)


def metric_card(title: str, value: str, subtitle: str, accent: str) -> str:
    return f"""
    <div class="metric-card">
      <div style="font-weight:800;color:#102A43;margin-bottom:.2rem;">{title}</div>
      <div style="font-size:2rem;font-weight:900;color:{accent};line-height:1;">{value}</div>
      <div style="color:#627D98;margin-top:.35rem;">{subtitle}</div>
    </div>
    """


def status_badge(status: str) -> str:
    mapping = {
        "En attente": "badge-wait",
        "En cours": "badge-progress",
        "Résolu": "badge-closed",
        "Clôturé": "badge-closed",
    }
    css = mapping.get(status, "badge-wait")
    return f'<span class="badge {css}">{status}</span>'


