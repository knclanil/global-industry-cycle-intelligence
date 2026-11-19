"""Single visual language for the Global Industry Cycle Intelligence app.
UI only: this module does not fetch data or modify financial computations.
"""
from __future__ import annotations
import math
import streamlit as st

COLORS = dict(background="#0b1220", sidebar="#101a2d", panel="#142137", panel_alt="#182941",
              border="#2a3c55", accent="#51b7e8", text="#e7eef9", muted="#a7bbd5",
              green="#39c99d", red="#f0828d", amber="#eec176")

def compact_number(value, unit="", decimals=1):
    """Format scalar display values; never convert unknown to zero."""
    try:
        n = float(value)
        if not math.isfinite(n):
            return "N/A"
    except (ValueError, TypeError):
        return "N/A"
    a = abs(n)
    scale, suffix = ((1e12,"T") if a >= 1e12 else (1e9,"B") if a >= 1e9 else
                     (1e6,"M") if a >= 1e6 else (1e3,"K") if a >= 1e3 else (1,""))
    return f"{unit}{n / scale:,.{decimals}f}{suffix}"

def indian_number(value, *, crore=False, currency=True):
    """Crore-based amounts remain in crore; no accidental double conversion."""
    try:
        n=float(value)
        if not math.isfinite(n): return "N/A"
    except (TypeError, ValueError):
        return "N/A"
    prefix = "₹" if currency else ""
    if crore:
        return f"{prefix}{n/100000:,.2f} L Cr" if abs(n)>=100000 else f"{prefix}{n:,.2f} Cr"
    return f"{prefix}{n:,.2f}"

GLOBAL_CSS = r"""<style>
:root { color-scheme:dark; --bg:#0b1220; --sidebar:#101a2d; --panel:#142137; --raised:#182941;
 --stroke:#2a3c55; --accent:#51b7e8; --text:#e7eef9; --muted:#a7bbd5; }
html,body,[class*="css"],.stApp {font-family:Inter,"Segoe UI",Roboto,Arial,sans-serif!important;}
.stApp {background:var(--bg);color:var(--text);}
[data-testid="stMainBlockContainer"] {padding-top:1.3rem;padding-bottom:2.5rem;max-width:1600px;}
.block-container h1 {font-weight:760;letter-spacing:-.035em;font-size:clamp(1.55rem,2.3vw,2.18rem);line-height:1.2;margin-bottom:.4rem;}
.block-container h2 {font-weight:720;letter-spacing:-.025em;font-size:1.4rem;}
.block-container h3 {font-weight:690;letter-spacing:-.02em;font-size:1.08rem;}
[data-testid="stCaptionContainer"] {color:var(--muted);font-size:.82rem;line-height:1.38;}
[data-testid="stMetric"] {background:linear-gradient(155deg,#182a43,#122035);border:1px solid var(--stroke);
 border-radius:11px;padding:12px 14px;min-height:88px;box-shadow:none;}
[data-testid="stMetricLabel"] {font-size:.73rem;color:#b3c7df!important;font-weight:560;}
[data-testid="stMetricValue"] {font-size:clamp(1.17rem,1.45vw,1.65rem);letter-spacing:-.025em;font-variant-numeric:tabular-nums;color:#f2f8ff!important;}
[data-testid="stMetricDelta"] {font-size:.76rem;}
[data-testid="stSidebar"] {background:var(--sidebar);border-right:1px solid #253750;}
[data-testid="stSidebar"] [data-testid="stExpander"] {background:transparent;border:0;}
[data-testid="stSidebar"] details summary {font-size:.74rem;font-weight:760;letter-spacing:.075em;color:#849cb7;}
[data-testid="stSidebar"] button[kind="primary"],
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {background:#173c57!important;border:1px solid #398fbe!important;
 box-shadow:inset 3px 0 #64d4fb!important;color:#f6fbff!important;font-weight:700!important;}
[data-testid="stSidebar"] button[kind="secondary"] {border:1px solid transparent!important;background:transparent!important;color:#adc0d8!important;}
[data-testid="stSidebar"] button[kind="secondary"]:hover {background:#1a2f48!important;color:white!important;}
[data-testid="stTabs"] [data-baseweb="tab-list"] {border-bottom:1px solid var(--stroke);gap:5px;overflow-x:auto;padding-bottom:5px;}
[data-testid="stTabs"] button[role="tab"] {background:#142137;border:1px solid #293c55;border-radius:8px;
 color:#b9cde2;padding:8px 12px;white-space:nowrap;font-size:.83rem;}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {background:#1a3852;border-color:#4eadd9;color:#fff;font-weight:700;}
[data-testid="stDataFrame"] {background:var(--panel);border:1px solid var(--stroke);border-radius:9px;overflow:hidden;}
[data-testid="stPlotlyChart"] {background:var(--panel);border:1px solid var(--stroke);border-radius:11px;padding:5px;overflow:hidden;}
[data-testid="stForm"] {background:#111e31;border:1px solid var(--stroke);border-radius:11px;padding:13px;}
[data-testid="stExpander"] {border:1px solid var(--stroke);border-radius:9px;background:#101d30;}
[data-testid="stAlert"] {border-radius:9px;}
[data-testid="stButton"] button {border-radius:8px;min-height:2.25rem;}
[data-testid="stDownloadButton"] button {border-color:#31516c;color:#bfdcf2;font-size:.82rem;}
[data-testid="stSelectbox"] label,[data-testid="stTextInput"] label {font-size:.82rem;}
.app-brand {letter-spacing:.085em;font-size:.72rem;color:#8db2d0;font-weight:800;margin:4px 0 2px;}
.app-brand-name {font-size:1.04rem;letter-spacing:-.025em;font-weight:780;line-height:1.25;color:#f3faff;}
.app-brand-sub {color:#829cb8;font-size:.73rem;margin-top:5px;}
.app-topline {display:flex;align-items:center;gap:9px;justify-content:space-between;margin-bottom:11px;border-bottom:1px solid #26374e;padding-bottom:10px;}
.app-path {font-size:.75rem;letter-spacing:.04em;color:#8fabca;}
.app-pill {font-size:.69rem;color:#88d3f7;background:#13314a;padding:4px 9px;border:1px solid #285572;border-radius:999px;}
.kpi-tile,.ifr-tile {background:linear-gradient(145deg,#172941,#112035)!important;border:1px solid var(--stroke)!important;
 border-radius:9px!important;min-height:69px!important;padding:9px 12px!important;}
.kpi-number,.ifr-number {font-size:clamp(.95rem,1.2vw,1.25rem)!important;font-variant-numeric:tabular-nums;letter-spacing:-.025em;}
.kpi-label,.ifr-label {font-size:.71rem!important;}
.india-note,.ifr-callout,.iol-panel {border-radius:9px!important;}
@media (max-width:750px) {[data-testid="stMainBlockContainer"]{padding-left:.9rem;padding-right:.9rem;}
 [data-testid="stMetric"]{padding:9px;min-height:76px;} [data-testid="stMetricValue"]{font-size:1.1rem;}}
</style>"""

def apply_global_design():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
