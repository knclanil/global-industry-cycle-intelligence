"""Offline SEC facts resolver shared by USA build jobs (never makes HTTP requests)."""
from __future__ import annotations
import json
from pathlib import Path


def ticker_directory(root: Path) -> dict[str, int]:
    """Map only unambiguous official SEC ticker -> CIK identifiers."""
    sources = [root / 'data/fundamentals/sec_company_directory.json',
               root / 'data/sec_cache/company_tickers.json']
    directory = {}
    for path in sources:
        if not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            continue
        values = raw.values() if isinstance(raw, dict) else raw if isinstance(raw, list) else []
        by_ticker = {}
        for item in values:
            if not isinstance(item, dict):
                continue
            try:
                symbol = str(item['ticker']).strip().upper().replace('.', '-')
                cik = int(item['cik_str'])
            except (KeyError, ValueError, TypeError):
                continue
            by_ticker.setdefault(symbol, set()).add(cik)
        directory.update({s: next(iter(ids)) for s, ids in by_ticker.items() if len(ids) == 1})
    return directory


def cached_companyfacts(root: Path, ticker: str, directory: dict[str, int]):
    """Read already-published CompanyFacts by official CIK; no ticker guesses."""
    cik = directory.get(str(ticker).strip().upper().replace('.', '-'))
    if cik is None:
        raise ValueError('No unique SEC CIK match in cached official ticker directory')
    for path in (root / f'data/fundamentals/facts_{cik:010d}.json',
                 root / f'data/sec_cache/CIK{cik:010d}.json'):
        if not path.is_file():
            continue
        try:
            raw = json.loads(path.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            continue
        if int(raw.get('cik', -1)) == cik and isinstance(raw.get('facts'), dict):
            return raw, cik
    raise ValueError('SEC CompanyFacts not cached for verified CIK')
