"""Synthetic fixtures only. These are not claims about real NSE changes."""
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from india_constituents import INDEX_BY_SLUG
from india_holdings_history import compare_snapshots
from scripts.refresh_india_constituents import refresh

INDEX = INDEX_BY_SLUG["nifty500_value_50"]


def _raw(rows, *, weighted=False):
    weight_head = ",Weightage (%)" if weighted else ""
    lines = ["Company Name,Industry,Symbol,Series,ISIN Code" + weight_head]
    for name, symbol, isin, weight in rows:
        lines.append(f"{name},Industry,{symbol},EQ,{isin}" + ("," + str(weight) if weighted else ""))
    return ("\n".join(lines) + "\n").encode()


def _row(i, *, symbol=None, weight=""):
    return (f"Example Company {i}", symbol or f"CO{i}", f"INE{i:07d}01", weight)


def _read(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _run(root, rows, *, weighted=False, **opts):
    manual = root / "manual"
    manual.mkdir(exist_ok=True)
    (manual / f"{INDEX.slug}.csv").write_bytes(_raw(rows, weighted=weighted))
    return refresh(data_dir=root / "data", offline=True, from_dir=manual,
                   selected={INDEX.slug}, delay=0, **opts)


def test_baseline_then_new_removed_added_and_idempotence(tmp_path):
    sample = [_row(1), _row(2), _row(3)]
    first = _run(tmp_path, sample)
    assert first["loaded_indices"] == 1
    assert first["total_observed_changes"] == 0
    assert first["history_revisions"] == 1
    assert _read(tmp_path / "data" / "holding_changes.csv") == []

    unchanged = _run(tmp_path, list(reversed(sample)))
    assert unchanged["history_revisions"] == 1
    assert unchanged["changes_this_run"]["added"] == 0

    changed = _run(tmp_path, [_row(1), _row(3), _row(4)])
    assert changed["history_revisions"] == 2
    assert changed["changes_this_run"] == {"added": 1, "removed": 1,
                                            "weight_changed": 0, "symbol_changed": 0}
    events = _read(tmp_path / "data" / "holding_changes.csv")
    assert {(e["change_type"], e["symbol"]) for e in events} == {
        ("Added", "CO4"), ("Removed", "CO2")}
    again = _run(tmp_path, [_row(1), _row(3), _row(4)])
    assert again["history_revisions"] == 2
    assert again["total_observed_changes"] == 2
    assert again["changes_this_run"]["added"] == 0


def test_symbol_isin_and_weight_with_unknown_coverage(tmp_path):
    old = [_row(1, weight="3.21"), _row(2, weight="")]
    first = _run(tmp_path, old, weighted=True)
    assert first["history_revisions"] == 1
    changed = _run(tmp_path, [_row(1, symbol="ONE", weight="3.51"), _row(2, weight="7.0")],
                   weighted=True)
    assert changed["changes_this_run"]["added"] == 0
    assert changed["changes_this_run"]["removed"] == 0
    assert changed["changes_this_run"]["symbol_changed"] == 1
    assert changed["changes_this_run"]["weight_changed"] == 1
    events = _read(tmp_path / "data" / "holding_changes.csv")
    assert {e["change_type"] for e in events} == {"Symbol Changed", "Weight Changed"}
    assert all(e["symbol"] == "ONE" for e in events)
    assert not any(e["symbol"] == "CO2" for e in events), "Missing->known is not a measured weight change"


def test_existing_legacy_raw_snapshot_seeds_real_baseline(tmp_path):
    data = tmp_path / "data"
    snap = data / "snapshots"
    meta = data / "snapshot_meta"
    snap.mkdir(parents=True)
    meta.mkdir()
    (snap / f"{INDEX.slug}.csv").write_bytes(_raw([_row(1), _row(2)]))
    (meta / f"{INDEX.slug}.json").write_text(json.dumps({
        "retrieved_utc": "2026-11-18T12:00:00+00:00", "source_type": "direct_nse"
    }))
    summary = _run(tmp_path, [_row(1), _row(3)])
    assert summary["history_revisions"] == 2
    revisions = _read(data / "index_revisions.csv")
    assert [r["revision_type"] for r in revisions] == ["legacy_baseline", "changed"]
    assert revisions[0]["observed_utc"] == "2026-11-18T12:00:00+00:00"
    assert set(e["change_type"] for e in _read(data / "holding_changes.csv")) == {"Added", "Removed"}


def test_invalid_download_and_suspicious_drop_preserve_data_and_events(tmp_path):
    original = [_row(i) for i in range(1, 21)]
    _run(tmp_path, original)
    changed = _run(tmp_path, original[:2])  # suspicious 20 -> 2 should be blocked
    assert changed["failed_indices"] == 1
    assert changed["total_observed_changes"] == 0
    assert changed["history_revisions"] == 1
    assert changed["index_constituent_memberships"] == 20
    status = next(r for r in _read(tmp_path / "data" / "index_status.csv")
                  if r["index_slug"] == INDEX.slug)
    assert status["status"] == "cached_after_error"
    assert "Suspicious" in status["error"]
    assert status["constituent_count"] == "20"
    manual = tmp_path / "manual" / f"{INDEX.slug}.csv"
    manual.write_bytes(b"<html>403 forbidden</html>")
    failure = refresh(data_dir=tmp_path / "data", offline=True, from_dir=tmp_path / "manual",
                      selected={INDEX.slug}, delay=0)
    assert failure["total_observed_changes"] == 0
    assert failure["index_constituent_memberships"] == 20
    assert failure["history_revisions"] == 1


def test_approved_major_reconstitution_is_logged(tmp_path):
    original = [_row(i) for i in range(1, 21)]
    _run(tmp_path, original)
    update = _run(tmp_path, original[:2], allow_large_changes=True)
    assert update["failed_indices"] == 0
    assert update["changes_this_run"]["removed"] == 18
    assert update["history_revisions"] == 2


def test_history_across_two_indices_and_version_comparison(tmp_path):
    first = INDEX_BY_SLUG["nifty_bank"]
    old_rows = [{"company_name": "Demo A", "symbol": "DEMOA", "isin": "INE000000001",
                 "weight_pct": "", "industry": "", "series": ""}]
    later = old_rows + [{"company_name": "Demo B", "symbol": "DEMOB", "isin": "INE000000002",
                         "weight_pct": "", "industry": "", "series": ""}]
    assert compare_snapshots(old_rows, later)[0]["change_type"] == "Added"
    _run(tmp_path, [_row(1)])
    bank_data = tmp_path / "manual" / f"{first.slug}.csv"
    bank_data.write_bytes(_raw([_row(2)]))
    summary = refresh(data_dir=tmp_path / "data", offline=True, from_dir=tmp_path / "manual",
                      selected={first.slug}, delay=0)
    assert summary["history_revisions"] == 2
    assert summary["total_observed_changes"] == 0
    assert summary["loaded_indices"] == 2


def test_default_fetches_nse_even_when_manual_file_exists(tmp_path):
    class FakeResponse:
        content = _raw([_row(9)])
        def raise_for_status(self):
            pass

    class FakeSession:
        def __init__(self):
            self.called = 0
        def get(self, url, timeout):
            self.called += 1
            return FakeResponse()

    session = FakeSession()
    manual = tmp_path / "manual"
    manual.mkdir()
    (manual / f"{INDEX.slug}.csv").write_bytes(_raw([_row(1)]))
    result = refresh(data_dir=tmp_path / "data", from_dir=manual, offline=False,
                     selected={INDEX.slug}, session=session, delay=0)
    assert session.called == 1
    assert result["index_constituent_memberships"] == 1
    assert _read(tmp_path / "data" / "constituents.csv")[0]["symbol"] == "CO9"


def test_stale_manual_fallback_does_not_reverse_live_snapshot(tmp_path):
    class FakeResponse:
        content = _raw([_row(7)])
        def raise_for_status(self):
            pass

    class Success:
        def get(self, url, timeout):
            return FakeResponse()

    class Failure:
        def get(self, url, timeout):
            raise RuntimeError("simulated NSE access failure")

    manual = tmp_path / "manual"
    manual.mkdir()
    (manual / f"{INDEX.slug}.csv").write_bytes(_raw([_row(2)]))
    good = refresh(data_dir=tmp_path / "data", from_dir=manual, selected={INDEX.slug},
                   session=Success(), delay=0)
    assert good["index_constituent_memberships"] == 1
    no_rollback = refresh(data_dir=tmp_path / "data", from_dir=manual, selected={INDEX.slug},
                          session=Failure(), attempts=1, delay=0)
    assert no_rollback["failed_indices"] == 1
    assert no_rollback["total_observed_changes"] == 0
    assert no_rollback["history_revisions"] == 1
    assert _read(tmp_path / "data" / "constituents.csv")[0]["symbol"] == "CO7"
