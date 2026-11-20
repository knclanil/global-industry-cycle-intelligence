"""Prevent an incomplete cached graph from being published by GitHub Actions."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / 'data' / 'dashboard_cache' / 'rotation_graphs'
REGIONS = ('global', 'usa', 'india')
PERIODS = ('1m', '3m', '6m')


def validate() -> None:
    errors: list[str] = []
    manifest_path = STORE / 'manifest.json'
    if not manifest_path.is_file():
        raise SystemExit(f'Missing manifest: {manifest_path}')
    report = json.loads(manifest_path.read_text(encoding='utf-8'))
    entries = report.get('regions', {})
    for region in REGIONS:
        for period in PERIODS:
            key = f'{region}_{period}'
            entry = entries.get(key)
            if not isinstance(entry, dict):
                errors.append(f'{key}: no manifest entry')
                continue
            if entry.get('error'):
                errors.append(f"{key}: builder error: {entry['error']}")
            for kind, required in (
                ('edges', {'company_key', 'quadrant', 'kind', 'source_id'}),
                ('signals', {'quadrant', 'kind', 'source_id', 'label'}),
            ):
                path = STORE / f'{key}_{kind}.csv'
                if not path.is_file():
                    errors.append(f'{key}: missing {path.name}')
                    continue
                try:
                    frame = pd.read_csv(path)
                    absent = required - set(frame.columns)
                    if absent:
                        errors.append(f'{key}: {path.name} missing columns: {sorted(absent)}')
                    print(f'{key}: {kind}: {len(frame)} rows')
                except Exception as exc:
                    errors.append(f'{key}: unreadable {path.name}: {exc}')
    if errors:
        raise SystemExit('Knowledge Graph cache validation failed:\n' + '\n'.join(errors))
    print('Success: all 9 region/period snapshots validated. Empty graphs may reflect absent source data.')


if __name__ == '__main__':
    validate()
