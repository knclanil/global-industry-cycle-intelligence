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

# Bundled documentation fallback keeps Wiki working if WIKI.md is omitted from deployment.
BUNDLED_WIKI = "# Dashboard Wiki\n\n**Global Industry Cycle Intelligence** is a US equity-sector rotation dashboard comparing 11 sector ETFs with **SPY** (the S&P 500 ETF). It is a descriptive, historical analytics tool, not an investment recommendation or a forward-return forecast.\n\n## 1. Coverage and source\n\n| ETF | Sector |\n|---|---|\n| XLC | Communication Services |\n| XLY | Consumer Discretionary |\n| XLP | Consumer Staples |\n| XLE | Energy |\n| XLF | Financials |\n| XLV | Healthcare |\n| XLI | Industrials |\n| XLB | Materials |\n| XLRE | Real Estate |\n| XLK | Technology |\n| XLU | Utilities |\n| SPY | Benchmark: S&P 500 ETF |\n\n**Data provider:** Yahoo Finance, retrieved using the Python `yfinance` package. The dashboard uses **adjusted daily closing prices** for all returns and relative indicators; OHLC and volume are downloaded for integrity checks. Adjusted prices may be revised by the provider, and their handling of distributions and corporate actions is not independently certified. This application does not query an independent second market-data provider.\n\n## 2. Controls and effective dates\n\n- **Select all sectors / SECTORS:** Include all 11 ETFs or choose one or more. This changes the plotted sector points, comparison bars, trend lines and classification table. SPY remains the benchmark even when it is not shown as a sector.\n- **RELATIVE TIME:** Sets the trading-session lookback used to calculate relative strength and momentum; it does **not** set the displayed date range. Mapping: **1W = 5**, **2W = 10**, **4W = 20**, **1M = 21**, **3M = 63**, **6M = 126**, **12M = 252** trading sessions.\n- **FROM DATE → TO DATE:** Defines the display period and the classification **as-of** date. The app uses the first and last available trading sessions *inside* the chosen calendar range. Weekends and exchange holidays therefore do not generate observations. The app also retrieves up to **600 calendar days before From Date** to warm up the indicators.\n- **QUADRANT FILTER:** Shows only sectors in the chosen quadrant on the charts and table. The four KPI counts still describe the complete selected sector set, before this filter.\n- **Show smooth movement path:** Toggles the historical rotation trail. **Path length (sessions)** chooses the maximum number of recent plotted observations: 5, 10, 20, 40 or 60. **Movement path for** chooses one sector. Only one trail is shown at a time to reduce overlapping paths; other sector endpoints remain on the map.\n- **Refresh now:** Clears Streamlit's cached price download and reruns the dashboard. It does not force Yahoo Finance to publish a new session.\n\nThe app permits dates from **January 1, 2019** through the current date. Relative Time is independent of the From/To span: a 12M indicator can be shown as of the last day of a short selected period if sufficient earlier data is available.\n\n## 3. Relative rotation map: exact model\n\nThis is an **original zero-centered strength/momentum model**, **not** the proprietary Relative Rotation Graph (RRG) methodology. Let:\n\n- `P(s,t)` = adjusted close of sector ETF `s` on trading session `t`.\n- `P(SPY,t)` = SPY adjusted close on the same session.\n- `Q(s,t) = P(s,t) / P(SPY,t)` = sector-to-SPY price ratio.\n- `L` = sessions selected by **RELATIVE TIME**.\n- `M = max(2, floor(L / 2))` = momentum comparison lag, in sessions.\n\n**Relative strength (horizontal axis, %):**\n\n`RS(s,t) = 100 × [ Q(s,t) / Q(s,t−L) − 1 ]`\n\n**Relative strength momentum (vertical axis, percentage points):**\n\n`MOM(s,t) = RS(s,t) − RS(s,t−M)`\n\nHere `t−L` and `t−M` mean earlier **trading observations**, not calendar-day subtraction. The ratio compares adjusted-price performance over the lookback; the momentum metric measures how that lookback-relative-strength value changed over `M` observations. Momentum is measured in **percentage points (pp)**, not percent change of RS.\n\n### Quadrant classification\n\n| Quadrant | Condition | Meaning |\n|---|---|---|\n| **Leading** | `RS ≥ 0` and `MOM ≥ 0` | Outperforming SPY over the RS lookback, with non-declining RS |\n| **Improving** | `RS < 0` and `MOM ≥ 0` | Underperforming SPY over the RS lookback, but RS is improving |\n| **Weakening** | `RS ≥ 0` and `MOM < 0` | Outperforming SPY over the RS lookback, but RS is deteriorating |\n| **Lagging** | `RS < 0` and `MOM < 0` | Underperforming SPY over the RS lookback, with declining RS |\n\n**Zero belongs to the nonnegative side** of each threshold. The quadrant is determined from the latest available trading session inside To Date, using the selected Relative Time. The four KPI cards count how many selected sectors are classified in each quadrant.\n\n### Rotation paths and visual interpretation\n\nEach point is the sector's current `(RS, MOM)` pair. The chosen movement path connects up to the selected number of **daily historical indicator observations** ending at the as-of date. The path is drawn using a **Plotly spline** (`smoothing = 0.65`) to look continuous. The curve between observations is **visual interpolation only**: it does not represent additional measured prices or alter calculations. A hollow circle marks the path's first observation and an arrow indicates the most recent direction. Paths can bend, loop or cross themselves. Showing only one path at a time avoids cross-sector trail clutter but does **not** guarantee the path never crosses itself or an endpoint.\n\nThe map is a **relative** diagnostic: Leading does not necessarily mean positive absolute returns, and Lagging does not necessarily mean negative absolute returns.\n\n## 4. Sector performance chart and classification table\n\nLet `t0` be the **first** available trading session inside From/To and `t1` the **last**. Both returns are computed from adjusted closing prices:\n\n`SectorReturn(s) = 100 × [ P(s,t1) / P(s,t0) − 1 ]`\n\n`SPYReturn = 100 × [ P(SPY,t1) / P(SPY,t0) − 1 ]`\n\n`Excess(s) = SectorReturn(s) − SPYReturn` **(percentage points)**\n\nThe **horizontal bar chart** ranks sector excess returns from the selected period, with a vertical zero reference line. Positive bars outperform SPY over that period; negative bars underperform. Bar color reflects the sector's **quadrant**, which is calculated over the separate Relative Time lookback and may not agree with the sign of the selected-period excess return.\n\nThe **classification table** displays ETF, sector, quadrant, RS (%), RS momentum (pp), selected-period sector return (%) and selected-period excess vs SPY (pp). It is sorted by relative strength descending by default and can be interactively sorted.\n\n## 5. Sector trends vs SPY: every line starts at zero\n\nFor each trading session `t` in the selected period, using the **same initial date `t0`** for sector and SPY:\n\n`CumulativeSector(s,t) = 100 × [ P(s,t) / P(s,t0) − 1 ]`\n\n`CumulativeSPY(t) = 100 × [ P(SPY,t) / P(SPY,t0) − 1 ]`\n\n`Trend(s,t) = CumulativeSector(s,t) − CumulativeSPY(t)` **(percentage points)**\n\nAt `t = t0`, both cumulative returns equal zero, so **every sector trend starts at exactly 0 pp**. For example, if a sector has returned **+8%** and SPY **+5%** since the selected starting session, its plotted value is **+3 pp**. If the sector is **−4%** and SPY **−2%**, its plotted value is **−2 pp**.\n\n- **Above 0:** The sector has outperformed SPY cumulatively since the selected start.\n- **Below 0:** The sector has underperformed SPY cumulatively since the selected start.\n- **Rising/falling:** Its cumulative performance gap versus SPY is increasing/decreasing. A rising line does not necessarily imply a rising sector price.\n\nThis chart plots **cumulative-return differences**, not daily excess returns and not the sector/SPY ratio. It uses the **From/To** dates, not the Relative Time lookback. Trend lines are straight connections between actual daily observations; they are not smoothed or forecast.\n\n## 6. Validation, freshness and missing data\n\nThe dashboard downloads all 11 sector ETFs **plus SPY** and validates the primary-source data before showing classifications. It checks for:\n\n- Missing ETF or benchmark data, required Open/High/Low/Close/Adj Close/Volume columns, nulls, duplicate dates and nonpositive prices or negative volume.\n- Impossible OHLC ordering (for example, High below Open/Close/Low).\n- Missing benchmark-aligned sessions *within each ETF's available span*, or an ETF lacking the latest SPY session.\n- Adjusted-close daily changes greater than **15%**, flagged for review as **warnings**, not automatic failures.\n- Stale data (a warning when a recent end date was requested but the last observed session is more than five calendar days before it).\n\n**FAIL:** Critical integrity errors; classifications are withheld. **WARNING:** Data is usable but flagged issues are displayed. **PASS:** The listed primary-source checks passed. PASS does **not** mean prices were independently cross-checked or audited. Validation is not a guarantee of complete market-data accuracy.\n\nMissing values are **not forward-filled** in the trend series. An invalid or unavailable starting sector price prevents a zero-based trend for that selection. The latest session can lag the current day, especially before market close, on weekends and holidays.\n\n## 7. Refreshing, scheduled checks and architecture\n\n- **On-demand dashboard:** Streamlit retrieves market data through `yfinance`. Its price-download cache lasts **3,600 seconds (one hour)**. Opening or rerunning the app after cache expiry fetches again; an already-open idle browser is **not** guaranteed to refresh itself automatically.\n- **Manual refresh:** The **Refresh now** button clears that cache and reruns the app.\n- **Scheduled GitHub Actions check:** `.github/workflows/daily-data-check.yml` runs at **23:30 UTC Monday–Friday** (6:30 p.m. Eastern Standard Time / 7:30 p.m. Eastern Daylight Time), subject to GitHub scheduling delays and skips. The workflow calls `daily_check.py`, checks approximately **45 calendar days** of recent data and uploads `data_quality_report.json` as a workflow artifact.\n- **No database:** The workflow **does not** persist historical price data, commit reports to the repository, or push updates into a running Streamlit session. The dashboard downloads its own prices when needed. GitHub Actions may be run manually, but manual daily execution is not required for normal dashboard use.\n\n### Files in the repository\n\n| File | Purpose |\n|---|---|\n| `app.py` | Streamlit UI, controls, KPI cards, plots and wiki navigation |\n| `market_data.py` | Yahoo download, validation, relative rotation calculations and zero-based trend |\n| `daily_check.py` | Standalone data-quality verification and JSON report |\n| `.github/workflows/daily-data-check.yml` | Scheduled and manually dispatched verification workflow |\n| `tests/` | Synthetic-data tests for market calculations |\n| `requirements.txt` | Python dependencies |\n| `README.md` | Installation and deployment instructions |\n| `WIKI.md` | This documentation, displayed inside the application |\n\n## 8. Important limitations\n\n1. **Historical classifications are not predictions.** Sector rotation can change quickly; relative outperformance does not guarantee a positive return.\n2. **SPY is a proxy** for the S&P 500, not the index itself; sector ETFs have their own fees, holdings and tracking differences.\n3. **The quadrant model is custom**, not the proprietary JdK RRG method. Its axes and quadrant names should not be treated as directly interchangeable with commercial RRG charts.\n4. **Lookback and display window are different concepts.** The rotation map and period-excess chart can show different signs without a calculation error.\n5. **Smooth paths are cosmetic**, and intermediate positions on the spline are not observed data.\n6. **Provider dependence:** There is no second-source verification, and Yahoo Finance may revise or delay prices.\n7. **No database or continuous streaming:** Data is downloaded on demand; scheduled validation does not update an open dashboard.\n8. **Date and data availability:** ETF inception dates, holidays, incomplete sessions and missing provider records can restrict historical comparisons.\n\n**Glossary:** **Adjusted close** = provider-adjusted closing price; **RS** = relative strength over the chosen lookback; **MOM** = change in RS over a shorter lag; **pp** = percentage points; **as-of date** = last observed trading session inside the chosen date range; **excess return** = sector cumulative return minus SPY cumulative return.\n"

# Keep documentation accessible even when market data is unavailable.
page = st.sidebar.radio('NAVIGATION', ['Dashboard', 'Wiki'], index=0)
if page == 'Wiki':
    from pathlib import Path
    st.title('Dashboard Wiki')
    st.caption('Definitions, calculation formulas, controls, data quality and operational details.')
    wiki_path = Path(__file__).resolve().parent / 'WIKI.md'
    st.markdown(wiki_path.read_text(encoding='utf-8') if wiki_path.is_file() else BUNDLED_WIKI)
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
