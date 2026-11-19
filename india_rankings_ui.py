"""Dark-mode India sector × factor overlap explorer and transparent membership rankings.

Only reads GitHub-Actions-generated CSVs; no synchronous NSE/Yahoo requests.
Financial data is shown as a separate research context, never used to award
constituent membership points, and is not presented as official NSE fundamentals.
"""
from __future__ import annotations

from html import escape
from pathlib import Path
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data' / 'india_holdings'
FINANCIALS = ROOT / 'data' / 'india_financials'


def _mtime(path: Path) -> int:
    return path.stat().st_mtime_ns if path.is_file() else 0


@st.cache_data(show_spinner=False, max_entries=20)
def _load_csv(path: str, mtime_ns: int) -> pd.DataFrame:
    if not Path(path).is_file():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _get(path: Path) -> pd.DataFrame:
    return _load_csv(str(path), _mtime(path))


def _to_numeric(frame: pd.DataFrame, columns: list[str]):
    for col in columns:
        if col in frame:
            frame[col] = pd.to_numeric(frame[col], errors='coerce')
    return frame


def _style():
    st.markdown("""<style>
    .iol-kicker {color:#54c1ed;font-size:.75rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase}
    .iol-title {color:#eff7ff;font-size:2rem;font-weight:800;letter-spacing:-.025em;margin:3px 0}
    .iol-sub {color:#a7bbd5;font-size:.9rem;margin:4px 0 16px}
    .iol-panel {background:#132136;border:1px solid #2c415b;border-radius:11px;padding:13px 17px;margin:9px 0}
    .iol-small {color:#a9bdd8;font-size:.82rem}
    [data-testid="stDataFrame"] {border:1px solid #30435b;border-radius:9px;overflow:hidden}
    </style>""", unsafe_allow_html=True)


def _report_date(records: pd.DataFrame) -> str:
    if records.empty or 'source_latest_utc' not in records:
        return 'Unknown'
    stamps = sorted(str(v) for v in records['source_latest_utc'] if v)
    return stamps[-1][:16].replace('T', ' ') + ' UTC' if stamps else 'Unknown'


def _prepare_rankings(frame: pd.DataFrame) -> pd.DataFrame:
    return _to_numeric(frame.copy(), [
        'factor_score', 'sector_score', 'combined_score',
        'factor_rank', 'sector_rank', 'combined_rank',
        'factor_family_count', 'factor_index_count', 'repeat_factor_memberships',
        'repeat_confirmed_families', 'sector_group_count', 'sector_index_count',
        'thematic_index_count', 'index_count', 'known_weight_entries', 'factor_and_sector',
    ])


def _rank_table(df: pd.DataFrame, axis: str, context: pd.DataFrame):
    axes = {
        'Combined': ('combined_score', 'combined_rank', 'Both factor and sector/theme membership confirmed'),
        'Factor': ('factor_score', 'factor_rank', 'At least one selected NSE factor index'),
        'Sector': ('sector_score', 'sector_rank', 'At least one sector or thematic index'),
    }
    score, rank, description = axes[axis]
    st.caption(description + ' · Scores represent *membership breadth*, not investment performance.')
    c1, c2, c3, c4 = st.columns([2.0, 1.3, 1.35, 1.0])
    search = c1.text_input('Company, symbol or ISIN', key=f'iol_find_{axis}', placeholder='e.g. RELIANCE')
    families = sorted({f.strip() for v in df['factor_families'] for f in v.split('|') if f.strip()})
    selected_family = c2.selectbox('Factor family', ['All factors'] + families, key=f'iol_family_{axis}')
    sector_groups = sorted({f.strip() for v in df['sector_groups'] for f in v.split('|') if f.strip()})
    selected_group = c3.selectbox('Sector / theme group', ['All groups'] + sector_groups, key=f'iol_group_{axis}')
    max_rows = c4.selectbox('Show', [20, 50, 100, 'All'], key=f'iol_max_{axis}')
    filtered = df[df[score].notna()].copy()
    if search.strip():
        query = search.lower().strip()
        filtered = filtered[(filtered['company_name'].str.lower().str.contains(query, regex=False))
                            | (filtered['symbol'].str.lower().str.contains(query, regex=False))
                            | (filtered['isin'].str.lower().str.contains(query, regex=False))]
    if selected_family != 'All factors':
        filtered = filtered[filtered['factor_families'].str.split(' | ', regex=False).apply(lambda x: selected_family in x)]
    if selected_group != 'All groups':
        filtered = filtered[filtered['sector_groups'].str.split(' | ', regex=False).apply(lambda x: selected_group in x)]
    filtered = filtered.sort_values([rank, 'factor_family_count', 'symbol'],
                                    ascending=[True, False, True], kind='stable')
    st.caption(f'{len(filtered):,} companies match the filters. Missing membership is not represented as a score of zero.')
    if filtered.empty:
        st.info('No companies match this filter. Try a different factor or sector group.')
        return
    if max_rows != 'All':
        visible = filtered.head(max_rows)
    else:
        visible = filtered
    basic = {
        rank: 'Rank', 'symbol': 'NSE Symbol', 'company_name': 'Company',
        score: f'{axis} indicator / 100', 'factor_family_count': 'Factor families',
        'repeat_factor_memberships': 'Repeat factor confirmations',
        'sector_group_count': 'Distinct sector/theme groups',
        'factor_families': 'Factor families observed', 'sector_groups': 'Sector / theme groups',
        'factor_universes': 'Factor · parent universe',
    }
    fields = [key for key in basic if key in visible.columns]
    st.dataframe(visible[fields].rename(columns=basic), use_container_width=True,
                 hide_index=True, height=445)
    st.download_button(f'⬇ Export {axis.lower()} ranking (filtered full result)',
                       filtered.to_csv(index=False).encode('utf-8'),
                       file_name=f'india_{axis.lower()}_membership_rankings.csv', mime='text/csv',
                       key=f'iol_export_{axis}')
    chart = filtered.head(16).sort_values(score)
    if len(chart):
        fig = go.Figure(go.Bar(x=chart[score], y=chart['symbol'], orientation='h',
                               marker_color='#4bb8e8', customdata=chart['company_name'],
                               hovertemplate='%{customdata}<br>Indicator: %{x:.1f}<extra></extra>'))
        fig.update_layout(title=f'Top {axis.lower()} membership indicators',
                          paper_bgcolor='#0b1220', plot_bgcolor='#132136',
                          font_color='#e7eef9', height=440,
                          xaxis=dict(range=[0, 102], title='Index-membership indicator (0–100)'),
                          margin=dict(l=12, r=24, t=50, b=45), showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with st.expander('Financial context for displayed companies (separate from ranking)', expanded=False):
        if context.empty or 'company_key' not in context:
            st.info('No Indian Yahoo financial snapshots available yet. The rankings require only NSE index constituent snapshots.')
        else:
            fields = ['company_key', 'income_period', 'revenue_yoy', 'operating_margin',
                      'roe', 'pe', 'retrieved_utc']
            present = [f for f in fields if f in context]
            attached = visible[['symbol', 'company_key', score]].merge(
                context[present].drop_duplicates('company_key'), on='company_key', how='left')
            for field in ('revenue_yoy', 'operating_margin', 'roe'):
                if field in attached:
                    attached[field] = (pd.to_numeric(attached[field], errors='coerce') * 100).round(2)
            st.caption('Yahoo-sourced cached metrics; report dates and statement scope may vary. No financial KPI alters the NSE membership score.')
            st.dataframe(attached.rename(columns={'income_period': 'Annual income period',
                            'revenue_yoy': 'Revenue YoY (%)', 'operating_margin': 'Operating margin (%)',
                            'roe': 'ROE (%)', 'pe': 'P/E', 'retrieved_utc': 'Yahoo retrieved UTC'}),
                         hide_index=True, use_container_width=True, height=325)


def _factor_patterns(patterns: pd.DataFrame, pairs: pd.DataFrame, rows: pd.DataFrame):
    if patterns.empty:
        st.info('Factor overlap exports are not available yet. Run India NSE Constituents Refresh.')
        return
    families = sorted(patterns['factor_family'].unique())
    family = st.selectbox('Factor family', families, key='iol_overlap_family')
    selected = patterns[patterns['factor_family'] == family].copy()
    _to_numeric(selected, ['company_count', 'pattern_size'])
    selected = selected.sort_values(['pattern_size', 'company_count'], ascending=[False, False])
    st.caption('**Exact membership combinations:** each company is counted in exactly one combination within its factor family. '
               'Nifty 50/100/200/500 are parent *universes*, not mutually exclusive cap bands.')
    st.dataframe(selected[['source_indices', 'parent_universes', 'pattern_size',
                           'company_count', 'company_symbols']].rename(columns={
                               'source_indices': 'Selected factor indices',
                               'parent_universes': 'Parent universes',
                               'pattern_size': 'Indices selected',
                               'company_count': 'Companies',
                               'company_symbols': 'NSE symbols',
                           }), hide_index=True, use_container_width=True, height=360)
    if len(selected) > 0:
        fig = go.Figure(go.Bar(x=selected['company_count'].head(12).iloc[::-1],
                               y=selected['source_indices'].head(12).iloc[::-1],
                               orientation='h', marker_color='#58c3d8'))
        fig.update_layout(title=f'{family} · exact cross-index memberships',
                          font_color='#e7eef9', paper_bgcolor='#0b1220',
                          plot_bgcolor='#132136', height=390,
                          margin=dict(l=12, r=15, t=47, b=22),
                          xaxis_title='Unique companies in exact combination')
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    if not pairs.empty:
        related = pairs[pairs['factor_family'] == family].copy()
        if not related.empty:
            st.markdown('##### Pairwise index overlap')
            cols = ['index_a', 'index_b', 'companies_a', 'companies_b',
                    'shared_companies', 'jaccard_pct', 'shared_symbols']
            st.dataframe(related[cols].rename(columns={
                'index_a': 'Index A', 'index_b': 'Index B',
                'companies_a': 'A members', 'companies_b': 'B members',
                'shared_companies': 'Shared', 'jaccard_pct': 'Jaccard overlap (%)',
                'shared_symbols': 'Shared NSE symbols',
            }), hide_index=True, use_container_width=True, height=300)
    st.download_button('⬇ Export factor membership patterns', selected.to_csv(index=False).encode('utf-8'),
                       file_name=f'india_{family.lower().replace(" ", "_")}_patterns.csv', mime='text/csv')
    st.markdown('##### Source index membership matrix')
    all_factor_rows = rows[(rows['category'] == 'Factor') & (rows['factor_family'] == family)].copy()
    if all_factor_rows.empty:
        return
    company_list = sorted(all_factor_rows['company_key'].unique())
    company_symbols = all_factor_rows.drop_duplicates('company_key').set_index('company_key')['symbol'].to_dict()
    matrix = pd.crosstab(all_factor_rows['company_key'], all_factor_rows['index_name']).reindex(company_list, fill_value=0)
    matrix = matrix.clip(upper=1).astype(int)
    matrix.index = [company_symbols.get(key, key) for key in matrix.index]
    matrix.index.name = 'NSE Symbol'
    st.dataframe(matrix.reset_index(), use_container_width=True, height=430, hide_index=True)


def _sector_factor_view(frame: pd.DataFrame, members: pd.DataFrame):
    if frame.empty:
        st.info('No saved NSE sector × factor overlap data.')
        return
    frame = _to_numeric(frame.copy(), ['sector_constituents', 'factor_constituents',
                                       'overlap_companies', 'pct_of_sector'])
    metric = st.radio('Heatmap measure', ['Shared companies', '% of sector constituents'], horizontal=True,
                      key='iol_heat_metric')
    value_key = 'overlap_companies' if metric == 'Shared companies' else 'pct_of_sector'
    pivot = frame.pivot(index='sector_index', columns='factor_family', values=value_key).fillna(0)
    fig = go.Figure(go.Heatmap(z=pivot.values, x=list(pivot.columns), y=list(pivot.index),
                                colorscale=[[0,'#15243a'],[0.5,'#17658d'],[1,'#51c8e8']],
                                colorbar=dict(title='Count' if value_key == 'overlap_companies' else '%'),
                                hovertemplate='Sector/theme: %{y}<br>Factor: %{x}<br>Value: %{z:.1f}<extra></extra>'))
    fig.update_layout(title='Sector / thematic indices × factor families',
                      paper_bgcolor='#0b1220', plot_bgcolor='#132136',
                      font_color='#e7eef9', height=640, margin=dict(l=5, r=10, t=50, b=10),
                      xaxis=dict(side='top'))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    st.caption('Each heatmap cell counts unique securities shared between the NSE index and at least one '
               'index of the selected factor family. Sector indices can overlap: cell totals are not additive.')
    c1, c2 = st.columns(2)
    selected_sector = c1.selectbox('Sector / thematic index', sorted(frame['sector_index'].unique()), key='iol_sector')
    selected_factor = c2.selectbox('Factor family', sorted(frame['factor_family'].unique()), key='iol_factor')
    cell = frame[(frame['sector_index'] == selected_sector) & (frame['factor_family'] == selected_factor)]
    st.markdown('##### Companies in the selected intersection')
    if not cell.empty:
        one = cell.iloc[0]
        st.caption(f"{int(one['overlap_companies'])} unique securities · {float(one['pct_of_sector']):.1f}% of {selected_sector} constituents")
        ids = set(members.loc[(members['index_name'] == selected_sector), 'company_key'])
        ids &= set(members.loc[(members['category'] == 'Factor') &
                               (members['factor_family'] == selected_factor), 'company_key'])
        selected = members[members['company_key'].isin(ids)].drop_duplicates('company_key')
        st.dataframe(selected[['symbol','company_name','isin','industry']].rename(columns={
            'symbol':'NSE Symbol','company_name':'Company','isin':'ISIN','industry':'Industry'}),
            hide_index=True, use_container_width=True, height=310)
    st.download_button('⬇ Export all sector × factor overlap cells', frame.to_csv(index=False).encode('utf-8'),
                       file_name='india_sector_factor_overlap.csv', mime='text/csv')


def _company_evidence(ranking: pd.DataFrame, members: pd.DataFrame):
    if ranking.empty:
        return
    c1, c2 = st.columns([3, 1])
    labels = {r['company_key']: f"{r['symbol']} · {r['company_name']}" for _, r in ranking.iterrows()}
    keys = sorted(labels, key=lambda key: labels[key])
    picked = c1.selectbox('Company evidence / all source memberships', keys,
                          format_func=lambda k: labels[k], key='iol_evidence_company')
    row = ranking[ranking['company_key'] == picked].iloc[0]
    filtered = members[members['company_key'] == picked].copy()
    st.markdown(f"<div class='iol-panel'><b style='font-size:1.15rem;color:#eaf5ff'>{escape(str(row['company_name']))}</b>"
                f"<br><span class='iol-small'>{escape(str(row['symbol']))} · "
                f"{escape(str(row['isin']) or 'ISIN unavailable')}</span></div>", unsafe_allow_html=True)
    tiles = st.columns(3)
    for col, heading, score, rank in zip(tiles, ('Combined', 'Factor', 'Sector'),
                                          ('combined_score','factor_score','sector_score'),
                                          ('combined_rank','factor_rank','sector_rank')):
        s = row[score]
        col.metric(heading + ' membership indicator', 'N/A' if pd.isna(s) else f'{s:.1f} / 100',
                   help=f"Rank: {'N/A' if pd.isna(row[rank]) else int(row[rank])}; ordinal score based only on NSE constituent presence")
    st.caption(f"Factor families: {row['factor_families'] or 'None'} · "
               f"Distinct sector/thematic groups: {row['sector_group_count']} · "
               f"Repeat factor confirmations: {row['repeat_factor_memberships']}")
    cols = ['index_name','category','factor_family','parent_universe','weight_pct','snapshot_utc','source_url']
    table = filtered[[c for c in cols if c in filtered.columns]].copy()
    if 'weight_pct' in table:
        table['weight_pct'] = table['weight_pct'].replace('', 'N/A')
    display_names = {'index_name':'Verified NSE index','category':'Category',
                     'factor_family':'Factor family','parent_universe':'Parent index universe',
                     'weight_pct':'Published weight (%)','snapshot_utc':'Fetched UTC',
                     'source_url':'NSE source file'}
    st.dataframe(table.rename(columns=display_names), use_container_width=True, hide_index=True, height=370,
                 column_config={'NSE source file': st.column_config.LinkColumn('NSE source file', display_text='Open CSV')})
    symbol = str(row['symbol']).strip().upper()
    c1, c2, c3 = st.columns(3)
    if c1.button('📊 Open India Financial KPIs', use_container_width=True, type='primary'):
        st.session_state.india_kpi_reference_symbol = symbol
        st.session_state.selected_page = 'India Company Financial KPI Intelligence'
        st.rerun()
    c2.link_button('↗ Screener consolidated', f'https://www.screener.in/company/{symbol}/consolidated/', use_container_width=True)
    c3.link_button('↗ Yahoo Finance', f'https://finance.yahoo.com/quote/{symbol}.NS/', use_container_width=True)
    st.caption('External provider links are references only; company financials shown in India KPIs may be missing or stale.')


def render_india_overlap_leadership():
    _style()
    st.markdown("<div class='iol-kicker'>India · NSE company membership intelligence</div>"
                "<div class='iol-title'>Sector × Factor Overlap & Leadership</div>"
                "<div class='iol-sub'>Source-backed overlap analysis · transparent membership-only rankings · no assumed constituent weights</div>",
                unsafe_allow_html=True)
    companies = _get(DATA / 'leadership_companies.csv')
    members = _get(DATA / 'constituents.csv')
    patterns = _get(DATA / 'factor_membership_patterns.csv')
    pairs = _get(DATA / 'factor_index_overlaps.csv')
    intersections = _get(DATA / 'sector_factor_overlaps.csv')
    finance = _get(FINANCIALS / 'company_financial_summary.csv')
    if not members.empty and (companies.empty or patterns.empty or pairs.empty or intersections.empty):
        from india_overlap_rankings import build_leadership
        computed = build_leadership(members.to_dict('records'))
        if companies.empty: companies = pd.DataFrame(computed['companies'])
        if patterns.empty: patterns = pd.DataFrame(computed['factor_membership_patterns'])
        if pairs.empty: pairs = pd.DataFrame(computed['factor_index_overlaps'])
        if intersections.empty: intersections = pd.DataFrame(computed['sector_factor_overlaps'])
        st.caption('Overlap tables calculated from saved NSE constituents; no live network access.')
    if companies.empty or members.empty:
        st.warning('No saved NSE overlap/ranking outputs available. First run **India NSE Constituents Refresh** in '
                   'GitHub Actions. It now builds the ranking exports after updating constituents. If constituents.csv '
                   'is already committed, the standalone command is `python scripts/build_india_overlap_rankings.py`.')
        st.caption('This page never makes live NSE or Yahoo requests, so it will not hang while fetching data.')
        return
    requirements = {'company_key','company_name','symbol','factor_score','sector_score',
                    'combined_score','factor_rank','sector_rank','combined_rank',
                    'factor_families','factor_universes','sector_groups'}
    if not requirements.issubset(companies):
        st.error('Saved leadership_companies.csv is missing required fields. Rebuild from your verified NSE constituents.csv.')
        return
    companies = _prepare_rankings(companies)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Unique securities', len(companies))
    m2.metric('Factor members', int(companies['factor_score'].notna().sum()))
    m3.metric('Sector / theme members', int(companies['sector_score'].notna().sum()))
    m4.metric('Factor + sector overlap', int(companies['combined_score'].notna().sum()))
    st.caption(f"Latest collected membership snapshot: {_report_date(companies)}. Source timestamps represent retrieval, not NSE reconstitution effective dates.")
    with st.expander('About membership-based scoring'):
        st.caption('Combined scores require factor and sector membership. Rankings use verified NSE constituent overlap, not portfolio weights or fundamental valuation. Methodology is available in the Methodology tab.')
    tabs = st.tabs(['Combined', 'Factors', 'Sectors', 'Factor Overlap', 'Sector × Factor', 'Company Evidence', 'Methodology'])
    with tabs[0]:
        _rank_table(companies, 'Combined', finance)
    with tabs[1]:
        _rank_table(companies, 'Factor', finance)
    with tabs[2]:
        _rank_table(companies, 'Sector', finance)
    with tabs[3]:
        _factor_patterns(patterns, pairs, members)
    with tabs[4]:
        _sector_factor_view(intersections, members)
    with tabs[5]:
        _company_evidence(companies, members)
    with tabs[6]:
        st.markdown('''### Membership-only research indicators · version 1
**Factor signal (0–100):** 70 points × min(distinct factor families / 4, 1) +
30 points × min(extra same-family index memberships / 3, 1). An index such as
*Nifty50 Equal Weight* is a strategy, not an independent factor: shown for traceability,
excluded from factor scoring.

**Sector/theme signal (0–100):** 65 points for at least one sector/thematic membership,
up to 25 additional points for up to two *additional distinct sector/theme groups*,
and 10 points when sector and thematic memberships are both observed. Nifty Bank,
PSU Bank and Financial Services are one thematic sector-breadth group; Oil & Gas and
Energy are another, preventing artificial inflation from overlapping sector indices.

**Combined signal (0–100):** `0.5 × Factor + 0.5 × Sector − 0.20 × |Factor − Sector|`.
Calculated **only when both signals are supported by actual membership**. Each ranking
is calculated independently. Equal scores receive equal competition ranks.

**What this does *not* imply:** The scores are not an equity fair value,
profitability measurement, ETF capital allocation, index weight, or recommendation.
Missing weights are N/A; no guessed zeros. The Nifty 50/100/200/500 groups are
*overlapping parent universes*, not separate large/mid/small-cap categories.

**Negative points:** In the present 31-source NSE collection, parent index
eligibility is not independently verified. Therefore we give **no negative penalty**
for absence from any related factor index. Exact membership patterns expose the
missing selections, and a future eligibility-verified model can separately evaluate them.

**Financial context:** Cached Yahoo financial KPIs are visible on demand in the
ranking tab but do *not* affect these rankings. Screener links are external; no
Screener data is scraped or republished.

**Freshness:** The page reads committed CSV snapshots. Run **India NSE Constituents
Refresh** to update them and recompute rankings. Raw original memberships remain
available in **India Sector & Factor Holdings**.''')
