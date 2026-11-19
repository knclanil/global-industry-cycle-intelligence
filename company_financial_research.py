"""On-demand financial research, adapted from the attached Factor Holdings Intelligence project."""
import re
import streamlit as st

def render_company_financial_research():
    from research_theme import apply_research_theme
    apply_research_theme()
    st.title('📑 Company Financial Research')
    st.caption('SEC-sourced annual and quarterly statements, business quality, and conservative valuation research.')
    st.caption('On-demand research · SEC company facts · Cached financial statements')
    with st.expander('Data coverage and methodology', expanded=False):
        st.info('Search one SEC-reporting company at a time. Global issuers without SEC filings require another provider. Data availability depends on the saved SEC cache.')
    default = str(st.session_state.get('research_ticker', 'AAPL'))
    with st.form('research_company_form'):
        ticker = st.text_input('Company ticker', value=default, placeholder='AAPL').strip().upper()
        submitted = st.form_submit_button('Load company financials', type='primary')
    if submitted:
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9.\-]{0,14}', ticker):
            st.error('Enter a valid ticker (letters, numbers, period or hyphen).')
            return
        st.session_state.research_ticker = ticker
        st.session_state.research_loaded = ticker
    if not st.session_state.get('research_loaded'):
        st.caption('Financial statements are retrieved only after you click Load company financials.')
        return
    from financial_research_ui import render_financial_research
    render_financial_research(st.session_state.research_loaded)
