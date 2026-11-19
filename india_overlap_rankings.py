"""Transparent, unweighted India index-membership overlap and leadership research.

NSE constituent records are the sole source of index membership.  This module
never infers portfolio weights, market-cap classes, or eligibility-based absences.
Scores are *index-membership breadth/confirmation indicators*, NOT business
quality, past/future performance, or investment recommendations.

Cross-universe repetitions are positive confirmations only. A company excluded
from an index may be ineligible for its parent universe, so missing membership
is never a negative point without separate validated eligibility data.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from typing import Iterable, Mapping

from india_constituents import INDIA_INDICES, INDEX_BY_SLUG

# Related NSE sector indices are one group for *sector breadth*. Original
# memberships are retained without modification for audit and drill-down.
SECTOR_GROUPS = {
    "nifty_bank": "Banking & Financials",
    "nifty_psu_bank": "Banking & Financials",
    "nifty_financial_services": "Banking & Financials",
    "nifty_oil_gas": "Energy",
    "nifty_energy": "Energy",
    "nifty_media": "Media",
    "nifty_pharma": "Pharmaceuticals",
    "nifty_it": "Information Technology",
    "nifty_realty": "Realty",
    "nifty_fmcg": "FMCG",
    "nifty_metal": "Metals",
    "nifty_auto": "Automobiles",
}

LEADERSHIP_FIELDS = [
    "company_key", "company_name", "symbol", "isin", "industry",
    "factor_families", "factor_indices", "factor_universes",
    "sector_indices", "thematic_indices", "strategy_indices",
    "sector_groups", "factor_family_count", "factor_index_count",
    "repeat_factor_memberships", "repeat_confirmed_families",
    "sector_group_count", "sector_index_count", "thematic_index_count",
    "index_count", "known_weight_entries", "factor_score", "sector_score",
    "combined_score", "factor_rank", "sector_rank", "combined_rank",
    "factor_and_sector", "source_first_utc", "source_latest_utc",
]
INDEX_OVERLAP_FIELDS = [
    "factor_family", "index_a", "index_b", "parent_a", "parent_b",
    "companies_a", "companies_b", "shared_companies", "union_companies",
    "jaccard_pct", "overlap_a_pct", "overlap_b_pct", "shared_symbols",
]
PATTERN_FIELDS = [
    "factor_family", "source_indices", "parent_universes", "pattern_size",
    "company_count", "company_symbols",
]
SECTOR_FACTOR_FIELDS = [
    "sector_index", "category", "factor_family", "sector_constituents",
    "factor_constituents", "overlap_companies", "pct_of_sector", "company_symbols",
]


def _as_num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _text_list(items: Iterable[str]) -> str:
    return " | ".join(sorted({str(v) for v in items if v}))


def _rank(rows: list[dict], score_key: str, rank_key: str, tie_keys: tuple[str, ...]):
    """Competition ranks: tied scores get same rank, e.g. 1, 1, 3."""
    ranked = sorted((r for r in rows if r[score_key] is not None),
                    key=lambda r: (-r[score_key], *(-int(r[k]) for k in tie_keys),
                                   r["symbol"], r["company_key"]))
    prev_score = None
    current_rank = None
    for pos, row in enumerate(ranked, 1):
        score = row[score_key]
        if score != prev_score:
            current_rank = pos
            prev_score = score
        row[rank_key] = current_rank


def build_leadership(memberships: Iterable[Mapping]) -> dict:
    """Build precomputed rankings and exact overlap evidence from NSE records.

    Factor and sector ranks are independent. Combined score is defined only
    when a company is actually in >=1 Factor and >=1 Sector/Thematic index.
    The Nifty50 Equal Weight Strategy is shown, but excluded from factor score.
    """
    observed: dict[tuple[str, str], dict] = {}
    for raw in memberships:
        slug = str(raw.get("index_slug", "")).strip()
        company = str(raw.get("company_key", "")).strip()
        if not company or slug not in INDEX_BY_SLUG:
            continue
        # Ignore unverified category/family annotations from stale exports:
        # catalogue definitions, not the row, determine group membership.
        row = dict(raw)
        if not row.get("symbol"):
            continue
        index = INDEX_BY_SLUG[slug]
        row["index_name"] = index.name
        row["category"] = index.category
        row["factor_family"] = index.family
        row["parent_universe"] = index.parent_universe
        observed[(company, slug)] = row

    by_company = defaultdict(list)
    by_index = defaultdict(set)
    company_symbols = {}
    for (key, slug), row in observed.items():
        by_company[key].append(row)
        by_index[slug].add(key)
        company_symbols[key] = str(row["symbol"])

    factor_indices = {idx.slug for idx in INDIA_INDICES
                      if idx.category == "Factor" and by_index.get(idx.slug)}
    factor_families = {INDEX_BY_SLUG[s].family for s in factor_indices}
    family_to_slugs = defaultdict(set)
    for s in factor_indices:
        family_to_slugs[INDEX_BY_SLUG[s].family].add(s)

    companies = []
    for key, records in by_company.items():
        records.sort(key=lambda r: (0 if r.get("isin") else 1, r["index_slug"]))
        primary = records[0]
        factors = [r for r in records if r["category"] == "Factor"]
        sectors = [r for r in records if r["category"] == "Sector"]
        themes = [r for r in records if r["category"] == "Thematic"]
        strategies = [r for r in records if r["category"] == "Strategy"]
        counts = Counter(r["factor_family"] for r in factors)
        family_count = len(counts)
        extra_members = sum(max(0, n - 1) for n in counts.values())
        repeated_families = sum(n >= 2 for n in counts.values())
        # A cap of four families and three extra family-index observations
        # stops one family's many variant indices dominating all others.
        factor_score = (round(70 * min(family_count / 4, 1) +
                              30 * min(extra_members / 3, 1), 2)
                        if factors else None)
        buckets = {SECTOR_GROUPS.get(r["index_slug"], r["index_name"])
                   for r in sectors}
        # Thematic indices are a distinct evidence type; do not conflate
        # them with a mutually exclusive GICS sector taxonomy.
        buckets.update("Theme: " + r["index_name"] for r in themes)
        has_sector = bool(sectors or themes)
        # 65 for evidence in at least one sector/theme group, 0..25 extra
        # breadth for distinct groups, 10 for sector+thematic agreement.
        sector_score = (round(65 + 25 * min(max(len(buckets)-1, 0) / 2, 1)
                              + (10 if sectors and themes else 0), 2)
                        if has_sector else None)
        combined = None
        if factor_score is not None and sector_score is not None:
            combined = round(max(0, min(100, (factor_score + sector_score) / 2
                                        - 0.20 * abs(factor_score - sector_score))), 2)
        dates = sorted(r["snapshot_utc"] for r in records if r.get("snapshot_utc"))
        companies.append({
            "company_key": key, "company_name": primary.get("company_name", ""),
            "symbol": primary.get("symbol", ""),
            "isin": next((r["isin"] for r in records if r.get("isin")), ""),
            "industry": _text_list(r.get("industry", "") for r in records),
            "factor_families": _text_list(counts),
            "factor_indices": _text_list(r["index_name"] for r in factors),
            "factor_universes": _text_list(
                r["factor_family"] + " · " + r["parent_universe"] for r in factors),
            "sector_indices": _text_list(r["index_name"] for r in sectors),
            "thematic_indices": _text_list(r["index_name"] for r in themes),
            "strategy_indices": _text_list(r["index_name"] for r in strategies),
            "sector_groups": _text_list(buckets),
            "factor_family_count": family_count,
            "factor_index_count": len(factors),
            "repeat_factor_memberships": extra_members,
            "repeat_confirmed_families": repeated_families,
            "sector_group_count": len(buckets),
            "sector_index_count": len(sectors),
            "thematic_index_count": len(themes),
            "index_count": len(records),
            "known_weight_entries": sum(_as_num(r.get("weight_pct")) is not None for r in records),
            "factor_score": factor_score, "sector_score": sector_score,
            "combined_score": combined, "factor_rank": None,
            "sector_rank": None, "combined_rank": None,
            "factor_and_sector": int(factor_score is not None and sector_score is not None),
            "source_first_utc": dates[0] if dates else "",
            "source_latest_utc": dates[-1] if dates else "",
        })

    _rank(companies, "factor_score", "factor_rank",
          ("factor_family_count", "repeat_factor_memberships"))
    _rank(companies, "sector_score", "sector_rank", ("sector_group_count",))
    _rank(companies, "combined_score", "combined_rank",
          ("factor_family_count", "sector_group_count"))
    companies.sort(key=lambda r: (r["combined_rank"] is None,
                                  r["combined_rank"] or 10**9, r["symbol"], r["company_key"]))

    pairwise = []
    patterns = []
    for family in sorted(family_to_slugs):
        slugs = sorted(family_to_slugs[family])
        for a, b in combinations(slugs, 2):
            left, right = by_index[a], by_index[b]
            both = left & right
            union = left | right
            pairwise.append({
                "factor_family": family,
                "index_a": INDEX_BY_SLUG[a].name, "index_b": INDEX_BY_SLUG[b].name,
                "parent_a": INDEX_BY_SLUG[a].parent_universe,
                "parent_b": INDEX_BY_SLUG[b].parent_universe,
                "companies_a": len(left), "companies_b": len(right),
                "shared_companies": len(both), "union_companies": len(union),
                "jaccard_pct": round(100 * len(both) / len(union), 2) if union else 0,
                "overlap_a_pct": round(100 * len(both) / len(left), 2) if left else 0,
                "overlap_b_pct": round(100 * len(both) / len(right), 2) if right else 0,
                "shared_symbols": _text_list(company_symbols[k] for k in both),
            })
        # Exact membership-pattern groups: company appears in precisely the
        # listed indices of this factor family, not the other family indices.
        all_keys = set().union(*(by_index[s] for s in slugs))
        groupings = defaultdict(list)
        for key in all_keys:
            pattern = tuple(s for s in slugs if key in by_index[s])
            groupings[pattern].append(key)
        for pattern, keys in groupings.items():
            patterns.append({
                "factor_family": family,
                "source_indices": _text_list(INDEX_BY_SLUG[s].name for s in pattern),
                "parent_universes": _text_list(INDEX_BY_SLUG[s].parent_universe for s in pattern),
                "pattern_size": len(pattern), "company_count": len(keys),
                "company_symbols": _text_list(company_symbols[k] for k in keys),
            })

    sector_factor = []
    sector_slugs = sorted(s for s in by_index if INDEX_BY_SLUG[s].category in ("Sector", "Thematic"))
    family_to_keys = {family: set().union(*(by_index[s] for s in slugs))
                      for family, slugs in family_to_slugs.items()}
    for slug in sector_slugs:
        sector = by_index[slug]
        for family in sorted(family_to_keys):
            factor = family_to_keys[family]
            both = sector & factor
            sector_factor.append({
                "sector_index": INDEX_BY_SLUG[slug].name,
                "category": INDEX_BY_SLUG[slug].category,
                "factor_family": family,
                "sector_constituents": len(sector),
                "factor_constituents": len(factor),
                "overlap_companies": len(both),
                "pct_of_sector": round(100 * len(both) / len(sector), 2) if sector else 0,
                "company_symbols": _text_list(company_symbols[k] for k in both),
            })

    return {
        "companies": companies,
        "factor_index_overlaps": sorted(pairwise, key=lambda r: (r["factor_family"], -r["shared_companies"], r["index_a"])),
        "factor_membership_patterns": sorted(patterns, key=lambda r: (r["factor_family"], -r["company_count"], r["source_indices"])),
        "sector_factor_overlaps": sorted(sector_factor, key=lambda r: (r["sector_index"], r["factor_family"])),
        "summary": {
            "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_membership_records": len(observed),
            "companies": len(companies),
            "active_factor_families": len(factor_families),
            "indices_with_memberships": len(by_index),
            "factor_covered_companies": sum(r["factor_score"] is not None for r in companies),
            "sector_or_theme_covered_companies": sum(r["sector_score"] is not None for r in companies),
            "dual_covered_companies": sum(r["combined_score"] is not None for r in companies),
            "factor_pair_comparisons": len(pairwise),
            "weight_records_observed": sum(r["known_weight_entries"] for r in companies),
            "methodology": "Verified index membership only; no estimated weights, absent-universe penalties, financial quality, or price signals.",
            "score_version": "india_membership_v1",
        },
    }
