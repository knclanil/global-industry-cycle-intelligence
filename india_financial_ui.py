"""Read-only professional India financial research and sector/factor analytics.

NSE = verified constituents. Yahoo Finance = optional cached financial snapshots.
Screener = independent consolidated-report link; not scraped/reproduced.
No rankings, inferred index weights, or synchronous financial API calls.
"""
from __future__ import annotations

from html import escape
from pathlib import Path
import json
import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from india_financial_data import (
    AGGREGATE_FIELDS, DATA, MONEY_METRICS, PERCENT_KPIS, RATIO_KPIS, build_kpis,
    company_file, equity_dcf_proxy, liquidation_proxy, load_company,
    safe_symbol, screener_url, statement_coverage,
)
from research_theme import PLOTLY_LAYOUT, apply_research_theme
from scripts.refresh_india_financials import fetch_yahoo_company

BASE = Path(__file__).resolve().parent
HOLDINGS = BASE / 'data' / 'india_holdings'


def _mtime(path: Path) -> int:
    return path.stat().st_mtime_ns if path.exists() else 0


@st.cache_data(show_spinner=False, max_entries=22)
def _csv(path: str, mtime_ns: int) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _read(directory: Path, filename: str) -> pd.DataFrame:
    path = directory / filename
    return _csv(str(path), _mtime(path))


def _style():
    apply_research_theme()
    st.markdown('''<style>
    .ifr-kicker {font-size:.75rem;letter-spacing:.13em;color:#56c9f4;font-weight:800}
    .ifr-title {font-size:1.75rem;font-weight:800;color:#f0f7ff;letter-spacing:-.025em;margin:0 0 4px}
    .ifr-muted {color:#a7bbd5;font-size:.88rem;margin-bottom:13px}
    .ifr-section {font-size:1rem;font-weight:700;color:#eaf3ff;margin:14px 0 8px}
    .ifr-tile {background:#142137;border:1px solid #2a3c55;border-radius:9px;min-height:72px;padding:9px 11px;margin-bottom:5px}
    .ifr-label {font-size:.72rem;color:#b6c5d9;line-height:1.17}
    .ifr-number {font-size:1.15rem;color:#f1f7ff;font-weight:750;margin-top:7px;white-space:nowrap}
    .ifr-callout {background:#101e32;border:1px solid #29415c;border-radius:10px;padding:10px 15px;color:#abc1da;margin:10px 0;font-size:.83rem}
    @media(max-width:850px) {.ifr-number{font-size:.84rem}.ifr-tile{padding:8px 5px}}
    </style>''', unsafe_allow_html=True)


def _header(kicker: str, title: str, subtitle: str):
    st.markdown(f'<div class="ifr-kicker">{escape(kicker)}</div><div class="ifr-title">{escape(title)}</div>'
                f'<div class="ifr-muted">{escape(subtitle)}</div>', unsafe_allow_html=True)


def _aggregation_table(frame: pd.DataFrame, records: pd.DataFrame, group_type: str, membership_group=''):
    if frame.empty or records.empty:
        st.info('No valid NSE + Yahoo merged data available. Run the two refresh workflows to populate coverage.')
        return
    view = frame[frame['group_type'] == group_type].copy()
    if membership_group:
        pass
    if view.empty:
        st.info('No saved metrics for this grouping.')
        return
    rename = {
        'group_name':'Index / factor family', 'parent_universe':'Parent',
        'constituents':'NSE constituents', 'companies_with_snapshots':'Yahoo snapshots',
        'annual_income_coverage':'Annual income', 'annual_balance_coverage':'Balance sheets',
        'annual_cashflow_coverage':'Cash flows', 'price_coverage':'Market quotes',
        'pct_with_income':'Revenue coverage %',
        'median_revenue_yoy':'Median sales YoY', 'median_operating_margin':'Median operating margin',
        'median_net_margin':'Median net margin', 'median_roe':'Median ROE',
        'median_fcf_margin':'Median FCF margin', 'median_pe':'Median P/E',
        'median_fcf_yield':'Median FCF yield',
    }
    view = view.rename(columns=rename)
    measure_cols = ['Index / factor family','Parent','NSE constituents','Yahoo snapshots','Annual income',
                    'Balance sheets','Cash flows','Market quotes','Revenue coverage %',
                    'Median sales YoY','Median operating margin','Median net margin',
                    'Median ROE','Median FCF margin','Median P/E','Median FCF yield']
    for col in measure_cols[2:]:
        view[col] = pd.to_numeric(view[col], errors='coerce')
    for col in ('Median sales YoY','Median operating margin','Median net margin',
                'Median ROE','Median FCF margin','Median FCF yield'):
        view[col] = view[col] * 100
    st.caption('Unweighted company-level medians · NSE membership-based groups · No holdings weights or company rankings.')
    chart_names = view['Index / factor family'].tolist()
    coverage_values = [100 * a/b if b else 0 for a, b in zip(view['Annual income'], view['NSE constituents'])]
    plot = go.Figure(go.Bar(x=coverage_values, y=chart_names, orientation='h',
                            marker_color='#51b7e8', hovertemplate='%{y}<br>Annual income coverage: %{x:.1f}%<extra></extra>'))
    plot.update_layout(**PLOTLY_LAYOUT)
    plot.update_layout(height=max(245, min(750, 40*len(view))), xaxis_title='Annual income coverage (%)',
                       yaxis=dict(autorange='reversed'), margin=dict(l=8, r=10, t=20, b=30))
    st.plotly_chart(plot, use_container_width=True, config={'displayModeBar': False})
    st.dataframe(view[measure_cols], use_container_width=True, hide_index=True, height=415,
                 column_config={
                     'Revenue coverage %': st.column_config.NumberColumn(format='%.0f%%'),
                     'Median sales YoY': st.column_config.NumberColumn(format='%.2f'),
                     'Median operating margin': st.column_config.NumberColumn(format='%.2f'),
                     'Median net margin': st.column_config.NumberColumn(format='%.2f'),
                     'Median ROE': st.column_config.NumberColumn(format='%.2f'),
                     'Median FCF margin': st.column_config.NumberColumn(format='%.2f'),
                     'Median FCF yield': st.column_config.NumberColumn(format='%.2f'),
                 })
    st.caption('Median percentage columns are displayed as %; P/E is a multiple. Coverage and sample sizes differ across indices.')
    st.download_button('⬇ Export financial aggregation', view.to_csv(index=False).encode('utf-8'),
                       file_name=f'india_{group_type.lower().replace(" ", "_")}_financials.csv', mime='text/csv')


def _group_company_detail(memberships: pd.DataFrame, company_fin: pd.DataFrame, *, label_key='index_name', group=None):
    options = sorted(memberships[label_key].dropna().unique())
    if not options:
        return
    name = st.selectbox('Inspect constituent financials for', options, key='india_group_selector_' + label_key)
    if label_key == 'factor_family':
        selection = memberships[(memberships['category'] == 'Factor') & (memberships[label_key] == name)]
    else:
        selection = memberships[memberships[label_key] == name]
    unique = selection.drop_duplicates('company_key')
    if company_fin.empty or 'company_key' not in company_fin:
        st.info(f'{len(unique)} NSE companies are members; Yahoo financial snapshots are not cached yet.')
        return
    merged = unique[['company_key', 'company_name', 'symbol', 'isin']].merge(company_fin, how='left', on='company_key', suffixes=('', '_y'))
    display = merged[['company_name','symbol','isin','financial_period','revenue_yoy',
                      'operating_margin','net_margin','roe','fcf_margin','pe','retrieved_utc']].copy()
    display.columns = ['Company','NSE Symbol','ISIN','Fiscal period','Revenue YoY','Operating margin',
                       'Net margin','ROE','FCF margin','P/E','Yahoo snapshot UTC']
    st.caption(f'{len(unique):,} verified NSE members · {merged["financial_period"].replace("", pd.NA).notna().sum():,} with annual financial periods.')
    st.dataframe(display, hide_index=True, use_container_width=True, height=365)
    st.download_button('⬇ Download group constituents and KPIs', display.to_csv(index=False).encode('utf-8'),
                       file_name='india_group_constituent_financials.csv', mime='text/csv')
    if len(unique):
        co1, co2 = st.columns([2.1, 1.0])
        chosen_key = co1.selectbox('View financial KPIs for one constituent', list(unique['company_key']),
                                  format_func=lambda k: str(unique.loc[unique['company_key'] == k, 'symbol'].iloc[0]),
                                  key='india_group_drill_' + label_key)
        if co2.button('📊 Open company KPIs', key='india_group_open_' + label_key):
            chosen_symbol = str(unique.loc[unique['company_key'] == chosen_key, 'symbol'].iloc[0]).upper()
            st.session_state.india_kpi_reference_symbol = chosen_symbol
            st.session_state.selected_page = 'India Company Financial KPI Intelligence'
            st.rerun()


def _factor_sector_heatmap(memberships: pd.DataFrame, summary: pd.DataFrame):
    factors = memberships[memberships['category'] == 'Factor']
    sector = memberships[memberships['category'].isin(['Sector','Thematic'])]
    if factors.empty or sector.empty:
        st.info('NSE sector/factor membership data missing.')
        return
    family_members = {f:set(g['company_key']) for f,g in factors.groupby('factor_family')}
    sector_members = {s:set(g['company_key']) for s,g in sector.groupby('index_name')}
    financial_keys = set(summary['company_key']) if 'company_key' in summary else set()
    mode = st.radio('Intersection measure', ['Verified shared constituents','Shared companies with Yahoo snapshots'],
                    horizontal=True, key='india_intersection_measure')
    cells = []
    for s, s_keys in sorted(sector_members.items()):
        row = {'Index':s}
        for f, f_keys in sorted(family_members.items()):
            shared = s_keys & f_keys
            if mode.startswith('Shared companies'):
                shared &= financial_keys
            row[f] = len(shared)
        cells.append(row)
    matrix = pd.DataFrame(cells).set_index('Index')
    fig = go.Figure(go.Heatmap(z=matrix.to_numpy(dtype=int),x=matrix.columns.tolist(),
                y=matrix.index.tolist(),colorscale=[[0,'#12213a'],[0.4,'#226388'],[1,'#47c5eb']],
                text=matrix.astype(str).to_numpy(), texttemplate='%{text}',
                hovertemplate='%{y} × %{x}<br>Companies: %{z}<extra></extra>'))
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(height=max(460, 27*len(matrix)), margin=dict(l=25,r=15,t=15,b=80),
                      xaxis=dict(side='top'))
    st.plotly_chart(fig, use_container_width=True)
    st.caption('Overlap uses unique NSE company identifiers. The second option counts only companies with a saved Yahoo snapshot, not companies meeting any return threshold.')
    st.download_button('⬇ Export intersection matrix', matrix.to_csv().encode('utf-8'),
                       file_name='india_sector_factor_financial_coverage_matrix.csv', mime='text/csv')


def render_india_sector_factor_financials():
    _style()
    _header('INDIA · NSE HOLDINGS × FINANCIALS', 'India Sector & Factor Financial Analysis',
            '31 NSE indices · unique constituents · Yahoo company financials · descriptive group medians, not index returns or rankings')
    memberships = _read(HOLDINGS, 'constituents.csv')
    aggregates = _read(DATA, 'index_financial_summary.csv')
    financials = _read(DATA, 'company_financial_summary.csv')
    companies = _read(HOLDINGS, 'companies.csv')
    if memberships.empty or companies.empty:
        st.warning('NSE constituent data is missing. Run India NSE Constituents Refresh and commit its generated files.')
        return
    count_fin = len(financials)
    counts = st.columns(4)
    counts[0].metric('NSE securities', len(companies))
    counts[1].metric('Verified index memberships', len(memberships))
    counts[2].metric('Yahoo company snapshots', count_fin)
    counts[3].metric('Annual income statements', int((financials['income_period'] != '').sum()) if 'income_period' in financials else 0)
    st.markdown('<div class="ifr-callout">NSE index membership does not provide an allocation weight. '
        'Sector and factor measures below are unweighted company medians, never weighted index fundamentals. '
        'Factor families merge duplicate company memberships across their different Nifty parent universes.</div>',
        unsafe_allow_html=True)
    if aggregates.empty or 'group_type' not in aggregates:
        st.warning('Financial group data has not been built. Run **GitHub Actions → India Company Financials Refresh**, '
                   'or `python scripts/refresh_india_financials.py --rebuild-only` after downloading NSE constituents.')
        return
    tabs = st.tabs(['Sector & thematic', 'Factor families', 'All source indices', 'Sector × factor matrix', 'Coverage & diagnostics'])
    with tabs[0]:
        names = set(memberships.loc[memberships['category'].isin(['Sector','Thematic']),'index_slug'])
        sector_aggs = aggregates[aggregates['index_slug'].isin(names)]
        _aggregation_table(sector_aggs, memberships, 'Index')
        st.markdown('#### Sector constituent-level financials')
        _group_company_detail(memberships[memberships['category'].isin(['Sector','Thematic'])], financials)
    with tabs[1]:
        _aggregation_table(aggregates, memberships, 'Factor Family')
        st.markdown('#### Factor family company KPIs')
        _group_company_detail(memberships[memberships['category'] == 'Factor'], financials, label_key='factor_family')
    with tabs[2]:
        _aggregation_table(aggregates, memberships, 'Index')
        st.markdown('#### Index constituent research')
        _group_company_detail(memberships, financials)
    with tabs[3]:
        _factor_sector_heatmap(memberships, financials)
    with tabs[4]:
        status = _read(DATA, 'refresh_status.csv')
        st.markdown('#### Financial coverage & provider reliability')
        if status.empty:
            st.info('No Yahoo financial refresh has been attempted yet.')
        else:
            fails = status[status['status'] != 'ok']
            if not fails.empty:
                st.warning(f'{len(fails)} companies most recently failed Yahoo collection. Previous valid snapshots, if any, are preserved.')
                st.dataframe(fails, use_container_width=True, hide_index=True, height=340)
            else:
                st.success('No failures recorded in the saved provider status file.')
        st.markdown('**Data sources & limitations**')
        st.markdown('NSE: membership, ISIN, sector/factor index and observed entry/exit events. '
                    'Yahoo Finance via yfinance: annual/quarterly company statements and cached price reference. '
                    'Screener.in: direct consolidated report for independent research, not scraped or republished. '
                    'Unpublished constituent weights remain unknown. Company financials may be standalone or consolidated depending on Yahoo; scope is not assumed.')
        st.caption('GitHub Actions can refresh the full NSE universe (no 25-company limit). For individual company research, use India Company Financial KPI Intelligence.')
