"""v3.6.16 | 2026-11-12 | NSE-first per-field valuation fallback, Screener second, Yahoo third; provenance and missing-data diagnostics.
v3.6.15 | 2026-11-12 | Independent Yahoo fallback for unavailable valuation fields; source-labelled N/A handling.
v3.5.3 | 2026-11-12 | Watchlist-based consolidated financial extraction and scenario valuation.
Use only where website access and terms permit; no bypass of access controls.
"""
from __future__ import annotations
import io
import re
from datetime import datetime, timezone
from urllib.parse import quote
import numpy as np
import pandas as pd
import requests
import streamlit as st


def normalize_symbol(value):
    """Compatibility with reference project's India Portfolio symbol normalizer."""
    from india_financial_data import safe_symbol
    return safe_symbol(str(value or '').strip().upper().removesuffix('.NS'))

BASE_URL = 'https://www.screener.in/company/{}/consolidated/'
HEADERS = {'User-Agent': 'IndiaValuationResearch/1.0 (manual, low-volume financial research)'}
TABLES = {'profit-loss': 'Profit & Loss', 'balance-sheet': 'Balance Sheet', 'cash-flow': 'Cash Flows', 'ratios': 'Ratios', 'quarters': 'Quarterly Results', 'shareholding': 'Shareholding Pattern'}


def company_url(symbol):
    from india_valuation_reference import normalize_symbol
    return BASE_URL.format(quote(normalize_symbol(symbol), safe=''))


def _html_table_to_frame(node):
    """Keep published header and all reported rows; no inferred values."""
    from lxml import html as lxml_html
    frame = pd.read_html(
        io.StringIO(lxml_html.tostring(node, encoding='unicode')),
        displayed_only=False,
    )[0]
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [
            ' '.join(dict.fromkeys(str(item).strip() for item in column
                                  if str(item).strip() and not str(item).startswith('Unnamed:')))
            for column in frame.columns
        ]
    else:
        frame.columns = [str(c).strip() for c in frame.columns]
    return frame


def parse_tables(html):
    """Read published visible company tables from a single Screener response.

    Shareholding can include quarterly and yearly variants. Peers may be
    loaded separately by Screener; no private/AJAX endpoints are requested.
    """
    from lxml import html as lxml_html
    root = lxml_html.fromstring(html)
    output = {}
    for section_id, name in TABLES.items():
        nodes = root.xpath(f'//*[@id="{section_id}"]//table')
        if not nodes:
            continue
        for idx, node in enumerate(nodes):
            try:
                frame = _html_table_to_frame(node)
            except (ValueError, IndexError):
                continue
            if frame.empty:
                continue
            if section_id == 'shareholding':
                # Only include variants with distinct data; preserve separately.
                candidate = name if idx == 0 else f'{name} ({"Yearly" if idx == 1 else f"View {idx+1}"})'
                if any(frame.equals(existing) for key, existing in output.items() if key.startswith(name)):
                    continue
                output[candidate] = frame
            elif name not in output:
                output[name] = frame
    peer_nodes = root.xpath('//*[@id="peers"]//table')
    if peer_nodes:
        try:
            peers = _html_table_to_frame(peer_nodes[0])
            if not peers.empty:
                output['Peer Comparison'] = peers
        except (ValueError, IndexError):
            pass
    return output


def peer_median_pe(tables):
    """Return Screener's explicit peer median P/E; never invent industry P/E."""
    frame = tables.get('Peer Comparison')
    if frame is None or frame.empty:
        return np.nan
    # Flatten multi-level headings without altering numeric cell values.
    columns = [' '.join(map(str, c)) if isinstance(c, tuple) else str(c)
               for c in frame.columns]
    pe_columns = [i for i, label in enumerate(columns)
                  if re.search(r'(?<![a-z])p\s*/\s*e(?![a-z])', label, re.I)]
    if not pe_columns:
        return np.nan
    for _, row in frame.iterrows():
        label = str(row.iloc[0]).strip()
        if re.search(r'\bmedian\b', label, re.I):
            val = number(row.iloc[pe_columns[0]])
            return val if np.isfinite(val) and val > 0 else np.nan
    return np.nan


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_company(symbol):
    url = company_url(symbol)
    response = requests.get(url, headers=HEADERS, timeout=18)
    response.raise_for_status()
    if 'text/html' not in response.headers.get('Content-Type', '').lower():
        raise ValueError('Source did not return HTML.')
    if len(response.content) > 3_000_000:
        raise ValueError('Unexpectedly large page.')
    tables = parse_tables(response.text)
    if not tables and not _screener_quote_fields(response.text):
        raise ValueError('No usable Screener tables or published ratios. Site may restrict automated requests.')
    return {'url': url, 'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'tables': tables, 'quote_fields': _screener_quote_fields(response.text)}


def number(value):
    if pd.isna(value):
        return np.nan
    s = str(value).strip().replace(',', '').replace('₹', '').replace('%', '')
    if not s or s in {'-', '—', 'nan'}:
        return np.nan
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return np.nan


def row_series(frame, patterns):
    if frame is None or frame.empty:
        return pd.Series(dtype=float)
    label_col = frame.columns[0]
    labels = frame[label_col].astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
    for pattern in patterns:
        matches = labels.str.contains(pattern, case=False, regex=True, na=False)
        if matches.any():
            row = frame.loc[matches].iloc[0]
            values = {str(col): number(row[col]) for col in frame.columns[1:] if re.search(r'\b(?:Mar|Jun|Sep|Dec)\s*\d{2,4}\b|\b(?:FY)?20\d{2}\b', str(col), re.I)}
            return pd.Series(values, dtype=float).dropna()
    return pd.Series(dtype=float)


def annual_values(frame, patterns):
    series = row_series(frame, patterns)
    return series[[bool(re.search(r'Mar\s*\d{2,4}|FY20\d{2}|^20\d{2}$', str(k), re.I)) for k in series.index]]


def cagr(series, years=5):
    vals = series.dropna()
    if len(vals) < years + 1:
        return np.nan
    a, b = float(vals.iloc[-years-1]), float(vals.iloc[-1])
    if a <= 0 or b <= 0:
        return np.nan
    return 100 * ((b/a)**(1/years) - 1)


def dcf_per_share(starting_fcf_cr, growth_pct, discount_pct, terminal_pct, shares_cr, years=5):
    """Simplified equity FCF DCF: assumes input is FCFE, not CFO or FCFF."""
    if not all(np.isfinite(x) for x in (starting_fcf_cr, growth_pct, discount_pct, terminal_pct, shares_cr)):
        return np.nan
    if shares_cr <= 0 or discount_pct <= terminal_pct or starting_fcf_cr <= 0:
        return np.nan
    g, r, t = growth_pct / 100, discount_pct / 100, terminal_pct / 100
    pv = sum(starting_fcf_cr * (1+g)**yr / (1+r)**yr for yr in range(1, years+1))
    terminal = starting_fcf_cr * (1+g)**years * (1+t) / (r-t) / (1+r)**years
    return (pv+terminal)/shares_cr


def pegy(pe, eps_growth_pct, dividend_yield_pct):
    if not all(np.isfinite(x) for x in (pe, eps_growth_pct, dividend_yield_pct)):
        return np.nan
    denom = eps_growth_pct + dividend_yield_pct
    return pe/denom if pe > 0 and denom > 0 else np.nan


def aligned_annual(frame, patterns):
    """Annual rows with date-labelled columns, newest year last."""
    values = annual_values(frame, patterns)
    def year(label):
        m = re.search(r'(?:Mar\s*|FY)?(20\d{2}|\d{2})', str(label), re.I)
        if not m:
            return -1
        y = int(m.group(1))
        return y + 2000 if y < 100 else y
    return values.reindex(sorted(values.index, key=year))


def latest(series):
    values = series.dropna()
    return float(values.iloc[-1]) if len(values) else np.nan


def derive_fundamentals(tables):
    """Derive only identifiable financial inputs. Never treat all investing CF as capex."""
    pl = tables.get('Profit & Loss')
    cf = tables.get('Cash Flows')
    bs = tables.get('Balance Sheet')
    sales = aligned_annual(pl, [r'^Sales\s*\+?$', r'^Revenue'])
    profit = aligned_annual(pl, [r'^Net Profit\s*\+?$'])
    eps = aligned_annual(pl, [r'^EPS in Rs', r'^EPS'])
    cfo = aligned_annual(cf, [r'^Cash from Operating Activit'])
    # A dedicated capex line is required; Screener's summary investing cash flow is NOT capex.
    capex = aligned_annual(cf, [r'^Purchase of (?:Fixed Assets|Property)', r'^Capital Expenditure', r'^Purchase of PPE'])
    equity_capital = aligned_annual(bs, [r'^Equity Capital\s*\+?$'])
    out = {'sales_cr': latest(sales), 'net_profit_cr': latest(profit),
           'eps_inr': latest(eps), 'cfo_cr': latest(cfo),
           'revenue_cagr_5y_pct': cagr(sales), 'profit_cagr_5y_pct': cagr(profit),
           'eps_cagr_5y_pct': cagr(eps), 'capex_cr': np.nan,
           'fcf_proxy_cr': np.nan, 'shares_cr': np.nan, 'shares_method': 'Unavailable'}
    if len(capex):
        cap = latest(capex)
        out['capex_cr'] = abs(cap)
        if np.isfinite(out['cfo_cr']):
            out['fcf_proxy_cr'] = out['cfo_cr'] - abs(cap)
    # Net profit / EPS can imply weighted-average shares, not current diluted shares.
    # Do not silently use this estimate in the DCF denominator.
    if np.isfinite(out['net_profit_cr']) and np.isfinite(out['eps_inr']) and out['eps_inr'] > 0:
        out['implied_weighted_avg_shares_cr'] = out['net_profit_cr'] / out['eps_inr']
    else:
        out['implied_weighted_avg_shares_cr'] = np.nan
    out['equity_capital_cr'] = latest(equity_capital)
    return out


def valuation_row(symbol, data, assumptions, overrides):
    metrics = derive_fundamentals(data['tables'])
    price = float(overrides.get('price', np.nan))
    shares = float(overrides.get('shares', np.nan))
    fcfe = float(overrides.get('fcfe', np.nan))
    pe = price / metrics['eps_inr'] if price > 0 and np.isfinite(metrics['eps_inr']) and metrics['eps_inr'] > 0 else np.nan
    growth = float(overrides.get('growth', np.nan))
    dividend = float(overrides.get('dividend', np.nan))
    g, r, t = assumptions
    fair = dcf_per_share(fcfe, g, r, t, shares)
    return {'Symbol': symbol, 'Price ₹': price, 'EPS ₹': metrics['eps_inr'],
            'P/E': pe, 'EPS CAGR 5Y %': metrics['eps_cagr_5y_pct'],
            'PEG': pe/growth if np.isfinite(pe) and np.isfinite(growth) and growth>0 else np.nan,
            'PEGY': pegy(pe, growth, dividend), 'FCF proxy ₹ Cr': metrics['fcf_proxy_cr'],
            'DCF intrinsic ₹': fair, 'Margin of safety %': 100*(fair-price)/fair if np.isfinite(fair) and fair>0 and price>0 else np.nan,
            'Buy @25% MOS ₹': fair*.75 if np.isfinite(fair) else np.nan,
            'Data retrieved UTC': data['retrieved_utc'], 'Source': data['url']}


def _finite_positive(value):
    try:
        v = float(value)
        return v if np.isfinite(v) and v > 0 else np.nan
    except (ValueError, TypeError):
        return np.nan


def _yahoo_cashflow_row(frame, names):
    if frame is None or frame.empty:
        return pd.Series(dtype=float)
    for name in names:
        matches = [i for i in frame.index if str(i).lower().replace(' ', '') == name.lower().replace(' ', '')]
        if matches:
            values = pd.to_numeric(frame.loc[matches[0]], errors='coerce').dropna()
            return values.sort_index()  # oldest to newest
    return pd.Series(dtype=float)


@st.cache_data(ttl=21600, show_spinner=False)
def fetch_market_financials(symbol):
    """Yahoo supplemental fields; amounts converted INR to INR crore.

    Never silently substitute investing cash flow for capex, or Yahoo currency
    amounts denominated in currencies other than INR.
    """
    import yfinance as yf
    ticker = yf.Ticker(f'{symbol}.NS')
    info = ticker.info or {}
    currency = str(info.get('currency', '')).upper()
    if currency != 'INR':
        raise ValueError(f'Yahoo quote currency is {currency or "unknown"}, not INR.')
    price = _finite_positive(info.get('currentPrice'))
    if not np.isfinite(price):
        price = _finite_positive(info.get('regularMarketPrice'))
    shares = _finite_positive(info.get('sharesOutstanding'))
    shares_cr = shares / 1e7 if np.isfinite(shares) else np.nan
    div = info.get('dividendYield')
    # Yahoo dividendYield is expressed in percentage points (e.g. 2.5 = 2.5%).
    dividend_pct = float(div) if div is not None and np.isfinite(float(div)) and float(div) >= 0 else np.nan
    # Read quote-level multiples independently of financial statement availability.
    quote_fields = {}
    for label, keys in {
        'trailing_pe': ('trailingPE',), 'forward_pe': ('forwardPE',),
        'price_to_book': ('priceToBook',), 'price_to_sales': ('priceToSalesTrailing12Months',),
        'ev_ebitda': ('enterpriseToEbitda',), 'peg_ratio': ('trailingPegRatio', 'pegRatio'),
        'market_cap_cr': ('marketCap',), 'book_value': ('bookValue',),
        'roe_pct': ('returnOnEquity',), 'operating_margin_pct': ('operatingMargins',),
        'net_margin_pct': ('profitMargins',), 'revenue_growth_pct': ('revenueGrowth',),
    }.items():
        value = np.nan
        for key in keys:
            try:
                candidate = float(info.get(key))
                if np.isfinite(candidate):
                    value = candidate
                    break
            except (ValueError, TypeError):
                pass
        if label == 'market_cap_cr' and np.isfinite(value):
            value /= 1e7
        if label.endswith('_pct') and np.isfinite(value):
            value *= 100  # Yahoo represents these as fractions.
        quote_fields[label] = value
    try:
        cashflow = ticker.cashflow
    except Exception:
        cashflow = pd.DataFrame()
    cfo = _yahoo_cashflow_row(cashflow, ['Operating Cash Flow', 'Total Cash From Operating Activities'])
    capex = _yahoo_cashflow_row(cashflow, ['Capital Expenditure', 'Capital Expenditures'])
    common = cfo.index.intersection(capex.index)
    fcf = pd.Series(dtype=float)
    if len(common):
        fcf = (cfo.loc[common] - capex.loc[common].abs()) / 1e7
        fcf = fcf.replace([np.inf, -np.inf], np.nan).dropna()
    return {'price': price, 'shares_cr': shares_cr, 'dividend_pct': dividend_pct,
            'fcf_history_cr': fcf, 'cfo_history_cr': cfo / 1e7,
            'capex_history_cr': capex.abs() / 1e7,
            'source': 'Yahoo Finance (.NS)', 'currency': currency, 'quote_fields': quote_fields}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_nse_quote(symbol):
    """Best-effort public NSE equity quote; never evade access controls."""
    from india_valuation_reference import normalize_symbol
    sym = normalize_symbol(symbol).removesuffix('.NS')
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; ResearchDashboard/1.0)',
                            'Accept': 'application/json,text/plain,*',
                            'Referer': 'https://www.nseindia.com/get-quotes/equity?symbol=' + quote(sym)})
    response = session.get('https://www.nseindia.com/api/quote-equity',
                           params={'symbol': sym}, timeout=12)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not payload.get('info'):
        raise ValueError('NSE did not return a valid equity quote.')
    price_info = payload.get('priceInfo') or {}
    metadata = payload.get('metadata') or {}
    def numeric(*values):
        for value in values:
            try:
                value = float(str(value).replace(',', ''))
                if np.isfinite(value) and value > 0:
                    return value
            except (TypeError, ValueError):
                pass
        return np.nan
    return {'price': numeric(price_info.get('lastPrice'), metadata.get('lastPrice')),
            'trailing_pe': numeric(metadata.get('pdSymbolPe'), metadata.get('pe')),
            'industry_pe': numeric(metadata.get('pdSectorPe')),
            'source': 'NSE India (public equity quote)',
            'retrieved_utc': datetime.now(timezone.utc).isoformat()}


def _screener_quote_fields(html):
    """Parse published top-ratio labels, never infer unavailable values."""
    from lxml import html as lxml_html
    root = lxml_html.fromstring(html)
    fields = {}
    mapping = {'stock p/e': 'trailing_pe', 'p/e': 'trailing_pe',
               'book value': 'book_value', 'dividend yield': 'dividend_pct',
               'roe': 'roe_pct', 'roce': 'roce_pct', 'market cap': 'market_cap_cr'}
    for node in root.xpath('//*[@id="top-ratios"]//li'):
        text = ' '.join(node.itertext())
        text = re.sub(r'\s+', ' ', text).strip()
        for label, key in mapping.items():
            if re.match(re.escape(label) + r'\b', text, flags=re.I):
                tail = text[len(label):]
                match = re.search(r'-?\d[\d,]*(?:\.\d+)?', tail)
                if match:
                    value = number(match.group())
                    if np.isfinite(value):
                        fields[key] = value
                break
    return fields


def choose_valuation_fields(nse, screener, yahoo):
    """Per-metric NSE > Screener > Yahoo; no fake substitutes."""
    keys = ('price', 'trailing_pe', 'industry_pe', 'forward_pe', 'price_to_book',
            'price_to_sales', 'ev_ebitda', 'peg_ratio', 'roe_pct', 'roce_pct',
            'operating_margin_pct', 'net_margin_pct', 'revenue_growth_pct',
            'dividend_pct', 'book_value', 'market_cap_cr')
    selected, provenance, missing = {}, {}, {}
    yq = yahoo.get('quote_fields', {})
    for key in keys:
        sources = [('NSE India', nse.get(key)), ('Screener', screener.get(key)),
                   ('Yahoo Finance', yahoo.get(key) if key in ('price', 'dividend_pct') else yq.get(key))]
        value, origin = np.nan, None
        for name, candidate in sources:
            try:
                candidate = float(candidate)
                if np.isfinite(candidate) and (candidate > 0 or (key.endswith('_pct') and candidate == 0)):
                    value, origin = candidate, name
                    break
            except (TypeError, ValueError):
                continue
        selected[key] = value
        provenance[key] = origin or 'N/A'
        if origin is None:
            missing[key] = 'Not supplied by accessible NSE, Screener or Yahoo data.'
    return selected, provenance, missing


def automatic_assessment(tables, market):
    """Fully calculated where sources support inputs; otherwise return N/A.

    CFO minus capex is a levered-cash-flow proxy, not validated FCFE.
    DCF is explicitly labelled provisional, not a verified fair value.
    """
    metrics = derive_fundamentals(tables)
    price = _finite_positive(market.get('price'))
    shares = _finite_positive(market.get('shares_cr'))
    dividend = market.get('dividend_pct', np.nan)
    eps = _finite_positive(metrics['eps_inr'])
    pe = price / eps if np.isfinite(price) and np.isfinite(eps) else np.nan
    if not np.isfinite(pe):
        pe = _finite_positive(market.get('quote_fields', {}).get('trailing_pe'))
    growth = metrics['eps_cagr_5y_pct']
    peg = pe / growth if np.isfinite(pe) and np.isfinite(growth) and growth > 0 else np.nan
    if not np.isfinite(peg):
        peg = _finite_positive(market.get('quote_fields', {}).get('peg_ratio'))
    pegy_value = pegy(pe, growth, dividend)
    industry_pe = peer_median_pe(tables)
    history = market.get('fcf_history_cr', pd.Series(dtype=float)).dropna()
    positive = history[history > 0]
    # Use the full available cash-flow history, not only profitable years.
    normalized = float(history.tail(5).mean()) if len(history) >= 3 else np.nan
    if not np.isfinite(normalized) or normalized <= 0:
        normalized = np.nan
    scenarios = [('Bear', 0.0, 12.0, 2.0), ('Base', 3.0, 11.0, 3.0), ('Bull', 5.0, 10.0, 3.5)]
    rows = []
    for label, g, r, t in scenarios:
        fair = dcf_per_share(normalized, g, r, t, shares)
        mos = 100 * (fair - price) / fair if np.isfinite(fair) and fair > 0 and np.isfinite(price) else np.nan
        rows.append({'Scenario': label, 'FCF Growth %': g, 'Discount Rate %': r,
                     'Terminal Growth %': t, 'Intrinsic Value ₹': fair,
                     'Margin of Safety %': mos,
                     'Buy Price @ 25% MOS ₹': fair * .75 if np.isfinite(fair) else np.nan})
    return {'metrics': metrics, 'price': price, 'shares_cr': shares,
            'dividend_pct': dividend, 'pe': pe, 'industry_pe': industry_pe, 'peg': peg, 'pegy': pegy_value,
            'eps_growth_pct': growth, 'normalized_fcf_cr': normalized,
            'fcf_years': len(history), 'scenarios': pd.DataFrame(rows)}


def _display(value, kind='number'):
    if value is None or not np.isfinite(value):
        return 'N/A'
    if kind == 'inr':
        return f'₹{value:,.2f}'
    if kind == 'crore':
        return f'₹{value:,.0f} Cr'
    if kind == 'pct':
        return f'{value:,.2f}%'
    return f'{value:,.2f}'


def _format_table(df):
    configs = {}
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        if '₹ Cr' in col or '₹ crore' in col:
            fmt = '₹%.0f Cr'
        elif '₹' in col:
            fmt = '₹%.2f'
        elif '%' in col:
            fmt = '%.2f%%'
        else:
            fmt = '%.2f'
        configs[col] = st.column_config.NumberColumn(col, format=fmt)
    st.dataframe(df, column_config=configs, use_container_width=True, hide_index=True)


def render_watchlist_valuation(watchlist):
    st.title('Fundamental Valuation Intelligence')
    st.caption('INDIA PORTFOLIO  /  WATCHLIST  /  VALUATION  •  v3.6.16')
    st.markdown('**Understand what a business may be worth — and how that compares with its market price.**')
    st.info('Per-field source priority: NSE India → Screener → Yahoo Finance. Unavailable fields remain N/A with source diagnostics. NSE access can be restricted.')
    symbols = watchlist['Symbol'].dropna().astype(str).unique().tolist() if not watchlist.empty else []
    if not symbols:
        st.warning('Your watchlist is empty. Add a company in the Watchlist tab to begin.')
        return
    st.session_state.setdefault('india_valuation_cache', {})
    st.session_state.setdefault('india_auto_valuation_cache', {})
    left, right = st.columns([3, 1], vertical_alignment='bottom')
    symbol = left.selectbox('Select a watchlist company', symbols, key='valuation_symbol')
    run = right.button('Analyze company', type='primary', use_container_width=True, key='auto_analyze_company')
    st.caption(f'Consolidated financial statements: {company_url(symbol)}')
    if run:
        # Market quotes and consolidated statements are independent: a blocked
        # Screener request must not hide otherwise available Yahoo valuation.
        data = None
        market = None
        nse = {}
        errors = []
        with st.spinner(f'Collecting available {symbol} valuation data…'):
            try:
                nse = fetch_nse_quote(symbol)
            except Exception as exc:
                errors.append(f'NSE quote unavailable: {exc}')
            try:
                data = fetch_company(symbol)
            except Exception as exc:
                errors.append(f'Consolidated statements unavailable: {exc}')
            try:
                market = fetch_market_financials(symbol)
            except Exception as exc:
                errors.append(f'Yahoo market data unavailable: {exc}')
            if data is not None or market is not None or nse:
                data = data or {'url': '', 'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'tables': {}}
                market = market or {'price': np.nan, 'shares_cr': np.nan,
                                    'dividend_pct': np.nan, 'fcf_history_cr': pd.Series(dtype=float),
                                    'source': 'Unavailable', 'quote_fields': {}}
                chosen, provenance, missing = choose_valuation_fields(nse, data.get('quote_fields', {}), market)
                market['price'] = chosen['price']
                market['dividend_pct'] = chosen['dividend_pct']
                market['quote_fields'] = {**market.get('quote_fields', {}), **chosen}
                analysis = automatic_assessment(data['tables'], market)
                if np.isfinite(chosen['trailing_pe']):
                    analysis['pe'] = chosen['trailing_pe']
                if np.isfinite(chosen['industry_pe']):
                    analysis['industry_pe'] = chosen['industry_pe']
                analysis['provenance'] = provenance
                analysis['missing'] = missing
                st.session_state['india_valuation_cache'][symbol] = data
                st.session_state['india_auto_valuation_cache'][symbol] = {
                    'market': market, 'analysis': analysis, 'errors': errors}
            else:
                st.error('Both data sources failed. No financial figures have been invented.')
        for err in errors:
            st.warning(err)
    data = st.session_state['india_valuation_cache'].get(symbol)
    cached = st.session_state['india_auto_valuation_cache'].get(symbol)
    if data is None or cached is None:
        st.info('Select a company and choose **Analyze company**. Missing fields remain N/A.')
        return
    analysis = cached['analysis']
    market = cached['market']
    metrics = analysis['metrics']
    st.divider()
    st.subheader(f'{symbol} · Valuation at a glance')
    a, b, c, d = st.columns(4)
    base = analysis['scenarios'].iloc[1]
    a.metric('Reference Price', _display(analysis['price'], 'inr'))
    b.metric('Base DCF · provisional', _display(base['Intrinsic Value ₹'], 'inr'))
    c.metric('Margin of Safety', _display(base['Margin of Safety %'], 'pct'))
    d.metric('25% MOS Buy Price', _display(base['Buy Price @ 25% MOS ₹'], 'inr'))
    if not np.isfinite(base['Intrinsic Value ₹']):
        st.warning('DCF unavailable: at least 3 comparable annual CFO and capex observations, a positive normalized cash flow, a valid current share count, and a valid price are needed. Missing values are never estimated silently.')
    else:
        st.warning('**Provisional DCF:** Based on historical CFO − capital expenditure, used as a cash-flow proxy. This is not fully reconciled FCFE or a verified intrinsic value; financing cash flows and other adjustments may be material.')
    st.caption(f"Financial statements: {'Screener consolidated' if data['tables'] else 'N/A'} · Quote priority: NSE → Screener → Yahoo · Cash flow: {market['source']} · Retrieved {data['retrieved_utc'][:16]} UTC · Currency: INR · Statement values: ₹ crore")
    st.markdown('#### Valuation multiples')
    p, q, r, t, u = st.columns(5)
    p.metric('Company P/E', _display(analysis['pe']))
    q.metric('Industry P/E · peer median', _display(analysis['industry_pe']))
    r.metric('PEG · 5Y historical', _display(analysis['peg']))
    t.metric('PEGY · 5Y historical', _display(analysis['pegy']))
    u.metric('Dividend Yield', _display(analysis['dividend_pct'], 'pct'))
    st.caption('Industry P/E is shown only when Screener publishes a peer-table median P/E; it represents the listed peer group, not necessarily the entire industry. N/A means the median was not available.')
    st.caption('PEG = P/E ÷ EPS CAGR (%). PEGY = P/E ÷ [EPS CAGR (%) + dividend yield (%)]. Historical growth is not a forecast. Negative or zero denominators return N/A.')
    st.markdown('#### Additional valuation & quality indicators · NSE → Screener → Yahoo')
    quote = market.get('quote_fields', {})
    # Do not mix Yahoo's trailing P/E with statement-derived P/E without provenance.
    items = [
        ('Trailing P/E', 'trailing_pe', 'Lower may mean cheaper; compare with growth.'),
        ('Forward P/E', 'forward_pe', 'Lower may mean cheaper; forecast-dependent.'),
        ('Price / Book', 'price_to_book', 'Lower may mean cheaper; sector-dependent.'),
        ('EV / EBITDA', 'ev_ebitda', 'Lower may mean cheaper; compare peers.'),
        ('Price / Sales', 'price_to_sales', 'Lower may mean cheaper; check margins.'),
        ('PEG (Yahoo)', 'peg_ratio', 'Lower may mean cheaper; growth-dependent.'),
        ('ROE', 'roe_pct', 'Higher generally better; check leverage.'),
        ('Operating Margin', 'operating_margin_pct', 'Higher generally better.'),
        ('Net Margin', 'net_margin_pct', 'Higher generally better.'),
        ('Revenue Growth', 'revenue_growth_pct', 'Higher generally better if sustainable.'),
    ]
    for offset in range(0, len(items), 5):
        cols = st.columns(5)
        for col, (label, key, hint) in zip(cols, items[offset:offset+5]):
            value = quote.get(key, np.nan)
            col.metric(label, _display(value, 'pct' if key.endswith('_pct') else 'number'))
            col.caption(f"{hint} · Source: {analysis['provenance'].get(key, 'N/A')}")
    st.caption('Priority: NSE India → Screener → Yahoo Finance, per metric. N/A = not supplied or invalid. ' 
               'Ratios are not guaranteed to use the same reporting period as Screener statements. ' 
               'A lower valuation multiple does not by itself imply undervaluation.')
    with st.expander('Data sources and why values are N/A'):
        st.dataframe(pd.DataFrame([{'KPI': key.replace('_', ' ').title(), 'Source': analysis['provenance'][key], 'Status': analysis['missing'].get(key, 'Available')} for key in analysis['provenance']]), hide_index=True, use_container_width=True)
        for err in cached.get('errors', []):
            st.caption(err)
        st.caption('DCF additionally needs at least three aligned cash-flow years and valid shares. NSE may block automated requests. No access-control bypass is attempted.')
    with st.expander('Definitions & how to read valuation KPIs'):
        st.markdown("""**P/E:** Price ÷ earnings per share. **Forward P/E:** price ÷ forecast earnings.

**P/B:** Price ÷ book value per share. **P/S:** market value ÷ annual sales.

**EV/EBITDA:** enterprise value ÷ earnings before interest, taxes, depreciation and amortization.

**PEG:** P/E relative to earnings growth; definitions vary by provider.

**ROE:** net profit ÷ equity. **Operating margin:** operating income ÷ sales.

**Net margin:** net income ÷ sales. **Revenue growth:** change in sales over the comparison period.

**Simple reading:** Profitability/growth ↑ generally good; valuation multiples ↑ can mean more expensive. Always compare within the same industry.""")
    st.markdown('#### DCF scenarios · estimated value per share')
    _format_table(analysis['scenarios'])
    with st.expander('How the DCF is calculated · assumptions and limitations'):
        st.markdown("""**Cash flow:** Mean of up to five available annual CFO minus capital expenditure observations, requiring at least three years. Negative years are included. This is a **proxy**, not audited FCFE.

**Projection:** Five years of annual cash flow, plus a perpetuity terminal value, discounted using a scenario cost of equity.

**Bear:** 0% growth / 12% discount / 2% terminal. **Base:** 3% / 11% / 3%. **Bull:** 5% / 10% / 3.5%.

**Intrinsic value:** Present value of cash flows divided by Yahoo-reported shares outstanding. **Margin of safety:** (intrinsic value − reference price) / intrinsic value × 100. **25% MOS buy price:** intrinsic value × 0.75.

This model is inappropriate for many banks, NBFCs and firms with nonrepresentative cash flows. No model output should be interpreted as a price forecast.""")
    st.markdown('#### Business fundamentals · consolidated')
    fundamental_rows = pd.DataFrame([
        {'Metric': 'Revenue', 'Latest': metrics['sales_cr'], 'Five-Year CAGR %': metrics['revenue_cagr_5y_pct'], 'Unit': '₹ crore'},
        {'Metric': 'Net Profit', 'Latest': metrics['net_profit_cr'], 'Five-Year CAGR %': metrics['profit_cagr_5y_pct'], 'Unit': '₹ crore'},
        {'Metric': 'EPS', 'Latest': metrics['eps_inr'], 'Five-Year CAGR %': metrics['eps_cagr_5y_pct'], 'Unit': '₹ / share'},
        {'Metric': 'Operating Cash Flow', 'Latest': metrics['cfo_cr'], 'Five-Year CAGR %': np.nan, 'Unit': '₹ crore'},
    ])
    _format_table(fundamental_rows)
    x, y, z = st.columns(3)
    x.metric('Normalized FCF proxy', _display(analysis['normalized_fcf_cr'], 'crore'))
    y.metric('Annual cash-flow observations', str(analysis['fcf_years']))
    z.metric('Shares outstanding', _display(analysis['shares_cr'], 'number') + ' Cr' if np.isfinite(analysis['shares_cr']) else 'N/A')
    st.caption('For financial companies, CFO and capex may not reflect distributable equity cash flows. Use sector-specific models instead.')
    st.markdown('#### Watchlist comparison · analyzed companies')
    comparison = []
    for sym in symbols:
        item = st.session_state['india_auto_valuation_cache'].get(sym)
        if not item:
            continue
        a = item['analysis']; base_case = a['scenarios'].iloc[1]
        comparison.append({'Symbol': sym, 'Price ₹': a['price'], 'Base DCF ₹': base_case['Intrinsic Value ₹'],
                           'Margin of Safety %': base_case['Margin of Safety %'],
                           '25% MOS Buy Price ₹': base_case['Buy Price @ 25% MOS ₹'],
                           'Company P/E': a['pe'], 'Industry P/E · peer median': a['industry_pe'], 'PEG': a['peg'], 'PEGY': a['pegy'],
                           'Dividend Yield %': a['dividend_pct'], 'EPS CAGR 5Y %': a['eps_growth_pct']})
    if comparison:
        comp = pd.DataFrame(comparison)
        _format_table(comp)
        st.download_button('Export comparison CSV', comp.to_csv(index=False).encode(),
                           file_name='india_watchlist_valuation_v3_5_3.csv', mime='text/csv')
    st.markdown('#### Source statements · audit trail')
    for name, frame in data['tables'].items():
        with st.expander(name):
            st.dataframe(frame, use_container_width=True, hide_index=True)
    st.caption('Collection is per-company, initiated by you. Bulk scraping and scheduled requests are not enabled; verify website terms and financial results against official filings.')
