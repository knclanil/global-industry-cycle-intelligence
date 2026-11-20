import numpy as np
import pandas as pd
from fundamental_rankings_engine import history_metrics, rank_fundamentals, build_history_india, WEIGHTS


def sample_history():
    return [{'date': f'{y}-03-31', 'revenue': 100*(y-2018), 'net_income': 12*(y-2018),
             'operating_income': 18*(y-2018), 'equity': 100, 'debt': 30,
             'current_assets': 80, 'current_liabilities': 40, 'assets': 250,
             'liabilities': 100, 'dividend': y - 2020} for y in range(2021, 2026)]


def test_good_history():
    v = history_metrics(sample_history())
    assert v['Years'] == 5
    assert np.isclose(v['ROE'], .6)
    assert np.isclose(v['Current ratio'], 2)
    assert v['Dividend growth'] > 0
    assert sum(WEIGHTS.values()) == 1


def test_missing_dividend_unscored():
    h = sample_history()
    for r in h: r['dividend'] = np.nan
    v = history_metrics(h)
    assert np.isnan(v['Dividend consistency']) and np.isnan(v['Dividend growth'])


def test_short_history_not_ranked():
    v = history_metrics(sample_history()[-2:])
    assert np.isnan(v['ROE'])


def test_company_peer_rankings():
    base = history_metrics(sample_history())
    rows = []
    for n in range(7):
        r = dict(base)
        r['ROE'] = .10 + n*.025
        rows.append({'Region':'India', 'Sector':'Manufacturing', 'Ticker': str(n), 'Company': str(n), **r})
    scores = rank_fundamentals(pd.DataFrame(rows))
    assert scores['Rank'].notna().sum() == 7
    assert scores.loc[scores.Ticker.eq('6'), 'Fundamental score'].iloc[0] > scores.loc[scores.Ticker.eq('0'), 'Fundamental score'].iloc[0]


def test_sector_without_peers_is_not_ranked():
    base = history_metrics(sample_history())
    scores = rank_fundamentals(pd.DataFrame([{'Region':'USA','Sector':'Unique','Ticker':'A','Company':'A',**base}]))
    assert scores.Status.iloc[0].startswith('Insufficient')


def test_india_snapshot_no_invention():
    payload = {'statements': {'annual': {'income': {'2025-03-31': {'revenue': 100}},
                                            'balance': {}, 'cashflow': {}}}}
    rows = build_history_india(payload)
    assert len(rows) == 1 and np.isnan(rows[0]['debt'])


def test_discontinuous_history_not_ranked():
    records = sample_history()
    records[2]['date'] = '2016-03-31'
    vals = history_metrics(records)
    assert np.isnan(vals['ROE'])
