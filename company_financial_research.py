"""Existing Company Financial Research route with visible MongoDB fundamentals."""
import re
import streamlit as st


def render_company_financial_research():
    from research_theme import apply_research_theme
    apply_research_theme()
    st.title('📑 Company Financial Research')
    st.caption('MaketData MongoDB Atlas financial statements · read-only connection')
    ticker_default = str(st.session_state.get('research_ticker') or 'AAPL')
    with st.form('research_company_form'):
        ticker = st.text_input('US company ticker', value=ticker_default, placeholder='AAPL').strip().upper()
        submitted = st.form_submit_button('Load company financials', type='primary')
    if submitted:
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9.\-]{0,14}', ticker):
            st.error('Enter a valid ticker (letters, numbers, period or hyphen).')
            return
        st.session_state.research_ticker = ticker
        st.session_state.research_loaded = ticker
        st.session_state['maketdata_tickers'] = ticker
        st.session_state.maketdata_requested = True
    mongo_tab, legacy_tab = st.tabs(['🟢 MaketData MongoDB Fundamentals', 'Existing SEC Research (legacy)'])
    with mongo_tab:
        from maketdata_ui import render_maketdata
        render_maketdata()
    with legacy_tab:
        st.info('This is the existing SEC-based research view. MongoDB data is shown in the first tab; the legacy view is retained for compatibility during migration.')
        if st.session_state.get('research_loaded'):
            from financial_research_ui import render_financial_research
            render_financial_research(st.session_state.research_loaded)
        else:
            st.caption('Enter a ticker and click Load company financials to open the legacy research view.')
