"""Run from repository root: python scripts/build_source_taxonomy.py"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from source_taxonomy import build_india_taxonomy

if __name__ == '__main__':
    frame = build_india_taxonomy()
    destination = ROOT / 'data' / 'dashboard_cache' / 'rotation_graphs' / 'india_source_taxonomy.csv'
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)
    print(f'Wrote {len(frame)} index source classifications to {destination}')
    print(frame.groupby(['kind', 'mapping_status']).size().to_string())
    print(f'Unmapped or ambiguous: {sum(frame.mapping_status != "mapped")}')
