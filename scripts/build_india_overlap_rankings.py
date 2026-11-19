#!/usr/bin/env python3
"""Precompute India factor/sector overlap and membership ranking tables.

Run after refreshing NSE constituents. No live network or financial API calls.
Example: python scripts/build_india_overlap_rankings.py
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from india_overlap_rankings import (
    build_leadership, LEADERSHIP_FIELDS, INDEX_OVERLAP_FIELDS,
    PATTERN_FIELDS, SECTOR_FACTOR_FIELDS,
)
from scripts.refresh_india_constituents import atomic_csv, atomic_json

DATA = ROOT / 'data' / 'india_holdings'


def read_memberships(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f'No saved NSE constituent table: {path}. Run India NSE Constituents Refresh first.')
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f'NSE constituency source is empty: {path}. Refusing to write rankings from no data.')
    expected = {'company_key', 'index_slug', 'symbol', 'company_name'}
    if not expected.issubset(rows[0]):
        raise ValueError(f'Invalid constituents.csv schema: missing {expected - set(rows[0])}')
    return rows


def build(data_dir: Path = DATA) -> dict:
    members = read_memberships(data_dir / 'constituents.csv')
    out = build_leadership(members)
    if not out['companies']:
        raise ValueError('No recognized valid company/index memberships found; no ranking exports written.')
    # All outputs overwrite atomically. Never delete the input NSE snapshots.
    atomic_csv(data_dir / 'leadership_companies.csv', out['companies'], LEADERSHIP_FIELDS)
    atomic_csv(data_dir / 'factor_index_overlaps.csv', out['factor_index_overlaps'], INDEX_OVERLAP_FIELDS)
    atomic_csv(data_dir / 'factor_membership_patterns.csv', out['factor_membership_patterns'], PATTERN_FIELDS)
    atomic_csv(data_dir / 'sector_factor_overlaps.csv', out['sector_factor_overlaps'], SECTOR_FACTOR_FIELDS)
    atomic_json(data_dir / 'leadership_build_summary.json', out['summary'])
    return out['summary']


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=DATA)
    args = parser.parse_args()
    print(json.dumps(build(args.data_dir), indent=2))


if __name__ == '__main__':
    main()
