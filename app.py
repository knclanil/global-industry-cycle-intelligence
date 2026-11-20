"""Global Industry Cycle Intelligence — Global, USA and India sector pages."""
from pathlib import Path
import streamlit as st
from dashboard import render_dashboard
st.set_page_config(page_title='Global Industry Cycle Intelligence', page_icon='🌐', layout='wide')
from design_system import apply_global_design
apply_global_design()
# Grouped sidebar navigation. The selected page is stored in session state so
# changing groups does not reset the current dashboard's other widgets.
NAV_GROUPS = {
    '🕸️ KNOWLEDGE GRAPHS': ['Global Knowledge Graph', 'USA Knowledge Graph', 'India Knowledge Graph',
                            'Global Capital Intelligence Network', 'Leading & Lagging Companies'],
    '🌍 GLOBAL': ['Global Countries', 'Global Sectors', 'Global Factors', 'Global Asset Flow', 'Global Analysis'],
    '🇺🇸 USA': ['USA Sector', 'USA Factors', 'USA Asset Flow', 'USA Analysis'],
    '🇮🇳 INDIA': ['India Sector', 'India Factors', 'India Asset Flow', 'India Analysis',
                  'India Sector & Factor Holdings', 'India Overlap & Leadership', 'India Sector & Factor Financials'],
    '💼 COMPANY FINANCIALS': ['Fundamental Quality Rankings', 'Company Financial Research',
                              'USA Company Financial KPI Intelligence', 'India Company Financial KPI Intelligence',
                              'India Fundamental Valuation'],
    '📋 OTHER RESEARCH': ['Company Holdings Leadership', 'Data Table', 'Wiki'],
}

PAGE_LABELS = {
 'Global Capital Intelligence Network': 'Capital Network',
 'Global Countries': 'Countries',
 'Leading & Lagging Companies': 'Leading & Lagging',
 'Fundamental Quality Rankings': 'Quality Rankings',
 'USA Company Financial KPI Intelligence': 'USA Financial KPIs',
 'India Company Financial KPI Intelligence': 'India Financial KPIs',
 'India Sector & Factor Financials': 'India Sector & Factor Financials',
 'India Sector & Factor Holdings': 'India Holdings Explorer',
 'India Overlap & Leadership': 'India Overlap & Leadership',
 'India Fundamental Valuation': 'India Valuation',
 'Company Financial Research': 'USA Financial Research',
 'Global Knowledge Graph': 'Global', 'USA Knowledge Graph': 'USA', 'India Knowledge Graph': 'India',
 'Global Analysis': 'Sector · Factor · Holdings', 'USA Analysis': 'Sector · Factor · Holdings',
 'India Analysis': 'Sector · Factor · Holdings',
}
PAGE_ICONS = {
    'Global Knowledge Graph': '🌍', 'USA Knowledge Graph': '🇺🇸', 'India Knowledge Graph': '🇮🇳',
    'Global Analysis': '📊', 'USA Analysis': '📊', 'India Analysis': '📊',
    'Global Capital Intelligence Network': '🕸️', 'Leading & Lagging Companies': '🔀',
    'Global Countries': '🗺️',
    'Global Asset Flow': '🌍', 'USA Asset Flow': '🇺🇸', 'India Asset Flow': '🇮🇳',
    'Global Sectors': '🌍', 'USA Sector': '🇺🇸', 'India Sector': '🇮🇳',
    'Global Factors': '🌍', 'USA Factors': '🇺🇸', 'India Factors': '🇮🇳', 'India Sector & Factor Holdings': '🇮🇳', 'India Overlap & Leadership': '🏆', 'India Sector & Factor Financials': '📈',
    'Fundamental Quality Rankings': '🏅', 'Company Holdings Leadership': '🏆', 'Company Financial Research': '📑', 'USA Company Financial KPI Intelligence': '📊', 'India Company Financial KPI Intelligence': '🇮🇳', 'India Fundamental Valuation': '💠', 'Data Table': '🗂️', 'Wiki': '📖',
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
/* Active route uses Streamlit's primary button type; never highlight inactive pages. */
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"],
[data-testid="stSidebar"] [data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
  background:linear-gradient(90deg,#145678,#1c3550)!important;
  color:#fff!important; border:1px solid #4ac6ed!important;
  box-shadow:inset 4px 0 #55d5ff,0 0 0 1px rgba(81,183,232,.15);
  font-weight:750!important;
}
[data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"] {
  background:transparent!important; border:1px solid transparent!important;
  color:#b9c8df!important; font-weight:450;
}
[data-testid="stSidebar"] details {border:0;}
[data-testid="stSidebar"] details summary {font-size:0.81rem; font-weight:700; letter-spacing:0.025em;}
[data-testid="stSidebar"] hr {margin:0.7rem 0; border-color:#30405b;}
</style>""", unsafe_allow_html=True)
with st.sidebar:
    st.markdown('<div class="app-brand">◈ MARKET INTELLIGENCE</div><div class="app-brand-name">Global Industry<br>Cycle Intelligence</div><div class="app-brand-sub">Research terminal</div>', unsafe_allow_html=True)
    st.divider()
    for group, items in NAV_GROUPS.items():
        expanded = st.session_state.selected_page in items
        with st.expander(group, expanded=expanded):
            for item in items:
                active = item == st.session_state.selected_page
                label = f"{PAGE_ICONS[item]}  {PAGE_LABELS.get(item, item)}"
                if st.button(label, key=f'nav_{item}', use_container_width=True,
                             type='primary' if active else 'secondary'):
                    if not active:
                        st.session_state.selected_page = item
                        st.rerun()
    st.divider()
page = st.session_state.selected_page
group_name = next((g.split(' ', 1)[-1].title() for g, items in NAV_GROUPS.items() if page in items), 'Intelligence')
st.markdown(f'<div class="app-topline"><span class="app-path">GLOBAL INDUSTRY  /  {group_name.upper()}  /  {page.upper()}</span><span class="app-pill">RESEARCH</span></div>', unsafe_allow_html=True)

if page in ('Global Knowledge Graph', 'USA Knowledge Graph', 'India Knowledge Graph'):
    from regional_workspace import render_graph
    render_graph(page.split(' ',1)[0])
elif page in ('Global Analysis', 'USA Analysis', 'India Analysis'):
    from regional_workspace import render_analysis
    render_analysis(page.split(' ',1)[0])
elif page == 'Global Capital Intelligence Network':
    from capital_network import render_capital_network
    render_capital_network()
elif page == 'Leading & Lagging Companies':
    from leading_lagging_ui import render_leading_lagging_graph
    render_leading_lagging_graph()
elif page == 'Company Holdings Leadership':
    from holdings_intelligence import render_holdings_intelligence
    render_holdings_intelligence()
elif page == 'Fundamental Quality Rankings':
    from fundamental_rankings_ui import render_fundamental_rankings
    render_fundamental_rankings()
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
