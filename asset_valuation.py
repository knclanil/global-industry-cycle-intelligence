"""Asset-based and illustrative going-concern valuation for cached SEC Company Facts.

No live pricing. Scenario outputs are estimates, not realizable transaction prices.
"""
import math
import pandas as pd
import streamlit as st


def _fact(data, tags, unit, period, instant=True):
    target = pd.Timestamp(period)
    candidates = []
    for taxonomy in ('dei', 'us-gaap'):
        source = data.get('facts', {}).get(taxonomy, {})
        for priority, tag in enumerate(tags):
            for row in source.get(tag, {}).get('units', {}).get(unit, []):
                if row.get('form') not in ('10-K', '10-K/A', '10-Q', '10-Q/A'):
                    continue
                if instant and row.get('start'):
                    continue
                try:
                    end = pd.Timestamp(row['end'])
                    val = float(row['val'])
                except (KeyError, ValueError, TypeError):
                    continue
                if not math.isfinite(val) or end > target or (target - end).days > 100:
                    continue
                candidates.append(((target - end).days, priority, -pd.Timestamp(row.get('filed', '1900-01-01')).value, val, tag, str(end.date())))
    if not candidates:
        return None, None
    best = min(candidates)
    return best[3], f'{best[4]} · {best[5]}'


def _fmt(value):
    return 'N/A' if value is None or not math.isfinite(value) else f'${value:,.2f}'


def _per_share(numerator, shares):
    return numerator / shares if numerator is not None and shares is not None and shares > 0 else None


def render_asset_valuation(data, period, assets, liabilities, equity, current_assets, net_income, eps, fcf, bank=False):
    st.markdown('### Asset Value & Intrinsic Value')
    st.caption('Book-value measures use reported SEC facts. Liquidation and DCF values are assumption-driven scenarios, not guaranteed sale proceeds or price targets.')
    shares, shares_source = _fact(data, ['EntityCommonStockSharesOutstanding', 'CommonStockSharesOutstanding'], 'shares', period)
    preferred, preferred_source = _fact(data, ['PreferredStockValue', 'PreferredStockCarryingValue'], 'USD', period)
    goodwill, goodwill_source = _fact(data, ['Goodwill'], 'USD', period)
    intangibles, intangible_source = _fact(data, ['FiniteLivedIntangibleAssetsNet', 'IntangibleAssetsNetExcludingGoodwill'], 'USD', period)
    common_equity, common_source = _fact(data, ['StockholdersEquityCommonStock'], 'USD', period)
    # Do not silently assume preferred stock or unreported intangible assets are zero.
    if common_equity is None and preferred is not None and equity is not None:
        common_equity = equity - preferred
    book = _per_share(common_equity, shares)
    tangible = _per_share(common_equity - goodwill - intangibles, shares) if all(x is not None for x in (common_equity, goodwill, intangibles)) else None
    ncav = _per_share(current_assets - liabilities - preferred, shares) if all(x is not None for x in (current_assets, liabilities, preferred)) else None
    graham = math.sqrt(22.5 * eps * book) if eps is not None and book is not None and eps > 0 and book > 0 else None
    cards = [
        ('Common book value / share', book, 'Common equity ÷ shares'),
        ('Tangible book / share', tangible, 'Excludes reported goodwill and other intangibles'),
        ('NCAV / share', ncav, '(Current assets − all liabilities − preferred) ÷ shares'),
        ('Graham Number', graham, '√(22.5 × positive EPS × positive BVPS)'),
    ]
    for col, (name, value, explanation) in zip(st.columns(4), cards):
        with col:
            st.metric(name, _fmt(value))
            st.caption(explanation)
    if common_equity is None:
        st.info('Common shareholders’ equity is not separately verified for this period. Book-based per-share values are withheld rather than treating preferred claims as zero.')
    if shares is None:
        st.warning('Comparable period-end common shares outstanding are missing; per-share values cannot be calculated.')
    if bank:
        st.info('Financial institutions require specialized asset recovery, capital and regulatory assumptions. The scenarios below are not bank-specific valuations.')
    st.markdown('### Hypothetical liquidation recovery')
    st.caption('Illustrative total-asset recovery approach. Actual recoveries depend on asset classes, priority claims, taxes, contingent liabilities, and transaction costs.')
    col1, col2 = st.columns(2)
    with col1:
        recovery = st.slider('Estimated recovery of reported assets', 0, 120, 70, 5, key='asset_recovery') / 100
    with col2:
        costs = st.slider('Liquidation costs (% of gross recovered assets)', 0, 30, 5, 1, key='liquidation_cost') / 100
    liquidation = None
    if assets is not None and liabilities is not None and preferred is not None:
        gross = assets * recovery
        liquidation = _per_share(max(0, gross * (1 - costs) - liabilities - preferred), shares)
    st.metric('Illustrative common liquidation proceeds / share', _fmt(liquidation))
    if preferred is None:
        st.caption('N/A: preferred stock claims are not verified; they cannot be assumed to be zero. This conservative requirement can limit coverage.')
    st.markdown('### Discounted Cash Flow (DCF) — illustrative intrinsic value')
    st.caption('Five-year FCF projection plus perpetual terminal value. This simplified equity-FCF model is appropriate only when FCF represents cash available to common shareholders; reported operating FCF minus capex often does not, so treat output as a screening scenario.')
    a, b, c = st.columns(3)
    with a:
        growth = st.number_input('Annual FCF growth (%)', -50.0, 100.0, 5.0, 0.5, key='dcf_growth') / 100
    with b:
        discount = st.number_input('Required return (%)', 1.0, 40.0, 10.0, 0.5, key='dcf_discount') / 100
    with c:
        terminal = st.number_input('Terminal growth (%)', -5.0, 10.0, 2.0, 0.5, key='dcf_terminal') / 100
    intrinsic = None
    if fcf is not None and fcf > 0 and shares is not None and shares > 0 and discount > terminal:
        projected = [fcf * (1 + growth) ** t for t in range(1, 6)]
        present = sum(value / (1 + discount) ** t for t, value in enumerate(projected, 1))
        terminal_value = projected[-1] * (1 + terminal) / (discount - terminal)
        intrinsic = (present + terminal_value / (1 + discount) ** 5) / shares
    st.metric('Illustrative DCF value / share', _fmt(intrinsic))
    if fcf is None or fcf <= 0:
        st.caption('DCF not calculated: positive verified annual free cash flow is required for this simplified model.')
    if discount <= terminal:
        st.error('Required return must exceed terminal growth.')
    with st.expander('Definitions, data provenance & limitations'):
        st.markdown(f'''**Financial period:** {period}. **Share count:** {shares:,.0f} if available; otherwise N/A. **Share source:** {shares_source or 'unavailable'}.

**Common equity source:** {common_source or ('total equity less reported preferred' if common_equity is not None else 'unavailable')}. **Preferred source:** {preferred_source or 'unavailable'}. **Goodwill:** {goodwill_source or 'unavailable'}. **Other intangibles:** {intangible_source or 'unavailable'}.

**Graham Number:** A traditional screening formula, not Benjamin Graham’s complete investment method or a guaranteed intrinsic value. Only calculated when both EPS and common book value are positive.

**Liquidation scenario:** A single recovery percentage for all assets is a simplified sensitivity estimate, not an appraisal. Zero is used as a floor for hypothetical common liquidation proceeds, not for book or NCAV.

**DCF:** The model discounts a user-selected growth projection of the latest reported annual FCF. It does not adjust for debt financing, changes in working capital, or nonrecurring items and is not a formal FCFE valuation. **No current stock price is assumed or fetched.**''')
