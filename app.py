"""Global Industry Cycle Intelligence — Global, USA and India sector pages."""
from pathlib import Path
import streamlit as st
from dashboard import render_dashboard
st.set_page_config(page_title='Global Industry Cycle Intelligence', page_icon='🌐', layout='wide')
st.markdown("""<style>.stApp{background:#0b1220;color:#e7eef9}
[data-testid="stMetric"]{background:#142137;border:1px solid #2a3c55;border-radius:12px;padding:16px}
[data-testid="stMetricLabel"]{color:#b6c7de}</style>""", unsafe_allow_html=True)
# Grouped sidebar navigation. The selected page is stored in session state so
# changing groups does not reset the current dashboard's other widgets.
NAV_GROUPS = {
    '🌐 GLOBAL INTELLIGENCE': ['Global Capital Intelligence Network', 'Company Holdings Leadership', 'Company Financial Research', 'USA Company Financial KPI Intelligence', 'India Company Financial KPI Intelligence', 'India Fundamental Valuation'],
    '🌎 COUNTRY ANALYSIS': ['Global Countries'],
    '💰 ASSET CLASS ANALYSIS': ['Global Asset Flow', 'USA Asset Flow', 'India Asset Flow'],
    '📊 SECTOR ANALYSIS': ['Global Sectors', 'USA Sector', 'India Sector'],
    '🧩 FACTOR ANALYSIS': ['Global Factors', 'USA Factors', 'India Factors', 'India Sector & Factor Holdings', 'India Overlap & Leadership', 'India Sector & Factor Financials'],
    '📚 DATA & RESEARCH': ['Data Table', 'Wiki'],
}
PAGE_ICONS = {
    'Global Capital Intelligence Network': '🕸️',
    'Global Countries': '🌎',
    'Global Asset Flow': '🌍', 'USA Asset Flow': '🇺🇸', 'India Asset Flow': '🇮🇳',
    'Global Sectors': '🌍', 'USA Sector': '🇺🇸', 'India Sector': '🇮🇳',
    'Global Factors': '🌍', 'USA Factors': '🇺🇸', 'India Factors': '🇮🇳', 'India Sector & Factor Holdings': '🇮🇳', 'India Overlap & Leadership': '🏆', 'India Sector & Factor Financials': '📈',
    'Company Holdings Leadership': '🏆', 'Company Financial Research': '📑', 'USA Company Financial KPI Intelligence': '📊', 'India Company Financial KPI Intelligence': '🇮🇳', 'India Fundamental Valuation': '💠', 'Data Table': '🗂️', 'Wiki': '📖',
}
ALL_PAGES = [item for items in NAV_GROUPS.values() for item in items]
if st.session_state.get('selected_page') not in ALL_PAGES:
    st.session_state.selected_page = 'Global Capital Intelligence Network'

st.markdown("""<style>
[data-testid="stSidebar"] {background: #101a2d;}
[data-testid="stSidebar"] [data-testid="stButton"] button {
  width:100%; text-align:left; justify-content:flex-start;
  border-radius:7px; border:1px solid transparent;
  background:transparent; color:#c9d8eb; padding:0.32rem 0.65rem;
  min-height:2.15rem; font-size:0.87rem;
}
[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
  background:#213550; border-color:#385170; color:white;
}
[data-testid="stSidebar"] details {border:0;}
[data-testid="stSidebar"] details summary {font-size:0.81rem; font-weight:700; letter-spacing:0.025em;}
[data-testid="stSidebar"] hr {margin:0.7rem 0; border-color:#30405b;}
</style>""", unsafe_allow_html=True)
with st.sidebar:
    st.markdown('### ◈ GLOBAL INDUSTRY\nCYCLE INTELLIGENCE')
    st.caption('Market Rotation & Intelligence')
    st.divider()
    for group, items in NAV_GROUPS.items():
        expanded = st.session_state.selected_page in items
        with st.expander(group, expanded=expanded):
            for item in items:
                active = item == st.session_state.selected_page
                label = f"{'▌ ' if active else '   '}{PAGE_ICONS[item]}  {item}"
                if st.button(label, key=f'nav_{item}', use_container_width=True,
                             type='primary' if active else 'secondary'):
                    if not active:
                        st.session_state.selected_page = item
                        st.rerun()
    st.divider()
page = st.session_state.selected_page

if page == 'Global Capital Intelligence Network':
    from capital_network import render_capital_network
    render_capital_network()
elif page == 'Company Holdings Leadership':
    from holdings_intelligence import render_holdings_intelligence
    render_holdings_intelligence()
elif page == 'Company Financial Research':
    from company_financial_research import render_company_financial_research
    render_company_financial_research()
elif page == 'USA Company Financial KPI Intelligence':
    from company_kpi_metrics import render_company_kpi_metrics
    render_company_kpi_metrics()
elif page == 'India Company Financial KPI Intelligence':
    from india_kpi_intelligence import render_india_kpi_intelligence
    render_india_kpi_intelligence()
elif page == 'India Fundamental Valuation':
    from india_valuation_ui import render_india_valuation
    render_india_valuation()
elif page == 'India Sector & Factor Financials':
    from india_financial_ui import render_india_sector_factor_financials
    render_india_sector_factor_financials()
elif page == 'India Overlap & Leadership':
    from india_rankings_ui import render_india_overlap_leadership
    render_india_overlap_leadership()
elif page == 'India Sector & Factor Holdings':
    from india_constituents_ui import render_india_constituents
    render_india_constituents()
elif page == 'Data Table':
    from data_table import render_data_table
    render_data_table()
elif page == 'Wiki':
    region=st.radio('Documentation for', ['Global Sectors', 'Global Countries', 'Global Factors', 'Global Asset Flow', 'USA Sector', 'USA Factors', 'USA Asset Flow', 'India Sector', 'India Factors', 'India Asset Flow', 'Company Holdings Leadership', 'India Sector & Factor Holdings', 'India Overlap & Leadership', 'India Sector & Factor Financials', 'India Company Financial KPI Intelligence', 'India Fundamental Valuation'], horizontal=True)
    st.title(f'{region} Wiki')
    filename = {'India Sector': 'INDIA_WIKI.md', 'Global Sectors': 'GLOBAL_WIKI.md', 'Global Countries': 'COUNTRIES_WIKI.md', 'Global Factors': 'GLOBAL_FACTORS_WIKI.md', 'USA Factors': 'USA_FACTORS_WIKI.md', 'India Factors': 'INDIA_FACTORS_WIKI.md', 'Global Asset Flow': 'GLOBAL_ASSET_WIKI.md', 'USA Asset Flow': 'USA_ASSET_WIKI.md', 'India Asset Flow': 'INDIA_ASSET_WIKI.md', 'Company Holdings Leadership': 'HOLDINGS_LEADERSHIP_WIKI.md', 'India Sector & Factor Holdings': 'INDIA_CONSTITUENTS_GUIDE.md', 'India Overlap & Leadership': 'INDIA_OVERLAP_LEADERSHIP_GUIDE.md', 'India Sector & Factor Financials': 'INDIA_FINANCIAL_ANALYSIS_GUIDE.md', 'India Company Financial KPI Intelligence': 'INDIA_KPI_INTELLIGENCE_GUIDE.md', 'India Fundamental Valuation': 'INDIA_VALUATION_GUIDE.md'}.get(region, 'WIKI.md')
    path=Path(__file__).resolve().parent / filename
    if path.is_file():
        st.markdown(path.read_text(encoding='utf-8'))
    else:
        st.info('Documentation file is missing from deployment. Refer to the repository README for methodology.')
else:
    render_dashboard({'India Sector': 'India', 'Global Sectors': 'Global', 'Global Countries': 'Countries', 'Global Factors': 'GlobalFactors', 'USA Factors': 'USAFactors', 'India Factors': 'IndiaFactors', 'Global Asset Flow': 'GlobalAssets', 'USA Asset Flow': 'USAAssets', 'India Asset Flow': 'IndiaAssets'}.get(page, 'USA'))
