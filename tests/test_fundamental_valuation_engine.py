import math
from fundamental_valuation_engine import derived_eps, graham_number, evaluate, dcf_fcf_proxy


def history():
    return [{'date': f'{y}-03-31', 'net_income': 100_000_000,
             'equity': 500_000_000, 'weighted_average_shares': 10_000_000,
             'operating_cash_flow': 120_000_000,
             'capital_expenditure': 20_000_000} for y in (2022, 2023, 2024, 2025)]


def test_eps_computed_from_company_statement_not_cash_or_provider_eps():
    h = history()
    h[-1]['diluted_eps'] = 1000  # Must never be used to derive Graham number.
    v = evaluate(h)
    assert v['Calculated EPS'] == 10
    assert v['FCF / share'] == 10
    assert math.isclose(v['Graham number'], math.sqrt(22.5 * 10 * 50))
    assert v['EPS share basis'] == 'Reported weighted-average common shares'


def test_dcf_scenarios_and_no_fabricated_missing_values():
    v = evaluate(history())
    assert 0 < v['DCF Bear'] < v['DCF Base'] < v['DCF Bull']
    h = history()
    for row in h: row.pop('capital_expenditure')
    missing = evaluate(h)
    assert math.isnan(missing['DCF Base'])
    assert missing['FCF observations'] == 0


def test_invalid_graham_inputs_and_no_share_count():
    assert math.isnan(graham_number(-1, 20))
    h = history()
    for row in h: row.pop('weighted_average_shares')
    assert math.isnan(evaluate(h)['Calculated EPS'])
    assert math.isnan(evaluate(h)['Graham number'])


def test_banks_skip_cashflow_dcf():
    v = evaluate(history(), sector='Banking')
    assert math.isnan(v['DCF Base'])
    assert math.isfinite(v['Graham number'])


def test_no_negative_cash_flow_intrinsic_proxy():
    assert math.isnan(dcf_fcf_proxy(-1, 10, .03, .11, .03))
    assert math.isnan(dcf_fcf_proxy(100, 10, .03, .02, .03))
