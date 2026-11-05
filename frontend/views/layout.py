from __future__ import annotations

import base64
import sys
from pathlib import Path

import streamlit as st

# Add parent directory to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from constants import NAVY


def inject_styles() -> None:
    dark_mode = bool(st.session_state.get("dark_mode", False))
    page_bg = "#101923" if dark_mode else "#F7FAFC"
    card_bg = "#172431" if dark_mode else "#FFFFFF"
    text_color = "#F3F7FA" if dark_mode else "#102A43"
    muted_color = "#B4C3D0" if dark_mode else "#627D98"
    border_color = "#304354" if dark_mode else "#DCE5EC"
    logo_name = "tresor-voyages.jpg" if str(st.session_state.get("selected_station", "")).startswith("Trésor") else "global-voyages.png"
    logo_path = Path(__file__).resolve().parents[1] / "assets" / "logos" / logo_name
    logo_uri = ""
    if logo_path.exists():
        mime = "image/png" if logo_path.suffix.lower() == ".png" else "image/jpeg"
        logo_uri = f"data:{mime};base64,{base64.b64encode(logo_path.read_bytes()).decode('ascii')}"
    css = """
    <style>
    :root { --idc-navy:__TEXT__; --idc-muted:__MUTED__; --idc-border:__BORDER__; --idc-green:#2F7D4A; --idc-blue:#246BCE; --idc-page:__PAGE__; --idc-card:__CARD__; --idc-soft:__SOFT__; }
    html, body, [class*="css"] { font-family: "Segoe UI", Arial, sans-serif; }
    [data-testid="stSidebar"] {
        background-color: var(--idc-page) !important;
        border-right: 1px solid var(--idc-border);
        width: 235px !important;
        min-width: 235px !important;
        max-width: 235px !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"] {
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
    }
    [data-testid="stSidebar"][data-collapsed="true"] > div {
        width: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    /* Streamlit owns the sidebar/main grid. Do not add a second offset here:
       doing so leaves ticket forms stuck at the expanded-sidebar position. */
    [data-testid="stAppViewContainer"] > .main { width:auto !important; margin-left:0 !important; transition:width .2s ease, margin-left .2s ease; }
    [data-testid="stMainBlockContainer"] { max-width:none !important; width:100% !important; padding-left:3rem !important; padding-right:3rem !important; }
    [data-testid="stSidebarCollapsedControl"] { background:var(--idc-card) !important; border:1px solid var(--idc-border) !important; border-radius:10px !important; }
    [data-testid="stSidebarCollapsedControl"] button { width:2.25rem !important; height:2.25rem !important; background-image:url('__SIDEBAR_LOGO__') !important; background-size:1.65rem 1.65rem !important; background-position:center !important; background-repeat:no-repeat !important; }
    [data-testid="stSidebarCollapsedControl"] button span { visibility:hidden !important; }
    [data-testid="stSidebar"] .stButton > button {
        border-radius: 14px !important;
        border: 1px solid rgba(16,42,67,0.08) !important;
        text-align: left !important;
        padding: 0.75rem 0.9rem !important;
        margin-bottom: 0.45rem !important;
        background: var(--idc-card) !important;
        color: var(--idc-navy) !important;
    }
    [data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: var(--idc-agency, var(--idc-green)) !important;
        color: white !important;
        border-color: transparent !important;
    }
    .stButton > button {
        background-color: var(--idc-green) !important;
        color: white !important;
    }
    .stButton > button[kind="secondary"] {
        background-color: var(--idc-agency, var(--idc-green)) !important;
        border-color: var(--idc-agency, var(--idc-green)) !important;
        color: white !important;
    }
    /* Form actions follow the active agency theme. Closed/confirmed badges
       remain green independently of the agency. */
    .stFormSubmitButton > button,
    .stFormSubmitButton > button[kind="primary"] {
        background-color: var(--idc-agency, var(--idc-green)) !important;
        border-color: var(--idc-agency, var(--idc-green)) !important;
        color: white !important;
    }
    div[data-testid="stButton"]:has(button[kind="secondary"]) > button {
        background-color: var(--idc-agency, var(--idc-green)) !important;
        border-color: var(--idc-agency, var(--idc-green)) !important;
        color: white !important;
    }
    .hero-card, .panel, .field-card, .detail-sheet, .nav-shell {
        background: var(--idc-card);
        border-radius: 20px;
        box-shadow: 0 8px 28px rgba(16,42,67,0.07);
        border: 1px solid var(--idc-border);
        padding: 1.25rem 1.35rem;
        margin-bottom: 1rem;
    }
    .panel {
        margin-top: 0.35rem;
    }
    .hero-big { font-size: 2rem; font-weight: 800; color: var(--idc-navy); margin: 0; }
    .hero-muted { color: var(--idc-muted); margin-top: .35rem; line-height: 1.5; }
    .section-title { font-weight: 800; color: var(--idc-navy); font-size: 1.05rem; margin-bottom: .5rem; }
    .metric-card { border-radius: 18px; padding: 1rem; background: var(--idc-card); border:1px solid var(--idc-border); box-shadow:0 5px 18px rgba(16,42,67,.05); }
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
    .stApp { background: var(--idc-page); color: var(--idc-navy); }
    [data-testid="stHeader"] { background: var(--idc-page); }
    [data-testid="stMarkdownContainer"] p, label, .stCaption { color: var(--idc-navy); }
    input, textarea, [data-baseweb="select"] > div { background: var(--idc-soft) !important; color: var(--idc-navy) !important; border-color: var(--idc-border) !important; }
    .station-chip { display:inline-block; padding:.35rem .7rem; border-radius:999px; background:var(--idc-soft); color:var(--idc-green); font-weight:700; }
    .idc-eyebrow { color:var(--idc-muted); text-transform:uppercase; letter-spacing:.08em; font-size:.72rem; font-weight:800; }
    .idc-card-title { color:var(--idc-navy); font-weight:800; font-size:1.05rem; }
    .idc-card-subtitle { color:var(--idc-muted); font-size:.9rem; margin-top:.2rem; }
    .idc-step { display:flex; align-items:center; gap:.65rem; padding:.7rem .85rem; border:1px solid var(--idc-border); border-radius:14px; background:var(--idc-card); }
    .idc-step-number { width:1.7rem; height:1.7rem; border-radius:50%; display:flex; align-items:center; justify-content:center; background:var(--idc-soft); color:var(--idc-green); font-weight:800; }
    .idc-list-card { background:var(--idc-card); border:1px solid var(--idc-border); border-radius:14px; overflow:hidden; }
    .idc-list-row { display:flex; justify-content:space-between; gap:1rem; padding:.78rem .9rem; border-bottom:1px solid var(--idc-border); color:var(--idc-navy); }
    .idc-list-row:last-child { border-bottom:0; }
    .idc-list-label { color:var(--idc-muted); font-size:.78rem; font-weight:700; }
    .idc-list-value { color:var(--idc-navy); font-weight:800; }
    .ticket-hero { background:var(--idc-card); border:1px solid var(--idc-border); border-radius:22px; padding:1.35rem 1.5rem; margin-bottom:1rem; }
    .ticket-id { color:var(--idc-muted); font-size:.78rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
    .ticket-title { color:var(--idc-navy); font-size:1.65rem; font-weight:900; line-height:1.2; margin:.25rem 0 .45rem; }
    .ticket-meta { color:var(--idc-muted); font-size:.9rem; }
    .ticket-info-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.7rem; }
    .ticket-info { background:var(--idc-soft); border:1px solid var(--idc-border); border-radius:14px; padding:.75rem .85rem; }
    .ticket-info-label { color:var(--idc-muted); font-size:.75rem; font-weight:800; text-transform:uppercase; letter-spacing:.04em; }
    .ticket-info-value { color:var(--idc-navy); font-weight:750; margin-top:.18rem; }
    .comment-card { background:var(--idc-soft); border:1px solid var(--idc-border); border-radius:14px; padding:.8rem; margin-bottom:.65rem; }
    .comment-author { color:var(--idc-navy); font-weight:800; }
    .comment-time { color:var(--idc-muted); font-size:.75rem; }
    .ticket-description { color:var(--idc-navy); font-size:1rem; line-height:1.7; white-space:pre-wrap; background:var(--idc-soft); border:1px solid var(--idc-border); border-radius:14px; padding:1rem; }
    .management-action-spacer { height:.5rem; }
    [data-testid="stSidebar"] [data-testid="stImage"], [data-testid="stSidebar"] [data-testid="stImage"] > div { display:flex; justify-content:center; }
    [data-testid="stSidebar"] [data-testid="stImage"] img { display:block !important; margin-left:auto !important; margin-right:auto !important; }
    section[data-testid="stSidebar"] img { display:block !important; margin-left:auto !important; margin-right:auto !important; }
    section[data-testid="stSidebar"] [data-testid="stImage"] { width:100% !important; display:flex !important; justify-content:center !important; }
    section[data-testid="stSidebar"] [data-testid="stImage"] > div { display:flex !important; justify-content:center !important; width:100% !important; }
    section[data-testid="stSidebar"] .sidebar-logo-wrap { width:100% !important; display:flex !important; justify-content:center !important; align-items:center !important; margin:.35rem 0 .55rem !important; }
    section[data-testid="stSidebar"] .sidebar-logo { display:block !important; width:64px !important; height:64px !important; object-fit:contain !important; margin:0 auto !important; }
    .sidebar-agency { text-align:center; font-weight:800; margin:.35rem 0 1rem; }
    [data-testid="stColumn"]:has(.management-action-spacer) > div { padding:1rem !important; }
    [data-testid="stColumn"]:has(.management-action-spacer) textarea { min-height:120px !important; }
    .ai-suggestion-box {
        background: var(--idc-soft);
        border: 1px solid var(--idc-green);
        border-radius: 16px;
        padding: 1.2rem 1.4rem;
        margin: 1rem 0;
    }
    .ai-suggestion-title {
        font-weight: 800;
        color: var(--idc-green);
        font-size: 1.1rem;
        margin-bottom: 0.8rem;
    }
    .ai-suggestion-item {
        background: var(--idc-card);
        border-radius: 12px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.6rem;
        border: 1px solid var(--idc-border);
    }
    .ai-suggestion-label {
        font-weight: 700;
        color: var(--idc-navy);
        font-size: 0.9rem;
    }
    .ai-suggestion-value {
        color: var(--idc-green);
        font-weight: 600;
        font-size: 1rem;
    }
    .stButton > button, .stFormSubmitButton > button {
        transition: transform .12s ease, box-shadow .12s ease;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 14px rgba(16,42,67,.14);
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 18px !important;
        border-color: var(--idc-border) !important;
        box-shadow: 0 4px 16px rgba(16,42,67,0.06);
        transition: box-shadow .15s ease, transform .15s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 10px 26px rgba(16,42,67,0.1);
    }
    .idc-ticket-card-top { display:flex; align-items:center; justify-content:space-between; gap:.5rem; margin-bottom:.35rem; }
    .idc-ticket-card-title { font-weight:800; color:var(--idc-navy); font-size:1.02rem; line-height:1.3; margin-bottom:.25rem; }
    .idc-ticket-card-meta { color:var(--idc-muted); font-size:.85rem; }
    @media (max-width: 800px) {
      .hero-big { font-size:1.55rem; }
      .hero-card, .panel, .field-card, .detail-sheet { padding:1rem; border-radius:16px; }
      .metric-card { padding:.8rem; }
      [data-testid="stMainBlockContainer"] { padding-left:1rem !important; padding-right:1rem !important; }
      .management-action-spacer { height:1rem; }
    }
    @media (max-width: 680px) {
      [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; row-gap: .5rem !important; }
      [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important; }
      .ticket-info-grid { grid-template-columns: 1fr !important; }
      .idc-ticket-card-top { flex-wrap: wrap; }
      /* Below tablet width the sidebar becomes a slide-over overlay instead of
         pushing the main content off-screen (it was reserving a fixed 235px
         on viewports where that left little to no room for the page). */
      [data-testid="stSidebar"] {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        height: 100vh !important;
        z-index: 999 !important;
        width: 82vw !important;
        min-width: 82vw !important;
        max-width: 82vw !important;
        box-shadow: 0 0 28px rgba(16,42,67,.3);
        transition: transform .2s ease;
      }
      [data-testid="stSidebar"][data-collapsed="true"] {
        width: 82vw !important;
        min-width: 82vw !important;
        max-width: 82vw !important;
        transform: translateX(-100%);
      }
      [data-testid="stAppViewContainer"] > .main { margin-left: 0 !important; }
    }
    </style>
    """
    soft_color = "#223344" if dark_mode else "#F7FAFC"
    css = css.replace("__TEXT__", text_color).replace("__MUTED__", muted_color).replace("__BORDER__", border_color).replace("__PAGE__", page_bg).replace("__CARD__", card_bg).replace("__SOFT__", soft_color).replace("__SIDEBAR_LOGO__", logo_uri)
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
      <div style="font-weight:800;color:var(--idc-navy);margin-bottom:.2rem;">{title}</div>
      <div style="font-size:2rem;font-weight:900;color:{accent};line-height:1;">{value}</div>
      <div style="color:var(--idc-muted);margin-top:.35rem;">{subtitle}</div>
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


def ticket_card(ticket: dict, key_prefix: str, meta: str, button_label: str = "Ouvrir →") -> bool:
    """Render one ticket as a clickable card. Returns True when its open button is pressed."""
    with st.container(border=True):
        left, right = st.columns([0.74, 0.26], vertical_alignment="center")
        with left:
            st.markdown(
                f'''<div class="idc-ticket-card-top"><span class="ticket-id">{ticket["id"]}</span>{status_badge(ticket["status"])}</div>
                <div class="idc-ticket-card-title">{ticket["subject"]}</div>
                <div class="idc-ticket-card-meta">{meta}</div>''',
                unsafe_allow_html=True,
            )
        with right:
            opened = st.button(button_label, key=f"{key_prefix}_{ticket['id']}", width="stretch")
    return opened


