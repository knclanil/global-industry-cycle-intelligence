"""Synthetic constituent records: NEVER published as live company rankings."""
from __future__ import annotations

import csv
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from india_constituents import INDEX_BY_SLUG
from india_overlap_rankings import build_leadership
from scripts.build_india_overlap_rankings import build, read_memberships


def record(symbol, slug, isin=None, weight='', date='2026-11-19T00:00:00+00:00'):
    idx = INDEX_BY_SLUG[slug]
    return dict(company_key='ISIN:'+(isin or symbol), company_name=f'{symbol} Test Company',
                symbol=symbol, isin=isin or symbol, industry='Industrials',
                index_slug=slug, index_name=idx.name, category=idx.category,
                factor_family=idx.family, parent_universe=idx.parent_universe,
                weight_pct=weight, snapshot_utc=date)


def sample():
    return [
        record('AAA', 'nifty50_value_20'),
        record('AAA', 'nifty200_value_30'),
        record('AAA', 'nifty500_value_50'),
        record('AAA', 'nifty200_quality_30'),
        record('AAA', 'nifty_bank'),
        record('AAA', 'nifty_financial_services'),
        record('BBB', 'nifty500_value_50'),
        record('BBB', 'nifty_pharma'),
        record('CCC', 'nifty500_momentum_50'),
        record('DDD', 'nifty_media'),
        record('EEE', 'nifty50_equal_weight'),
        record('FFF', 'nifty500_quality_50'),
        record('FFF', 'nifty_india_manufacturing'),
        record('FFF', 'nifty_auto'),
    ]


def test_cross_universe_same_factor_counted_once_but_confirmed():
    out = build_leadership(sample())
    by_symbol = {c['symbol']: c for c in out['companies']}
    a = by_symbol['AAA']
    assert len(out['companies']) == 6
    assert a['factor_family_count'] == 2
    assert a['factor_index_count'] == 4
    assert a['repeat_factor_memberships'] == 2
    assert a['repeat_confirmed_families'] == 1
    assert 'Value · Nifty 50' in a['factor_universes']
    assert 'Value · Nifty 200' in a['factor_universes']
    assert 'Value · Nifty 500' in a['factor_universes']
    assert a['sector_index_count'] == 2
    assert a['sector_group_count'] == 1  # Bank and Financial Services = 1 group
    assert a['factor_score'] == 55.0 # 70*2/4 + 30*2/3
    assert a['sector_score'] == 65.0
    assert a['combined_score'] == 58.0
    assert a['combined_rank'] == 1


def test_equal_weight_not_treated_as_factor_and_missing_is_not_zero():
    out = build_leadership(sample())
    by = {r['symbol']: r for r in out['companies']}
    assert by['EEE']['factor_score'] is None
    assert by['EEE']['sector_score'] is None
    assert by['EEE']['combined_score'] is None
    assert by['CCC']['sector_score'] is None
    assert by['DDD']['factor_score'] is None
    assert by['BBB']['combined_score'] is not None
    assert by['FFF']['combined_score'] is not None
    assert by['AAA']['factor_score'] > by['BBB']['factor_score']


def test_factor_value_pattern_exact_and_pairwise():
    out = build_leadership(sample())
    values = [r for r in out['factor_membership_patterns'] if r['factor_family'] == 'Value']
    patterns = {r['source_indices']: r for r in values}
    assert len(patterns) == 2
    a = next(r for r in values if r['pattern_size'] == 3)
    assert a['company_count'] == 1
    assert a['company_symbols'] == 'AAA'
    b = next(r for r in values if r['pattern_size'] == 1)
    assert b['company_symbols'] == 'BBB'
    overlap = [r for r in out['factor_index_overlaps']
               if r['factor_family'] == 'Value' and 'Nifty500 Value 50' in (r['index_a'], r['index_b'])
               and 'Nifty50 Value 20' in (r['index_a'], r['index_b'])]
    assert len(overlap) == 1
    assert overlap[0]['shared_companies'] == 1
    assert overlap[0]['union_companies'] == 2
    assert overlap[0]['jaccard_pct'] == 50.0


def test_sector_factor_intersection_unique_company_not_memberships():
    out = build_leadership(sample())
    cell = next(r for r in out['sector_factor_overlaps']
                if r['sector_index'] == 'Nifty Bank' and r['factor_family'] == 'Value')
    assert cell['overlap_companies'] == 1
    assert cell['sector_constituents'] == 1
    assert cell['company_symbols'] == 'AAA'
    assert out['summary']['dual_covered_companies'] == 3
    assert out['summary']['weight_records_observed'] == 0


def test_duplicate_same_index_record_doesnt_inflate_score_or_counts():
    rows = sample()
    out = build_leadership(rows + [rows[0]])
    a = next(r for r in out['companies'] if r['symbol'] == 'AAA')
    assert a['index_count'] == 6
    assert out['summary']['source_membership_records'] == len(rows)


def test_no_weight_imputation_and_ranking_scores_capped():
    rows = sample() + [record('AAA', 'nifty500_momentum_50', weight='9.23')]
    out = build_leadership(rows)
    a = next(r for r in out['companies'] if r['symbol'] == 'AAA')
    assert a['known_weight_entries'] == 1
    assert out['summary']['weight_records_observed'] == 1
    for c in out['companies']:
        for key in ('factor_score', 'sector_score', 'combined_score'):
            assert c[key] is None or 0 <= c[key] <= 100


def test_build_artifacts_from_committed_constituents(tmp_path):
    data_dir = tmp_path/'india_holdings'
    data_dir.mkdir()
    path = data_dir/'constituents.csv'
    fields = list(sample()[0].keys())
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        writer.writerows(sample())
    summary = build(data_dir)
    assert summary['companies'] == 6
    assert (data_dir/'leadership_companies.csv').is_file()
    assert (data_dir/'factor_index_overlaps.csv').is_file()
    assert (data_dir/'factor_membership_patterns.csv').is_file()
    assert (data_dir/'sector_factor_overlaps.csv').is_file()
    assert (data_dir/'leadership_build_summary.json').is_file()
    with (data_dir/'leadership_companies.csv').open() as f:
        assert len(list(csv.DictReader(f))) == 6


def test_absent_source_cannot_erase_existing_rankings(tmp_path):
    with pytest.raises(FileNotFoundError):
        build(tmp_path)
    assert not (tmp_path/'leadership_companies.csv').exists()
