"""Read-only MongoDB fundamentals dashboard, exposed on the existing research route."""
import re
import pandas as pd
import streamlit as st
from maketdata_bridge import connection, fetch, metrics, score_universe, DEFAULT_WEIGHTS


def render_maketdata():
    st.subheader('MaketData · MongoDB Fundamental Analysis')
    st.caption('Source: MongoDB Atlas / companies, financial_annual, financial_quarterly. No SEC requests or database writes.')
    with st.expander('Database connection diagnostic', expanded=True):
        if st.button('Test MongoDB connection', key='maketdata_ping'):
            try:
                db = connection()
                db.command('ping')
                st.success('Connected to MongoDB Atlas. Database ping succeeded.')
                st.caption('Read-only financial collections: companies, financial_annual, financial_quarterly')
            except Exception as exc:
                st.error('MongoDB connection failed. Check Streamlit Secrets, Atlas access, and database permissions.')
                st.caption('Error type: ' + type(exc).__name__)
    initial = st.session_state.get('research_ticker') or 'AAPL'
    raw = st.text_input('Tickers to retrieve (comma-separated)', value=initial, key='maketdata_tickers')
    tickers = list(dict.fromkeys(t.strip().upper() for t in raw.split(',') if t.strip()))[:30]
    invalid = [t for t in tickers if not re.fullmatch(r'[A-Z0-9][A-Z0-9.\-]{0,14}', t)]
    if invalid:
        st.warning('Invalid ticker: ' + ', '.join(invalid))
        return
    clicked = st.button('Pull fundamentals from MongoDB', key='maketdata_fetch', type='primary')
    # The existing Load company financials button also triggers a MongoDB fetch.
    if not (clicked or st.session_state.pop('maketdata_requested', False)):
        st.info('Click “Pull fundamentals from MongoDB” to display live financial data. You can also use “Load company financials” above.')
        return
    if not tickers:
        st.warning('Enter at least one ticker.')
        return
    try:
        with st.spinner('Reading financial documents from MongoDB Atlas...'):
            data = fetch(tickers)
    except Exception as exc:
        st.error('MongoDB retrieval failed. Verify database connectivity and collection read permissions.')
        st.caption('Error type: ' + type(exc).__name__)
        return
    st.success('MongoDB query completed. ' + str(len(data)) + ' / ' + str(len(tickers)) + ' tickers returned.')
    missing = sorted(set(tickers) - set(data))
    if missing:
        st.warning('No MongoDB documents for: ' + ', '.join(missing))
    if not data:
        return
    overview = []
    observations = {}
    for ticker, entry in data.items():
        vals, valid_years = metrics(entry)
        observations[ticker] = vals
        overview.append({'Ticker': ticker, 'Company': entry.get('company', {}).get('name') or entry.get('company', {}).get('company_name') or '',
                         'Annual records': len(entry.get('annual', [])), 'Quarterly records': len(entry.get('quarterly', [])),
                         'Validated annual records': valid_years,
                         'Latest annual period': entry['annual'][0].get('period_end') if entry.get('annual') else None,
                         'Latest quarterly period': entry['quarterly'][0].get('period_end') if entry.get('quarterly') else None})
    st.markdown('#### MongoDB retrieval and coverage')
    st.dataframe(pd.DataFrame(overview), use_container_width=True, hide_index=True)
    st.markdown('#### Fundamental ratios (calculated from MongoDB annual records)')
    if any(observations.values()):
        st.dataframe(pd.DataFrame(observations).rename_axis('Metric'), use_container_width=True)
    else:
        st.warning('Companies were found, but no valid annual financial metrics are available.')
    st.caption('Ratios are raw decimals (0.15 = 15%). Missing or invalid values remain blank. Valuation ratios need verified current prices/market caps.')
    if len(observations) >= 2:
        with st.expander('Optional peer-relative weighted scoring'):
            weights = {k: st.number_input(k + ' weight (%)', min_value=0, max_value=100, value=round(v*100), key='maketdata_weight_'+k)/100 for k,v in DEFAULT_WEIGHTS.items()}
            if abs(sum(weights.values())-1) > 1e-6:
                st.warning('Weights must total 100%.')
            else:
                scored = score_universe(observations, weights)
                table = pd.DataFrame({t: {'Score': v['score'], 'Coverage': v['coverage'], **v['categories']} for t,v in scored.items()}).T
                st.dataframe(table, use_container_width=True)
                st.caption('Scores may be N/A without sufficient comparable peers and valuation data.')
    with st.expander('Raw annual and quarterly financial records', expanded=True):
        for ticker, entry in data.items():
            st.markdown('**' + ticker + '**')
            for kind in ('annual', 'quarterly'):
                rows = [{'Period end': r.get('period_end'), **(r.get('metrics') or {})} for r in entry.get(kind, [])]
                st.caption(kind.title() + ' financial records from financial_' + kind)
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.info('No ' + kind + ' financial records.')
