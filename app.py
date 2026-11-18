"""Global Industry Cycle Intelligence — Global, USA and India sector pages."""
from pathlib import Path
import streamlit as st
from dashboard import render_dashboard
st.set_page_config(page_title='Global Industry Cycle Intelligence', page_icon='🌐', layout='wide')
st.markdown("""<style>.stApp{background:#0b1220;color:#e7eef9}
[data-testid="stMetric"]{background:#142137;border:1px solid #2a3c55;border-radius:12px;padding:16px}
[data-testid="stMetricLabel"]{color:#b6c7de}</style>""", unsafe_allow_html=True)
page=st.sidebar.radio('NAVIGATION', ['Global Sectors', 'Global Countries', 'Global Factors', 'Global Asset Flow', 'USA Sector', 'USA Factors', 'USA Asset Flow', 'India Sector', 'India Factors', 'India Asset Flow', 'Wiki'], key='main_navigation')
if page == 'Wiki':
    region=st.radio('Documentation for', ['Global Sectors', 'Global Countries', 'Global Factors', 'Global Asset Flow', 'USA Sector', 'USA Factors', 'USA Asset Flow', 'India Sector', 'India Factors', 'India Asset Flow'], horizontal=True)
    st.title(f'{region} Wiki')
    filename = {'India Sector': 'INDIA_WIKI.md', 'Global Sectors': 'GLOBAL_WIKI.md', 'Global Countries': 'COUNTRIES_WIKI.md', 'Global Factors': 'GLOBAL_FACTORS_WIKI.md', 'USA Factors': 'USA_FACTORS_WIKI.md', 'India Factors': 'INDIA_FACTORS_WIKI.md', 'Global Asset Flow': 'GLOBAL_ASSET_WIKI.md', 'USA Asset Flow': 'USA_ASSET_WIKI.md', 'India Asset Flow': 'INDIA_ASSET_WIKI.md'}.get(region, 'WIKI.md')
    path=Path(__file__).resolve().parent / filename
    if path.is_file():
        st.markdown(path.read_text(encoding='utf-8'))
    else:
        st.info('Documentation file is missing from deployment. Refer to the repository README for methodology.')
else:
    render_dashboard({'India Sector': 'India', 'Global Sectors': 'Global', 'Global Countries': 'Countries', 'Global Factors': 'GlobalFactors', 'USA Factors': 'USAFactors', 'India Factors': 'IndiaFactors', 'Global Asset Flow': 'GlobalAssets', 'USA Asset Flow': 'USAAssets', 'India Asset Flow': 'IndiaAssets'}.get(page, 'USA'))
