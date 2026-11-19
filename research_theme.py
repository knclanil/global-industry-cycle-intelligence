"""Shared dark research styling matching Global Industry Cycle Intelligence."""
import streamlit as st

RESEARCH_CSS = """
<style>
:root { --research-bg:#0b1220; --research-panel:#142137; --research-border:#2a3c55; --research-muted:#a9bbd3; --research-accent:#51b7e8; }
.stApp {background:#0b1220;color:#e7eef9;}
[data-testid="stMetric"] {background:linear-gradient(145deg,#182a43,#111e32);border:1px solid #2a3c55;border-radius:13px;padding:16px 18px;box-shadow:0 6px 20px #00000020;}
[data-testid="stMetricLabel"] {color:#b6c7de!important;font-weight:600;}
[data-testid="stMetricValue"] {color:#f2f7ff!important;letter-spacing:-.02em;}
[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:6px;overflow-x:auto;border-bottom:1px solid #2a3c55;padding-bottom:8px;}
[data-testid="stTabs"] button[role="tab"] {background:#142137;border:1px solid #293d58;border-radius:9px;color:#c4d4e8;padding:10px 14px;white-space:nowrap;}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {background:#193a53;color:#f4fbff;border-color:#4ca9d8;}
[data-testid="stDataFrame"] {border:1px solid #2a3c55;border-radius:10px;overflow:hidden;}
[data-testid="stForm"] {background:#111f34;border:1px solid #2a3c55;border-radius:14px;padding:18px;}
[data-testid="stAlert"] {border-radius:10px;}
[data-testid="stExpander"] {border:1px solid #2a3c55;border-radius:10px;background:#111d30;}
[data-testid="stHeading"] h1,[data-testid="stHeading"] h2 {letter-spacing:-.035em;}
[data-testid="stCaptionContainer"] {color:#a9bbd3;}
[data-testid="stPlotlyChart"] {background:#142137;border:1px solid #2a3c55;border-radius:12px;padding:8px;}
</style>
"""

def apply_research_theme():
    st.markdown(RESEARCH_CSS, unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    template='plotly_dark',
    paper_bgcolor='#142137',
    plot_bgcolor='#142137',
    font=dict(color='#dce8f7', family='Arial, sans-serif'),
    title_font=dict(color='#f2f7ff', size=17),
    xaxis=dict(gridcolor='#293d58', linecolor='#3b536f', zerolinecolor='#293d58'),
    yaxis=dict(gridcolor='#293d58', linecolor='#3b536f', zerolinecolor='#293d58'),
    legend=dict(bgcolor='rgba(0,0,0,0)'),
    hoverlabel=dict(bgcolor='#213550', font_color='#f2f7ff'),
)
