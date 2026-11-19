"""Focused source & aggregation checks; all example constituents are synthetic."""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from india_constituents import (
    INDIA_INDICES, INDEX_BY_SLUG, parse_nse_csv, consolidate_memberships,
)
from scripts.refresh_india_constituents import refresh


def sample(names=("Example Holdings", "Example Technologies")):
    return ("Company Name,Industry,Symbol,Series,ISIN Code\n"
            f"{names[0]},Financial Services,EXHLD,EQ,INE000A01000\n"
            f"{names[1]},Information Technology,EXTEC,EQ,INE000A01001\n").encode()


def test_index_catalogue_has_exact_31_user_urls():
    assert len(INDIA_INDICES) == 31
    assert len({i.slug for i in INDIA_INDICES}) == 31
    assert sum(i.category in ("Sector", "Thematic") for i in INDIA_INDICES) == 15
    assert sum(i.category in ("Factor", "Strategy") for i in INDIA_INDICES) == 16
    assert INDEX_BY_SLUG["nifty50_value_20"].url.endswith("ind_Nifty50_Value20.csv")


def test_source_rows_dedup_across_indices_preserve_all_memberships():
    value_50 = INDEX_BY_SLUG["nifty500_value_50"]
    value_30 = INDEX_BY_SLUG["nifty200_value_30"]
    bank = INDEX_BY_SLUG["nifty_bank"]
    rows = sum((parse_nse_csv(sample(), idx) for idx in (value_50, value_30, bank)), [])
    memberships, companies = consolidate_memberships(rows)
    assert len(companies) == 2
    assert len(memberships) == 6
    example = next(x for x in companies if x["symbol"] == "EXHLD")
    assert example["factor_families"] == "Value"
    assert example["factor_index_count"] == 2
    assert example["sector_indices"] == "Nifty Bank"
    assert "Value · Nifty 200" in example["factor_universe_memberships"]
    assert "Value · Nifty 500" in example["factor_universe_memberships"]
    assert example["known_weight_entries"] == 0
    assert all(x["weight_pct"] == "" for x in memberships)


def test_missing_isin_joins_unique_symbol_only():
    a = parse_nse_csv(sample(), INDEX_BY_SLUG["nifty500_value_50"])
    b = parse_nse_csv(sample().replace(b"INE000A01000", b""), INDEX_BY_SLUG["nifty200_value_30"])
    memberships, companies = consolidate_memberships(a + b)
    assert len(companies) == 2
    assert len(memberships) == 4
    matched = [r for r in memberships if r["symbol"] == "EXHLD"]
    assert len({r["company_key"] for r in matched}) == 1
    assert {r["identity_basis"] for r in matched} == {"source_isin", "unique_symbol_to_isin"}


def test_forged_html_not_accepted():
    try:
        parse_nse_csv(b"<html><title>Forbidden</title></html>", INDEX_BY_SLUG["nifty_bank"])
    except ValueError as exc:
        assert "HTML" in str(exc)
    else:
        raise AssertionError("HTML must not become constituent data")


def test_manual_refresh_keeps_previous_valid_snapshot_after_bad_import(tmp_path):
    manual = tmp_path / "manual"
    manual.mkdir()
    (manual / "nifty500_value_50.csv").write_bytes(sample())
    data_dir = tmp_path / "data"
    first = refresh(data_dir=data_dir, offline=True, from_dir=manual,
                    selected={"nifty500_value_50"}, delay=0)
    assert first["loaded_indices"] == 1
    assert first["unique_companies_or_securities"] == 2
    assert first["index_constituent_memberships"] == 2
    (manual / "nifty500_value_50.csv").write_bytes(b"<html>403</html>")
    second = refresh(data_dir=data_dir, offline=True, from_dir=manual,
                     selected={"nifty500_value_50"}, delay=0)
    assert second["loaded_indices"] == 1
    assert second["unique_companies_or_securities"] == 2
    assert second["failed_indices"] == 1
    assert (data_dir / "snapshots" / "nifty500_value_50.csv").read_bytes() == sample()


def test_explicit_weights_only():
    idx = INDEX_BY_SLUG["nifty_bank"]
    weighted = b"Company Name,Industry,Symbol,Series,ISIN Code,Weightage (%)\nExample Holdings,Banks,EXHLD,EQ,INE000A01000,6.3\n"
    parsed = parse_nse_csv(weighted, idx)
    assert parsed[0]["weight_pct"] == "6.3"
    assert parsed[0]["weight_source"] == "nse_constituent_csv"


def test_import_with_original_nse_filename(tmp_path):
    manual = tmp_path / "manual"
    manual.mkdir()
    index = INDEX_BY_SLUG["nifty500_value_50"]
    (manual / index.filename).write_bytes(sample())
    report = refresh(data_dir=tmp_path / "saved", offline=True, from_dir=manual,
                     selected={index.slug}, delay=0)
    assert report["newly_updated_indices"] == 1
    assert report["loaded_indices"] == 1
