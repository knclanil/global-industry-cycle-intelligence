"""Scheduled daily verification. Writes a small JSON status artifact, not a database."""
import json
from datetime import date, timedelta, datetime, timezone
from pathlib import Path
from market_data import download, validate


def main():
    today = date.today()
    report = validate(download(today - timedelta(days=45), today), today)
    report['checked_at_utc'] = datetime.now(timezone.utc).isoformat()
    output = Path('data_quality_report.json')
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    if report['status'] == 'FAIL':
        raise SystemExit('Critical market-data integrity check failed')

if __name__ == '__main__':
    main()
