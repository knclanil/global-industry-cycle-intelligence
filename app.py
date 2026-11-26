"""Global Industry Cycle Intelligence: aggregate asset, sector and factor research only."""
from pathlib import Path
import streamlit as st
st.set_page_config(page_title="Global Industry Cycle Intelligence",page_icon="🌐",layout="wide")
from design_system import apply_global_design
from dashboard import render_dashboard
from aggregate_graph import render_aggregate_graph
from wiki_page import render_wiki
apply_global_design()
NAV={
 "🕸️ KNOWLEDGE GRAPHS": ["Global Knowledge Graph","USA Knowledge Graph","India Knowledge Graph"],
 "🌍 GLOBAL": ["Global Countries","Global Asset Flow","Global Sectors","Global Factors"],
 "🇺🇸 USA": ["USA Asset Flow","USA Sectors","USA Factors"],
 "🇮🇳 INDIA": ["India Asset Flow","India Sectors","India Factors"],
 "📖 WIKI": ["Market Intelligence Wiki"],
}
MARKETS={"Global Countries":"Countries","Global Asset Flow":"GlobalAssets","Global Sectors":"Global","Global Factors":"GlobalFactors","USA Asset Flow":"USAAssets","USA Sectors":"USA","USA Factors":"USAFactors","India Asset Flow":"IndiaAssets","India Sectors":"India","India Factors":"IndiaFactors"}
PAGES=[x for group in NAV.values() for x in group]
if st.session_state.get('selected_page') not in PAGES: st.session_state.selected_page="Global Knowledge Graph"
with st.sidebar:
 st.title("🌐 Global Industry Cycle Intelligence")
 st.caption("Aggregate markets · no company-level research")
 for group, pages in NAV.items():
  with st.expander(group,expanded=st.session_state.selected_page in pages):
   for name in pages:
    if st.button(name,key='nav_'+name,use_container_width=True,type='primary' if name==st.session_state.selected_page else 'secondary'):
     st.session_state.selected_page=name
     st.rerun()
page=st.session_state.selected_page
st.caption('GLOBAL INDUSTRY / '+page.upper())
if page.endswith('Knowledge Graph'):
 render_aggregate_graph(page.split(' ')[0])
elif page == 'Market Intelligence Wiki':
 render_wiki()
else:
 render_dashboard(MARKETS[page])
