"""Global Industry Cycle Intelligence — Streamlit Community Cloud app."""
from datetime import date, timedelta
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Global Industry Cycle Intelligence", page_icon="🌐", layout="wide")
SECTORS = {
    'XLC': 'Communication Services', 'XLY': 'Consumer Discretionary',
    'XLP': 'Consumer Staples', 'XLE': 'Energy', 'XLF': 'Financials',
    'XLV': 'Healthcare', 'XLI': 'Industrials', 'XLB': 'Materials',
    'XLRE': 'Real Estate', 'XLK': 'Technology', 'XLU': 'Utilities'
}
TICKERS = list(SECTORS) + ['SPY']
LOOKBACKS = {'1W': 5, '2W': 10, '4W': 20, '1M': 21, '3M': 63, '6M': 126, '12M': 252}
COLORS = {'Leading': '#19c58a', 'Improving': '#4da3ff', 'Weakening': '#f4aa4b', 'Lagging': '#fb7185'}
BG = '#0b1220'; PANEL = '#121e30'; TEXT = '#e8effa'; MUTED = '#95a8c1'

def fetch_prices(start, end):
    """Return raw multi-ticker OHLCV in memory; no filesystem or DB writes."""
    result = yf.download(TICKERS, start=start.strftime('%Y-%m-%d'), end=(end + timedelta(days=1)).strftime('%Y-%m-%d'), auto_adjust=False, actions=False, group_by='ticker', progress=False, threads=True)
    if result.empty:
        raise RuntimeError('Provider returned no market data. Check internet access or retry.')
    frames = {}
    for t in TICKERS:
        if isinstance(result.columns, pd.MultiIndex):
            if t in result.columns.get_level_values(0):
                df = result[t].copy()
            elif t in result.columns.get_level_values(1):
                df = result.xs(t, axis=1, level=1).copy()
            else:
                continue
        else:
            df = result.copy() if len(TICKERS) == 1 else pd.DataFrame()
        if not df.empty:
            df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
            frames[t] = df.sort_index()
    return frames

def validate(frames, selected_end):
    errors, warnings = [], []
    if 'SPY' not in frames or frames['SPY'].empty:
        return 'FAIL', ['Missing SPY benchmark'], []
    ref = frames['SPY'].dropna(subset=['Close']).index
    if len(ref) < 2:
        return 'FAIL', ['Insufficient benchmark observations'], []
    last = ref.max()
    for ticker in TICKERS:
        if ticker not in frames or frames[ticker].empty:
            errors.append(f'{ticker}: missing data')
            continue
        df = frames[ticker]
        needed = ['Open','High','Low','Close','Adj Close','Volume']
        if any(c not in df.columns for c in needed):
            errors.append(f'{ticker}: missing required OHLCV columns')
            continue
        if df.index.has_duplicates:
            errors.append(f'{ticker}: duplicate trading dates')
        if df[needed].isna().any().any():
            errors.append(f'{ticker}: missing OHLCV values')
        if (df[['Open','High','Low','Close','Adj Close']] <= 0).any().any() or (df['Volume'] < 0).any():
            errors.append(f'{ticker}: nonpositive price or negative volume')
        bad = (df['High'] < df[['Open','Close','Low']].max(axis=1)) | (df['Low'] > df[['Open','Close','High']].min(axis=1))
        if bad.any():
            errors.append(f'{ticker}: invalid OHLC ordering')
        missing = ref[(ref >= df.index.min()) & (ref <= df.index.max())].difference(df.index)
        if len(missing):
            errors.append(f'{ticker}: {len(missing)} missing SPY trading sessions')
        if df.index.max() < last:
            warnings.append(f'{ticker}: last observation precedes benchmark')
        outliers = (df['Adj Close'].pct_change().abs() > .15).sum()
        if outliers:
            warnings.append(f'{ticker}: {outliers} daily return outlier(s) >15%')
    if (pd.Timestamp(selected_end) - last).days > 5 and pd.Timestamp(selected_end).date() >= date.today() - timedelta(days=5):
        warnings.append(f'Latest session {last.date()} is more than five calendar days before selected end date')
    return ('FAIL' if errors else 'WARNING' if warnings else 'PASS'), errors, warnings

def compute(frames, chosen, from_date, to_date, lookback):
    adj = pd.concat({t: f['Adj Close'] for t, f in frames.items()}, axis=1).sort_index()
    adj = adj.loc[:pd.Timestamp(to_date)]
    if adj.empty or 'SPY' not in adj:
        raise ValueError('No benchmark data in selected range')
    ref = adj['SPY']; ratio = adj.div(ref, axis=0)
    L = LOOKBACKS[lookback]; M = max(2, L // 2)
    strength = (ratio / ratio.shift(L) - 1) * 100
    momentum = (ratio / ratio.shift(M) - 1) * 100
    # Use sessions at or before requested bounds; first session at or after from date for returns.
    window = adj.loc[pd.Timestamp(from_date):pd.Timestamp(to_date)]
    if len(window) < 2:
        raise ValueError('Select a date range with at least two trading sessions')
    end = window.index[-1]
    first = window.index[0]
    rows = []
    for t in chosen:
        if t not in adj or pd.isna(strength.at[end,t]) or pd.isna(momentum.at[end,t]):
            continue
        rs, mom = float(strength.at[end,t]), float(momentum.at[end,t])
        quadrant = 'Leading' if rs >= 0 and mom >= 0 else 'Improving' if rs < 0 and mom >= 0 else 'Weakening' if rs >= 0 else 'Lagging'
        if pd.isna(adj.at[first,t]) or pd.isna(adj.at[end,t]):
            continue
        ret = (adj.at[end,t] / adj.at[first,t] - 1) * 100
        spyret = (adj.at[end,'SPY'] / adj.at[first,'SPY'] - 1) * 100
        rows.append({'ticker': t, 'sector': SECTORS[t], 'status': quadrant, 'relative_strength': round(rs,2), 'momentum': round(mom,2), 'return': round(ret,2), 'excess': round(ret-spyret,2)})
    return pd.DataFrame(rows), strength, momentum, first, end


@st.cache_data(ttl=3600, show_spinner=False)
def cached_prices(start, end):
    return fetch_prices(start, end)

st.markdown("""<style>
.stApp {background:#0b1220;color:#e8effa}
[data-testid="stMetric"] {background:#121e30;border:1px solid #29384e;border-radius:12px;padding:14px}
[data-testid="stMetricLabel"] {color:#a7b9d1}
</style>""", unsafe_allow_html=True)

h1,h2=st.columns([5,1])
with h1:
    st.title('Global Industry Cycle Intelligence')
    st.caption('USA sector rotation · Relative strength and momentum versus SPY · No database')
with h2:
    if st.button('↻ Refresh data', use_container_width=True):
        cached_prices.clear()
        st.rerun()

with st.container(border=True):
    a,b,c=st.columns([2,2,2])
    with a:
        select_all=st.checkbox('Select all sectors',value=True,key='all_sectors')
        chosen=st.multiselect('SECTORS',options=list(SECTORS),default=list(SECTORS) if select_all else [],format_func=lambda t:f'{SECTORS[t]} ({t})',key='chosen_sectors')
    with b:
        lookback=st.segmented_control('RELATIVE TIME',options=list(LOOKBACKS),default='3M',selection_mode='single')
    with c:
        dr=st.date_input('FROM DATE → TO DATE',value=(date.today()-timedelta(days=365),date.today()),min_value=date(2019,1,1),max_value=date.today(),format='MM/DD/YYYY')

if not chosen:
    st.info('Select one or more sectors to begin.'); st.stop()
if not lookback or len(dr)!=2:
    st.info('Choose a relative time and both dates.'); st.stop()
start,end=dr
if start>=end:
    st.warning('From Date must be earlier than To Date.'); st.stop()

# Allow a full 12-month indicator warm-up before From Date.
with st.spinner('Downloading and validating USA sector data…'):
    try:
        frames=cached_prices(start-timedelta(days=420),end)
        quality,errors,warnings=validate(frames,end)
        if quality=='FAIL':
            st.error('Data validation failed; no sector classifications published.')
            for error in errors: st.write('• '+error)
            st.stop()
        rows,strength,momentum,first,last=compute(frames,chosen,start,end,lookback)
    except Exception as e:
        st.error(f'Market data unavailable or insufficient: {e}')
        st.stop()
if rows.empty:
    st.warning('Not enough valid observations for the selected dates.'); st.stop()

if quality=='PASS':
    st.success(f'Primary-source checks passed · Effective trading dates: {first.date()} – {last.date()} · Yahoo Finance · Independent verification not yet implemented')
else:
    st.warning('Primary-source validation warnings: '+'; '.join(warnings[:5]))

counts=rows.status.value_counts()
metrics=st.columns(4)
for col,q in zip(metrics,COLORS):
    col.metric(q, int(counts.get(q,0)))

filter_status=st.pills('QUADRANT FILTER',options=['All',*COLORS],default='All',selection_mode='single')
visible=rows if filter_status in (None,'All') else rows.loc[rows.status==filter_status]

fig=go.Figure()
for q,color in COLORS.items():
    subset=visible[visible.status==q]
    if subset.empty: continue
    for _,row in subset.iterrows():
        hist=pd.DataFrame({'x':strength[row.ticker],'y':momentum[row.ticker]}).loc[first:last].dropna()
        if len(hist)>1:
            hist=hist.iloc[::max(1,len(hist)//40)]
            fig.add_trace(go.Scatter(x=hist.x,y=hist.y,mode='lines',line=dict(color=color,width=1),opacity=.4,showlegend=False,hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=subset.relative_strength,y=subset.momentum,mode='markers+text',text=subset.ticker,textposition='top center',name=q,marker=dict(size=13,color=color,line=dict(width=1,color='white')),customdata=subset[['sector','return','excess']].values,hovertemplate='%{customdata[0]}<br>RS: %{x:.2f}%<br>Momentum: %{y:.2f}%<br>Return: %{customdata[1]:.2f}%<br>Excess: %{customdata[2]:.2f} pp<extra></extra>'))
fig.add_hline(y=0,line_color='#8293aa');fig.add_vline(x=0,line_color='#8293aa')
for x,y,q in [(0.98,0.98,'Leading'),(.02,.98,'Improving'),(.98,.02,'Weakening'),(.02,.02,'Lagging')]:
    fig.add_annotation(x=x,y=y,xref='paper',yref='paper',text=q.upper(),showarrow=False,font=dict(color=COLORS[q],size=11))
fig.update_xaxes(title='Relative strength vs SPY (%)');fig.update_yaxes(title='Relative momentum (%)')
style_fig(fig).update_layout(height=510)
ranked=visible.sort_values('excess')
bar=go.Figure(go.Bar(y=ranked.ticker,x=ranked.excess,orientation='h',marker_color=[COLORS[q] for q in ranked.status],customdata=ranked.sector,hovertemplate='%{customdata}<br>Excess: %{x:.2f} pp<extra></extra>'))
bar.add_vline(x=0,line_color='#8293aa');bar.update_xaxes(title='Excess return vs SPY (percentage points)')
style_fig(bar).update_layout(height=510)
left,right=st.columns(2)
with left:
    st.subheader('Relative Rotation Map')
    st.plotly_chart(fig,use_container_width=True)
with right:
    st.subheader('Sector performance · selected date range')
    st.plotly_chart(bar,use_container_width=True)
st.subheader('Sector classification')
st.dataframe(visible.rename(columns={'sector':'Sector','ticker':'ETF','status':'Quadrant','relative_strength':'Relative strength (%)','momentum':'Momentum (%)','return':'Return (%)','excess':'Excess vs SPY (pp)'}),hide_index=True,use_container_width=True)
st.caption('Method: sector/SPY adjusted-close ratio; relative strength uses selected lookback, momentum half that lookback. Original transparent quadrant model, not proprietary RRG. Adjusted-price returns are not independently verified total returns. Not investment advice.')
