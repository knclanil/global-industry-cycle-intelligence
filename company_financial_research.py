"""MaketData-backed financial research; preserves original navigation and selection state."""
import re
import streamlit as st

def render_company_financial_research():
    from research_theme import apply_research_theme
    apply_research_theme()
    st.title('📑 Company Financial Research')
    st.caption('MaketData MongoDB Atlas · validated annual and quarterly SEC financials')
    current = st.session_state.get('research_loaded') or st.session_state.get('research_ticker') or 'AAPL'
    with st.form('research_company_form'):
        ticker = st.text_input('Company ticker', value=str(current)).strip().upper()
        submitted = st.form_submit_button('Load company financials', type='primary')
    if submitted:
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9.\- ]{0,14}', ticker):
            st.error('Enter a valid ticker.'); return
        st.session_state.research_ticker = ticker
        st.session_state.research_loaded = ticker
    if not st.session_state.get('research_loaded'):
        st.info('Select a company and load its financials.'); return
    from maketdata_ui import render_maketdata
    render_maketdata()
