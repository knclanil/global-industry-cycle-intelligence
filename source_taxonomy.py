"""Source taxonomy for graph display. A category mapping is not a rotation signal.

Designed to group all NSE index/ETF source titles while preserving each original
source identity and its verified constituent membership.
"""
from __future__ import annotations
import re
from dataclasses import dataclass

# Explicit ETF classifications override generic "ETF" categories.
# Name matching is case-insensitive and whitespace-normalized; do not use loose
# substring matches for these two instrument-specific exceptions.
ETF_OVERRIDES = {
    'ishares russell 2000 etf': ('factor', 'Small Cap'),
    'ishares global comm services etf': ('sector', 'Communications'),
    'ishares global communication services etf': ('sector', 'Communications'),
}

NEW_SECTORS = {
    'nifty_oil_gas': 'Nifty Oil & Gas',
    'nifty_india_defence': 'Nifty India Defence',
    'nifty_india_manufacturing': 'Nifty India Manufacturing',
}

# Order gives longest/specific expressions precedence. Match complete words only.
FACTOR_RULES = (
    ('Low Volatility', (r'\blow\s+volatility\b', r'\bminimum\s+volatility\b', r'\bmin\s+vol\b')),
    ('Momentum', (r'\bmomentum\b',)),
    ('Quality', (r'\bquality\b',)),
    ('Value', (r'\bvalue\b',)),
    ('Growth', (r'\bgrowth\b',)),
    ('Alpha', (r'\balpha\b',)),
    ('Dividend', (r'\bdividend\b',)),
    ('Equal Weight', (r'\bequal\s+weight(?:ed)?\b',)),
    ('Small Cap', (r'\bsmall\s+cap\b', r'\bsmall\s+capitali[sz]ation\b')),
    ('Size', (r'\bsize\b',)),
    ('Multi-Factor', (r'\bmulti[\s-]*factor\b',)),
)

@dataclass(frozen=True)
class TaxonomyResult:
    kind: str
    family: str
    status: str
    note: str


def normalize(value: object) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'[_-]+', ' ', str(value or ''))).strip()


def classify_source(name: str, *, slug: str = '', category: str = '', family: str = '') -> TaxonomyResult:
    """Classify display taxonomy, never inventing market price or quadrant data."""
    name_norm = normalize(name)
    override = ETF_OVERRIDES.get(name_norm.casefold())
    if override is not None:
        kind, group = override
        return TaxonomyResult(kind, group, 'mapped',
                              'Explicit ETF source taxonomy override; does not imply holdings or rotation')
    slug_norm = normalize(slug)
    category_norm = normalize(category).casefold()
    if slug in NEW_SECTORS or any(name_norm.casefold() == label.casefold() for label in NEW_SECTORS.values()):
        canonical = NEW_SECTORS[slug] if slug in NEW_SECTORS else next(v for v in NEW_SECTORS.values() if v.casefold() == name_norm.casefold())
        return TaxonomyResult('sector', canonical, 'mapped', 'Named thematic/sector group requested by operator')

    # Explicit NSE factor/strategy metadata is stronger than name heuristics.
    if category_norm in ('factor', 'strategy'):
        text = f'{name_norm} {slug_norm}'
        groups = [label for label, patterns in FACTOR_RULES if any(re.search(p, text, re.I) for p in patterns)]
        if len(set(groups)) == 1:
            return TaxonomyResult('factor', groups[0], 'mapped', 'Source-title factor family; not a rotation/index identity')
        if len(set(groups)) > 1:
            # Explicit family can disambiguate e.g. dividend growth titles.
            fam = normalize(family)
            if fam and any(fam.casefold() == g.casefold() for g in groups):
                return TaxonomyResult('factor', fam, 'mapped', 'Explicit family disambiguates factor source title')
            return TaxonomyResult('factor', '', 'ambiguous', f'Multiple possible factor families: {", ".join(groups)}')
        if normalize(family):
            return TaxonomyResult('factor', normalize(family), 'mapped', 'Source-provided factor family')
        return TaxonomyResult('factor', '', 'unmapped', 'No recognizable factor name')

    if category_norm == 'sector':
        return TaxonomyResult('sector', name_norm, 'mapped', 'Source-provided sector classification')
    if category_norm == 'thematic':
        return TaxonomyResult('sector', name_norm, 'mapped', 'Thematic group displayed under sectors')

    # For other sources, do not infer factor from a random company/fund name.
    if category_norm:
        return TaxonomyResult(category_norm, '', 'unmapped', 'Unsupported source category')
    return TaxonomyResult('', '', 'unmapped', 'Missing source category; avoid guessing')


def build_india_taxonomy():
    """Return one row per official NSE constituent source in existing repository."""
    import pandas as pd
    from india_constituents import INDIA_INDICES
    rows = []
    for definition in INDIA_INDICES:
        result = classify_source(definition.name, slug=definition.slug,
                                 category=definition.category, family=definition.family)
        rows.append({
            'region': 'India', 'source_id': definition.slug,
            'source_name': definition.name, 'original_category': definition.category,
            'kind': result.kind, 'family': result.family,
            'mapping_status': result.status, 'mapping_note': result.note,
            'rotation': '', 'rotation_status': 'requires matching validated price series',
            'constituents_file': definition.filename,
        })
    return pd.DataFrame(rows)
