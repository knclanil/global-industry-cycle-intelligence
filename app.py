"""Global Industry Cycle Intelligence | USA sector rotation dashboard."""
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from market_data import SECTORS, LOOKBACKS, QUADRANTS, download, validate, calculate, relative_trend_from_zero

st.set_page_config(page_title='Global Industry Cycle Intelligence', page_icon='🌐', layout='wide')
COLORS = {'Leading': '#22c58b', 'Improving': '#4b9cff', 'Weakening': '#f4aa4b', 'Lagging': '#fa7185'}

st.markdown('''<style>
.stApp{background:#0b1220;color:#e7eef9}
[data-testid="stMetric"]{background:#142137;border:1px solid #2a3c55;border-radius:12px;padding:16px}
[data-testid="stMetricLabel"]{color:#b6c7de}
div[data-testid="stVerticalBlockBorderWrapper"]{border-color:#2a3c55}
</style>''', unsafe_allow_html=True)

# Keep documentation accessible even when market data is unavailable.
page = st.sidebar.radio('NAVIGATION', ['Dashboard', 'Wiki'], index=0)
if page == 'Wiki':
    from pathlib import Path
    st.title('Dashboard Wiki')
    st.caption('Definitions, calculation formulas, controls, data quality and operational details.')
    st.markdown((Path(__file__).resolve().parent / 'WIKI.md').read_text(encoding='utf-8'))
    st.stop()

@st.cache_data(ttl=3600, show_spinner=False)
def prices_cached(start: date, end: date):
    return download(start, end)


def style(fig, height=485):
    fig.update_layout(template='plotly_dark', paper_bgcolor='#142137', plot_bgcolor='#142137',
                      font=dict(color='#dce8f8'), height=height, margin=dict(l=25,r=25,t=28,b=35),
                      legend=dict(orientation='h', y=1.13), hovermode='closest')
    fig.update_xaxes(gridcolor='#26384e', zeroline=False)
    fig.update_yaxes(gridcolor='#26384e', zeroline=False)
    return fig


def set_sector_from_all():
    st.session_state.sectors = list(SECTORS) if st.session_state.all_sectors else []


def sync_all():
    st.session_state.all_sectors = len(st.session_state.sectors) == len(SECTORS)

if 'sectors' not in st.session_state:
    st.session_state.sectors = list(SECTORS)
if 'all_sectors' not in st.session_state:
    st.session_state.all_sectors = True

head, refresh = st.columns([6, 1], vertical_alignment='center')
with head:
    st.title('Global Industry Cycle Intelligence')
    st.caption('USA Sector Rotation  •  11 S&P 500 sectors vs SPY  •  No database')
with refresh:
    if st.button('↻ Refresh now', use_container_width=True):
        prices_cached.clear()
        st.rerun()

with st.container(border=True):
    left, mid, right = st.columns([2.2, 2.6, 2.6])
    with left:
        st.checkbox('Select all sectors', key='all_sectors', on_change=set_sector_from_all)
        chosen = st.multiselect('SECTORS', list(SECTORS), key='sectors',
                                format_func=lambda t: f'{SECTORS[t]} ({t})', on_change=sync_all)
    with mid:
        lookback = st.select_slider('RELATIVE TIME', options=list(LOOKBACKS), value='3M')
        st.caption('Controls the strength/momentum calculation window.')
    with right:
        selected = st.date_input('FROM DATE → TO DATE',
                                 value=(date.today() - timedelta(days=365), date.today()),
                                 min_value=date(2019, 1, 1), max_value=date.today(), format='MM/DD/YYYY')
        st.caption('Controls the displayed history and period returns.')

if not chosen:
    st.info('Select at least one sector.'); st.stop()
if len(selected) != 2:
    st.info('Select both From Date and To Date.'); st.stop()
start, end = selected
if start >= end:
    st.error('From Date must be before To Date.'); st.stop()

# 600 calendar days supports 12M RS + 6M momentum warm-up.
with st.spinner('Retrieving and validating daily US market data…'):
    try:
        frames = prices_cached(start - timedelta(days=600), end)
        report = validate(frames, end)
        if report['status'] == 'FAIL':
            st.error('Data validation failed. Classifications have been withheld.')
            with st.expander('Validation failures', expanded=True):
                for issue in report['errors']: st.write('• ' + issue)
            st.stop()
        rows, strength, momentum, first, last = calculate(frames, chosen, start, end, lookback)
    except Exception as exc:
        st.error(f'Unable to calculate the dashboard: {exc}')
        st.stop()
if rows.empty:
    st.warning('No sector has enough valid observations for the selected settings.'); st.stop()

now_et = datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %I:%M %p ET')
if report['status'] == 'PASS':
    st.success(f'Primary-source validation: PASS  •  Latest verified session: {report["latest"]}  •  Retrieved: {now_et}')
else:
    st.warning(f'Primary-source validation: WARNING  •  Latest session: {report["latest"]}  •  Retrieved: {now_et}')
    with st.expander('Data quality warnings'):
        for issue in report['warnings']: st.write('• ' + issue)
st.caption('Source: Yahoo Finance (yfinance). Independent cross-provider verification is not yet implemented; PASS means primary-source checks only.')
st.caption(f'Effective analysis dates: {first.date()} → {last.date()}  •  Relative window: {lookback}')

cards = st.columns(4)
counts = rows['Quadrant'].value_counts()
for col, quadrant in zip(cards, QUADRANTS):
    col.metric(quadrant, int(counts.get(quadrant, 0)))

status_filter = st.pills('QUADRANT FILTER', ['All', *QUADRANTS], default='All', selection_mode='single')
visible = rows if status_filter in ('All', None) else rows[rows['Quadrant'] == status_filter]

# Show one smooth movement path at a time. Multiple historical paths overlap
# geometrically, so avoid plotting them simultaneously.
st.markdown('#### Sector rotation overview')
control1, control2, control3 = st.columns([1.2, 1.3, 2])
with control1:
    show_trails = st.toggle('Show smooth movement path', value=True,
                            help='Shows one continuous curve without intermediate dots.')
with control2:
    trail_points = st.select_slider('Path length (sessions)', options=[5, 10, 20, 40, 60], value=20,
                                     disabled=not show_trails)
with control3:
    focus_ticker = st.selectbox('Movement path for', visible['ETF'].tolist(),
                                format_func=lambda t: f'{SECTORS[t]} ({t})',
                                disabled=not show_trails)

fig = go.Figure()
# Plot a single smooth spline beneath all current sector positions. This is
# visual interpolation only; observed daily values are never modified.
if show_trails and focus_ticker:
    selected_row = visible.loc[visible['ETF'] == focus_ticker].iloc[0]
    path_color = COLORS[selected_row['Quadrant']]
    trail = pd.DataFrame({'rs': strength[focus_ticker], 'mom': momentum[focus_ticker]}).loc[first:last].dropna().tail(trail_points)
    if len(trail) > 1:
        fig.add_trace(go.Scatter(
            x=trail.rs, y=trail.mom, mode='lines',
            line=dict(color=path_color, width=5, shape='spline', smoothing=0.65),
            opacity=0.94, name=f'{focus_ticker} movement', showlegend=False,
            text=[d.strftime('%b %d, %Y') for d in trail.index],
            hovertemplate=f'{focus_ticker} · %{{text}}<br>Strength: %{{x:.2f}}%<br>Momentum: %{{y:.2f}} pp<extra></extra>'))
        # Start marker and latest endpoint are the only path markers.
        fig.add_trace(go.Scatter(
            x=[trail.rs.iloc[0]], y=[trail.mom.iloc[0]], mode='markers',
            marker=dict(size=10, color=path_color, symbol='circle-open', line=dict(width=2, color=path_color)),
            name='Path start', showlegend=False,
            hovertemplate=f'{focus_ticker} · Path start<extra></extra>'))
        # Direction arrow from the penultimate observation to the latest.
        fig.add_annotation(x=trail.rs.iloc[-1], y=trail.mom.iloc[-1],
                           ax=trail.rs.iloc[-2], ay=trail.mom.iloc[-2],
                           xref='x', yref='y', axref='x', ayref='y',
                           showarrow=True, arrowhead=2, arrowsize=1.3,
                           arrowwidth=2.5, arrowcolor=path_color)

for quadrant in QUADRANTS:
    subset = visible[visible['Quadrant'] == quadrant]
    for _, row in subset.iterrows():
        ticker = row['ETF']
        focused = not show_trails or ticker == focus_ticker
        fig.add_trace(go.Scatter(
            x=[row['Relative strength (%)']], y=[row['RS momentum (pp)']],
            mode='markers+text', text=[ticker], textposition='top center',
            textfont=dict(size=15, color='#ffffff' if focused else '#b0bfd1'),
            name=quadrant, legendgroup=quadrant,
            showlegend=not any(t.legendgroup == quadrant and t.showlegend for t in fig.data),
            marker=dict(color=COLORS[quadrant], size=20 if focused else 13,
                        opacity=1 if focused else 0.55,
                        line=dict(color='#ffffff', width=2 if focused else 1)),
            customdata=[[row['Sector'], row['Return (%)'], row['Excess vs SPY (pp)']]],
            hovertemplate='%{customdata[0]}<br>Relative strength: %{x:.2f}%<br>RS momentum: %{y:.2f} pp<br>Return: %{customdata[1]:.2f}%<br>Excess: %{customdata[2]:.2f} pp<extra></extra>'))
fig.add_hline(y=0, line_color='#a7b9d1', line_width=2)
fig.add_vline(x=0, line_color='#a7b9d1', line_width=2)
for x, y, q in [(0.97,0.97,'Leading'),(0.03,0.97,'Improving'),(0.97,0.03,'Weakening'),(0.03,0.03,'Lagging')]:
    fig.add_annotation(x=x, y=y, xref='paper', yref='paper', text=q.upper(),
                       showarrow=False, font=dict(color=COLORS[q], size=14))
fig.update_xaxes(title='Relative strength vs SPY (%)')
fig.update_yaxes(title='Relative strength momentum (pp)')
style(fig, height=460)
fig.update_layout(margin=dict(l=35, r=35, t=55, b=45),
                  legend=dict(orientation='h', y=1.08, x=0))
# Keep both primary visuals side by side instead of spanning the entire page.
rotation_col, performance_col = st.columns([1.15, 1], gap='medium')
with rotation_col:
    st.markdown('**Relative rotation map**')
    st.plotly_chart(fig, use_container_width=True, key='sector_rotation_map')
    st.caption('One smooth sector trail at a time; all sector endpoints remain visible.')

ranked = visible.sort_values('Excess vs SPY (pp)')
bar = go.Figure(go.Bar(y=ranked['ETF'], x=ranked['Excess vs SPY (pp)'], orientation='h',
                       marker_color=[COLORS[q] for q in ranked['Quadrant']],
                       customdata=ranked['Sector'],
                       hovertemplate='%{customdata}<br>Excess vs SPY: %{x:.2f} pp<extra></extra>'))
bar.add_vline(x=0, line_color='#8ea0b8')
bar.update_xaxes(title='Excess return vs SPY (percentage points)')
style(bar, height=460)
with performance_col:
    st.markdown('**Sector performance · selected date range**')
    st.plotly_chart(bar, use_container_width=True, key='sector_performance')
    st.caption('Excess return versus SPY, in percentage points.')

# Date-range cumulative performance relative to SPY: each series starts at 0 pp.
st.markdown('#### Sector trends vs SPY')
st.caption('Cumulative sector return minus cumulative SPY return, in percentage points. Every selected sector starts at 0 on the first trading session of the From/To range. Above zero = outperforming SPY; below zero = underperforming.')
try:
    trend_data = relative_trend_from_zero(frames, visible['ETF'].tolist(), first, last)
    trend_fig = go.Figure()
    palette = ['#52b788', '#60a5fa', '#f59e0b', '#f472b6', '#a78bfa', '#2dd4bf',
               '#facc15', '#fb7185', '#38bdf8', '#c084fc', '#94a3b8']
    for idx, ticker in enumerate(trend_data.columns):
        series = trend_data[ticker].dropna()
        if series.empty:
            continue
        trend_fig.add_trace(go.Scatter(
            x=series.index, y=series.values, mode='lines', name=ticker,
            line=dict(width=2.5, color=palette[list(SECTORS).index(ticker) % len(palette)]),
            customdata=[SECTORS[ticker]] * len(series),
            hovertemplate='%{customdata} (%{fullData.name})<br>%{x|%b %d, %Y}<br>Vs SPY: %{y:+.2f} pp<extra></extra>'))
    trend_fig.add_hline(y=0, line_color='#d2dce9', line_width=1.5, line_dash='dash')
    style(trend_fig, height=390)
    trend_fig.update_layout(hovermode='x unified', legend=dict(orientation='h', y=-0.25, x=0),
                            margin=dict(l=35, r=25, t=15, b=55))
    trend_fig.update_xaxes(title='Trading date')
    trend_fig.update_yaxes(title='Cumulative excess return (pp)', ticksuffix=' pp')
    st.plotly_chart(trend_fig, use_container_width=True, key='sector_spy_relative_trend')
except ValueError as exc:
    st.warning(f'Trend unavailable: {exc}')

st.subheader('Sector classification')
st.dataframe(visible.sort_values('Relative strength (%)', ascending=False), hide_index=True,
             use_container_width=True, column_config={
                 'Relative strength (%)': st.column_config.NumberColumn(format='%.2f%%'),
                 'RS momentum (pp)': st.column_config.NumberColumn(format='%.2f'),
                 'Return (%)': st.column_config.NumberColumn(format='%.2f%%'),
                 'Excess vs SPY (pp)': st.column_config.NumberColumn(format='%.2f'),
             })
with st.expander('How classifications and dates work'):
    st.markdown('''**Leading:** positive sector/SPY relative strength and improving relative-strength momentum.  
**Improving:** negative relative strength, improving momentum.  
**Weakening:** positive relative strength, declining momentum.  
**Lagging:** negative relative strength, declining momentum.

**Relative Time** selects the number of trading sessions used to measure the change in the sector/SPY adjusted-price ratio. Momentum is the change in that relative-strength measure over half as many sessions. This is a transparent, custom four-quadrant model, **not** the proprietary RRG calculation.

**Sector trends vs SPY:** For each date, cumulative adjusted-price sector return since the selected start minus cumulative adjusted-price SPY return since that same start. All lines begin at 0 percentage points on the first available trading session; this is not a sector/SPY ratio or a daily return series.\n\n**From / To** sets the historical trail, period return comparison, and classification's as-of date. The app fetches earlier observations for indicator warm-up. Non-trading dates are mapped to available sessions inside the range. The latest market session may lag today's date.

**Data quality:** critical missing/invalid records block publication; outliers trigger warnings. Corporate-action and total-return equivalence are not independently certified. No database is used. Daily background verification is available via the included GitHub Actions workflow, while the dashboard downloads fresh data when its one-hour cache expires or you press Refresh now.''')
