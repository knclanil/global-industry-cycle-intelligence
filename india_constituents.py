"""NSE index constituents: source catalogue, validation and membership aggregation.

No leadership scores, eligibility penalties, imputed constituent weights or
market-cap classifications are calculated here. Constituent membership != weight.
All input is fetched/snapshotted by scripts/refresh_india_constituents.py; the
Streamlit UI only reads the committed CSV exports.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO
import re
from typing import Dict, Iterable, List, Optional, Sequence

BASE_URL = "https://www.niftyindices.com/IndexConstituent/"


@dataclass(frozen=True)
class IndexDefinition:
    slug: str
    name: str
    filename: str
    category: str  # Sector, Thematic, Factor, Strategy
    family: str = ""
    parent_universe: str = "Not specified"

    @property
    def url(self) -> str:
        return BASE_URL + self.filename


def _idx(slug, name, filename, category, family="", parent="Not specified"):
    return IndexDefinition(slug, name, filename, category, family, parent)


# Exact 31 filenames supplied by the user; the original double-slash URLs have
# been normalized to a single path separator without changing the filenames.
INDIA_INDICES: tuple[IndexDefinition, ...] = (
    _idx("nifty_media", "Nifty Media", "ind_niftymedialist.csv", "Sector"),
    _idx("nifty_psu_bank", "Nifty PSU Bank", "ind_niftypsubanklist.csv", "Sector"),
    _idx("nifty_bank", "Nifty Bank", "ind_niftybanklist.csv", "Sector"),
    _idx("nifty_financial_services", "Nifty Financial Services", "ind_niftyfinancelist.csv", "Sector"),
    _idx("nifty_pharma", "Nifty Pharma", "ind_niftypharmalist.csv", "Sector"),
    _idx("nifty_it", "Nifty IT", "ind_niftyitlist.csv", "Sector"),
    _idx("nifty_realty", "Nifty Realty", "ind_niftyrealtylist.csv", "Sector"),
    _idx("nifty_fmcg", "Nifty FMCG", "ind_niftyfmcglist.csv", "Sector"),
    _idx("nifty_oil_gas", "Nifty Oil & Gas", "ind_niftyoilgaslist.csv", "Sector"),
    _idx("nifty_metal", "Nifty Metal", "ind_niftymetallist.csv", "Sector"),
    _idx("nifty_auto", "Nifty Auto", "ind_niftyautolist.csv", "Sector"),
    _idx("nifty_infrastructure", "Nifty Infrastructure", "ind_niftyinfralist.csv", "Thematic"),
    _idx("nifty_india_defence", "Nifty India Defence", "ind_niftyindiadefence_list.csv", "Thematic"),
    _idx("nifty_energy", "Nifty Energy", "ind_niftyenergylist.csv", "Sector"),
    _idx("nifty_india_manufacturing", "Nifty India Manufacturing", "ind_niftyindiamanufacturing_list.csv", "Thematic"),
    _idx("nifty500_low_volatility_50", "Nifty500 Low Volatility 50", "ind_nifty500LowVolatility50_list.csv", "Factor", "Low Volatility", "Nifty 500"),
    _idx("nifty500_momentum_50", "Nifty500 Momentum 50", "ind_nifty500Momentum50_list.csv", "Factor", "Momentum", "Nifty 500"),
    _idx("nifty500_quality_50", "Nifty500 Quality 50", "ind_nifty500Quality50_list.csv", "Factor", "Quality", "Nifty 500"),
    _idx("nifty500_value_50", "Nifty500 Value 50", "ind_nifty500Value50_list.csv", "Factor", "Value", "Nifty 500"),
    _idx("nifty200_momentum_30", "Nifty200 Momentum 30", "ind_nifty200Momentum30_list.csv", "Factor", "Momentum", "Nifty 200"),
    _idx("nifty200_value_30", "Nifty200 Value 30", "ind_nifty200Value30_list.csv", "Factor", "Value", "Nifty 200"),
    _idx("nifty200_alpha_30", "Nifty200 Alpha 30", "ind_nifty200alpha30_list.csv", "Factor", "Alpha", "Nifty 200"),
    _idx("nifty200_quality_30", "Nifty200 Quality 30", "ind_nifty200Quality30_list.csv", "Factor", "Quality", "Nifty 200"),
    _idx("nifty100_low_volatility_30", "Nifty100 Low Volatility 30", "ind_Nifty100LowVolatility30list.csv", "Factor", "Low Volatility", "Nifty 100"),
    _idx("nifty_alpha_index", "Nifty Alpha Index", "ind_nifty_Alpha_Index.csv", "Factor", "Alpha"),
    _idx("nifty_low_volatility_50", "Nifty Low Volatility 50", "nifty_low_Volatility50_Index.csv", "Factor", "Low Volatility"),
    _idx("nifty_dividend_opportunities_50", "Nifty Dividend Opportunities 50", "ind_niftydivopp50list.csv", "Factor", "Dividend"),
    _idx("nifty100_quality_30", "Nifty100 Quality 30", "ind_nifty100Quality30list.csv", "Factor", "Quality", "Nifty 100"),
    _idx("nifty500_growth_50", "Nifty500 Growth 50", "ind_nifty500Growth50list.csv", "Factor", "Growth", "Nifty 500"),
    _idx("nifty50_equal_weight", "Nifty50 Equal Weight", "ind_Nifty50EqualWeight.csv", "Strategy", "Equal Weight", "Nifty 50"),
    _idx("nifty50_value_20", "Nifty50 Value 20", "ind_Nifty50_Value20.csv", "Factor", "Value", "Nifty 50"),
)
INDEX_BY_SLUG = {item.slug: item for item in INDIA_INDICES}
INDEX_BY_NAME = {item.name: item for item in INDIA_INDICES}
FACTOR_FAMILIES = tuple(sorted({i.family for i in INDIA_INDICES if i.category == "Factor"}))

MEMBERSHIP_FIELDS = [
    "company_key", "company_name", "symbol", "isin", "identity_basis",
    "industry", "series", "index_slug", "index_name", "category", "factor_family",
    "parent_universe", "weight_pct", "weight_source", "source_url",
    "snapshot_utc", "source_type",
]
COMPANY_FIELDS = [
    "company_key", "company_name", "symbol", "isin", "identity_basis",
    "industry", "factor_families", "factor_indices", "factor_universes",
    "factor_universe_memberships", "sector_indices", "thematic_indices",
    "strategy_indices", "all_indices", "factor_family_count", "factor_index_count",
    "sector_index_count", "thematic_index_count", "index_count", "known_weight_entries",
]
STATUS_FIELDS = [
    "index_slug", "index_name", "category", "factor_family", "parent_universe",
    "status", "constituent_count", "retrieved_utc", "snapshot_utc",
    "source_type", "source_url", "error",
    "change_status", "additions", "removals", "weight_changes", "symbol_changes",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _header_lookup(headers: Sequence[str]) -> dict:
    names = {_label(x): x for x in headers}
    def find(*options):
        for option in options:
            if _label(option) in names:
                return names[_label(option)]
        return None
    return {
        "company_name": find("Company Name", "Company", "Security Name", "Name of Company", "Name of the Company"),
        "symbol": find("Symbol", "NSE Symbol", "Ticker", "Trading Symbol"),
        "isin": find("ISIN Code", "ISIN", "ISIN Number", "ISIN No"),
        "industry": find("Industry", "Sector", "Industry Name"),
        "series": find("Series", "Security Series"),
        "weight_pct": find("Weightage", "Weightage (%)", "Weight (%)", "Weight %", "Weightage %", "Index Weight (%)", "Weight Percent", "Weightage in %"),
    }


def _decode(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            out = raw.decode(encoding)
            if "\x00" not in out:
                return out
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def _weight_pct(value: str) -> str:
    """Only accept columns explicitly labelled as a percent/weight field.

    NSE CSVs normally omit weights. Never infer them from index position.
    """
    raw = str(value or "").strip().replace(",", "")
    if not raw or raw in ("-", "--", "NA", "N/A"):
        return ""
    try:
        number = float(raw.removesuffix("%"))
        if 0 <= number <= 100:
            return f"{number:.6g}"
    except ValueError:
        pass
    return ""


def parse_nse_csv(raw: bytes, index: IndexDefinition, snapshot_utc: Optional[str] = None,
                  source_type: str = "direct_nse") -> List[dict]:
    """Validate and normalize constituent rows; reject HTML/invalid responses."""
    if not raw:
        raise ValueError("Empty download")
    text = _decode(raw)
    if "<html" in text[:1000].lower() or "<!doctype" in text[:1000].lower():
        raise ValueError("Received HTML instead of constituent CSV")
    lines = list(csv.reader(StringIO(text)))
    header_no, headers, fields = None, None, None
    for ix, row in enumerate(lines[:20]):
        probe = _header_lookup(row)
        if probe["symbol"] and probe["company_name"]:
            header_no, headers, fields = ix, row, probe
            break
    if header_no is None:
        raise ValueError("Expected constituent columns 'Company Name' and 'Symbol' not found")
    if len(lines) - header_no <= 1:
        raise ValueError("No constituent data rows")
    stamp = snapshot_utc or utc_now()
    results = []
    for row in lines[header_no + 1:]:
        if not row or not any(cell.strip() for cell in row):
            continue
        data = dict(zip(headers, row + [""] * max(0, len(headers)-len(row))))
        get = lambda col: (data.get(fields[col], "") if fields[col] else "").strip()
        symbol = re.sub(r"\s+", "", get("symbol")).upper()
        name = " ".join(get("company_name").split())
        if not symbol or not name:
            continue
        isin = get("isin").upper().replace(" ", "")
        if isin and not re.fullmatch(r"IN[A-Z0-9]{10}", isin):
            isin = ""  # Don't use an invalid ISIN to merge distinct companies.
        weight = _weight_pct(get("weight_pct"))
        results.append({
            "company_key": "", "company_name": name, "symbol": symbol,
            "isin": isin, "identity_basis": "", "industry": get("industry"),
            "series": get("series"), "index_slug": index.slug, "index_name": index.name,
            "category": index.category, "factor_family": index.family,
            "parent_universe": index.parent_universe, "weight_pct": weight,
            "weight_source": "nse_constituent_csv" if weight else "",
            "source_url": index.url, "snapshot_utc": stamp,
            "source_type": source_type,
        })
    if not results:
        raise ValueError("No valid company/symbol rows")
    # Duplicate lines within the same source index do not create memberships.
    unique = {}
    for record in results:
        unique[(record["isin"] or record["symbol"], record["index_slug"])] = record
    return list(unique.values())


def consolidate_memberships(records: Iterable[dict]) -> tuple[List[dict], List[dict]]:
    """Unify shared constituents by ISIN, with safe unique-symbol fallback.

    All raw index memberships survive. We do not assume that Nifty 500 means
    Small Cap, or that absence from an index means an eligible rejection.
    """
    rows = [dict(r) for r in records]
    symbol_to_isins: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        if r.get("isin"):
            symbol_to_isins[r["symbol"].upper()].add(r["isin"].upper())
    for r in rows:
        isin = r.get("isin", "").upper()
        symbol = r.get("symbol", "").upper()
        if isin:
            r["company_key"] = f"ISIN:{isin}"
            r["identity_basis"] = "source_isin"
        elif len(symbol_to_isins[symbol]) == 1:
            r["company_key"] = "ISIN:" + next(iter(symbol_to_isins[symbol]))
            r["identity_basis"] = "unique_symbol_to_isin"
        else:
            r["company_key"] = "SYMBOL:" + symbol
            r["identity_basis"] = "symbol_only"

    memberships = {}
    for r in rows:
        key = (r["company_key"], r["index_slug"])
        if key not in memberships or (r["isin"] and not memberships[key].get("isin")):
            memberships[key] = r
    rows = sorted(memberships.values(), key=lambda x: (x["company_key"], x["index_slug"]))
    by_company: dict[str, list] = defaultdict(list)
    for r in rows:
        by_company[r["company_key"]].append(r)
    companies = []
    for key, matches in sorted(by_company.items()):
        # Prefer rows with an actual ISIN; preserve source company names.
        named = sorted(matches, key=lambda r: (bool(r["isin"]), len(r["company_name"])), reverse=True)
        main = named[0]
        categories = defaultdict(list)
        for r in matches:
            categories[r["category"]].append(r)
        factors = categories["Factor"]
        known_weights = [r for r in matches if r["weight_pct"] != ""]
        families = sorted({r["factor_family"] for r in factors if r["factor_family"]})
        universe_pairs = sorted({f"{r['factor_family']} · {r['parent_universe']}" for r in factors})
        def join_unique(values):
            return " | ".join(sorted({x for x in values if x}))
        companies.append({
            "company_key": key, "company_name": main["company_name"],
            "symbol": main["symbol"], "isin": next((r["isin"] for r in matches if r["isin"]), ""),
            "identity_basis": "symbol_only" if key.startswith("SYMBOL:") else "isin_matched",
            "industry": join_unique(r["industry"] for r in matches),
            "factor_families": " | ".join(families),
            "factor_indices": join_unique(r["index_name"] for r in factors),
            "factor_universes": join_unique(r["parent_universe"] for r in factors),
            "factor_universe_memberships": " | ".join(universe_pairs),
            "sector_indices": join_unique(r["index_name"] for r in categories["Sector"]),
            "thematic_indices": join_unique(r["index_name"] for r in categories["Thematic"]),
            "strategy_indices": join_unique(r["index_name"] for r in categories["Strategy"]),
            "all_indices": join_unique(r["index_name"] for r in matches),
            "factor_family_count": len(families), "factor_index_count": len(factors),
            "sector_index_count": len(categories["Sector"]),
            "thematic_index_count": len(categories["Thematic"]),
            "index_count": len(matches), "known_weight_entries": len(known_weights),
        })
    return rows, companies
