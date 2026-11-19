"""Reference-parity India Fundamental Valuation, adapted only for app routing.

The original attached project's valuation module and annual fundamental trends
remain separate, readable modules. All provider access is user-initiated.
"""
from __future__ import annotations
import pandas as pd
import streamlit as st
from pathlib import Path
from india_financial_data import safe_symbol
from india_financial_ui import _read
from research_theme import apply_research_theme
from india_valuation_reference import render_watchlist_valuation
from india_fundamental_trends_reference import render_india_trends

ROOT=Path(__file__).resolve().parent
HOLDINGS=ROOT/'data'/'india_holdings'

def render_india_valuation():
    apply_research_theme()
    st.caption('INDIA / NSE COMPANY RESEARCH / REFERENCE VALUATION ENGINE')
    st.markdown('### India Fundamental Valuation & Financial Trends')
    st.caption('Original reference methodology: NSE equity quote → Screener consolidated tables → Yahoo Finance fallback. Sources are attempted independently, and each published metric has provenance. Requests run only on button clicks.')
    directory=_read(HOLDINGS,'companies.csv')
    valid_symbols=[]
    if not directory.empty and 'symbol' in directory.columns:
        for raw in directory['symbol'].dropna().astype(str).unique():
            try:
                valid_symbols.append(safe_symbol(raw.removesuffix('.NS')))
            except ValueError:
                continue
        valid_symbols=sorted(set(valid_symbols))
    a,b=st.columns([2,3])
    with a:
        input_symbol=st.text_input('NSE ticker',value=st.session_state.get('reference_active_symbol','MGL'),key='ref_india_direct_ticker').strip().upper()
        try:
            symbol=safe_symbol(input_symbol.removesuffix('.NS'))
        except ValueError:
            st.error('Please enter a valid NSE symbol (for example MGL, RELIANCE or TCS).')
            return
        st.session_state['reference_active_symbol']=symbol
    with b:
        if valid_symbols:
            selected=st.selectbox('Or choose an NSE holdings company', ['Direct ticker']+valid_symbols, index=0, key='ref_india_holdings_symbol')
            if selected != 'Direct ticker':
                symbol=selected
                st.session_state['reference_active_symbol']=symbol
    st.caption(f'Financial statements: https://www.screener.in/company/{symbol}/consolidated/ · NSE index memberships are independent of financial valuation.')
    valuation, history=st.tabs(['Fundamental Valuation · original reference','Annual Fundamental Trends · original reference'])
    with valuation:
        render_watchlist_valuation(pd.DataFrame({'Symbol':[symbol]}))
    with history:
        render_india_trends(symbol)
    st.caption('Data rights: only use provider access where permitted; no rate-limit or access-control bypass. Screened values and provisional DCF are not verified fair values. Missing values remain N/A.')
