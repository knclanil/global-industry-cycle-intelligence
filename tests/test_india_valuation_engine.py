import math
from india_valuation_engine import normalized_fcf, scenario_table, choose_fields, earnings_valuation, valuation_metrics


def payload():
    inc = {f'{y}-03-31': {'revenue': 800 + 30 * (y-2021), 'net_income': 110, 'diluted_eps': 11} for y in range(2021, 2026)}
    bal = {f'{y}-03-31': {'total_assets': 1000, 'total_liabilities': 450, 'equity': 550, 'shares_statement': 10, 'cash': 180, 'preferred_equity':0} for y in range(2021, 2026)}
    cf = {f'{y}-03-31': {'operating_cash_flow': 120, 'capital_expenditure': -20} for y in range(2021, 2026)}
    return {'statements': {'annual': {'income': inc, 'balance': bal, 'cashflow': cf}},
            'quote': {'price': 90, 'currency': 'INR', 'shares_outstanding': 10}, 'currency': 'INR'}


def test_fcf_avg_and_scenarios():
    p = payload()
    f,n,obs = normalized_fcf(p)
    assert (f,n,len(obs)) == (100,5,5)
    s = scenario_table(p, period='2025-03-31')
    assert len(s['rows']) == 3
    assert s['rows'][0]['Value / share'] > 0
    assert s['rows'][0]['Margin of safety %'] is not None
    assert s['rows'][0]['25% MOS buy reference'] == s['rows'][0]['Value / share'] * .75


def test_no_lookahead_when_select_past_period():
    p = payload()
    s = scenario_table(p, period='2023-03-31')
    assert s['fcf_years'] == 3
    assert max(date for date,value in s['fcf_samples']) == '2023-03-31'


def test_missing_cashflow_no_value():
    p = payload()
    p['statements']['annual']['cashflow'] = {'2025-03-31': {'operating_cash_flow': 50}}
    s = scenario_table(p)
    assert all(row['Value / share'] is None for row in s['rows'])


def test_quote_currency_guard():
    p = payload(); p['quote']['currency']='USD'
    s = scenario_table(p)
    assert all(row['Margin of safety %'] is None for row in s['rows'])


def test_graham_and_earnings_multiple():
    m=valuation_metrics(payload())
    assert math.isclose(m['graham_number'], math.sqrt(22.5*11*55))
    assert earnings_valuation(11,15) == 165
    assert earnings_valuation(-11,15) is None


def test_provenance_priority():
    v, p=choose_fields({'price':100}, {}, {'price':90,'pb':2})
    assert v['price'] == 100 and p['price']=='NSE'
    assert v['pb'] == 2 and p['pb']=='Yahoo'
