import pandas as pd

def infer_asset_regime(rows, sectors):
    """Transparent heuristic based only on observed relative performance.

    Requires at least two positive excess-return assets from a group; otherwise
    return Mixed to avoid confident classification from sparse observations.
    """
    if rows.empty:
        return 'Mixed / insufficient data', 'No eligible asset-class observations.'
    names = {t: str(sectors.get(t, '')).lower() for t in rows['ETF']}
    scores = {t: float(v) for t, v in zip(rows['ETF'], rows['Excess vs SPY (pp)'])}
    def positives(terms):
        return sum(v > 0 for t, v in scores.items() if any(term in names[t] for term in terms))
    def count(terms):
        return sum(any(term in names[t] for term in terms) for t in scores)
    risk = ['equities', 'high yield', 'real estate']
    defensive = ['government bonds', 'treasury bonds', 'gold', 'cash', 'treasury bills', 'liquid etf']
    inflation = ['commodities', 'gold', 'silver']
    if count(risk) >= 2 and positives(risk) >= 2 and positives(risk) > positives(defensive):
        return 'Risk-on', 'At least two risk-sensitive asset proxies outperform the equity benchmark.'
    if count(defensive) >= 2 and positives(defensive) >= 2 and positives(defensive) > positives(risk):
        return 'Defensive', 'At least two defensive asset proxies outperform the equity benchmark.'
    if count(inflation) >= 2 and positives(inflation) >= 2 and positives(inflation) > positives(risk):
        return 'Inflation-sensitive leadership', 'At least two precious-metal/commodity proxies outperform the equity benchmark.'
    return 'Mixed / unconfirmed', 'No sufficiently broad, unambiguous cross-asset leadership signal.'
