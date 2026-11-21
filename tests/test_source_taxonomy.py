from source_taxonomy import classify_source


def test_value_grouping():
    for title in ['Nifty500 Value 50', 'Nifty200 Value 30', 'Nifty50 Value 20']:
        result = classify_source(title, category='Factor')
        assert (result.kind, result.family, result.status) == ('factor', 'Value', 'mapped')


def test_other_factors():
    for title, family in [('Nifty500 Momentum 50','Momentum'), ('Nifty200 Quality 30','Quality'),
                          ('Nifty100 Low Volatility 30','Low Volatility'),
                          ('Nifty500 Growth 50','Growth'), ('Nifty Alpha Index','Alpha'),
                          ('Nifty Dividend Opportunities 50','Dividend'),
                          ('Nifty50 Equal Weight','Equal Weight')]:
        assert classify_source(title, category='Factor').family == family


def test_new_sectors():
    for slug in ('nifty_oil_gas', 'nifty_india_defence', 'nifty_india_manufacturing'):
        result = classify_source('', slug=slug, category='Thematic')
        assert result.kind == 'sector' and result.status == 'mapped'


def test_avoid_invented_rotation():
    assert not hasattr(classify_source('Nifty500 Value 50', category='Factor'), 'rotation')


def test_ambiguity_not_guessed():
    assert classify_source('Dividend Growth Factor Index', category='Factor').status == 'ambiguous'


def test_russell_2000_etf_small_cap_factor():
    for category in ('ETF', '', 'Index', 'Factor'):
        actual = classify_source('iShares Russell 2000 ETF', category=category)
        assert (actual.kind, actual.family, actual.status) == ('factor', 'Small Cap', 'mapped')

def test_global_comm_services_etf_communications_sector():
    for name in ('iShares Global Comm Services ETF', 'iShares Global Communication Services ETF'):
        actual = classify_source(name, category='ETF')
        assert (actual.kind, actual.family, actual.status) == ('sector', 'Communications', 'mapped')
