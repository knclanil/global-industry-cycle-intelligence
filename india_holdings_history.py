"""Immutable NSE constituent revision log and observed membership changes.

This module does not predict index eligibility, holding weight, or rebalance dates.
Only validated snapshots create history. The first valid snapshot of each index
establishes a baseline; changes are recorded only between successive observations.
"""
from __future__ import annotations

import csv
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable

SNAPSHOT_FIELDS = ["company_name", "symbol", "isin", "industry", "series", "weight_pct"]
REVISION_FIELDS = [
    "index_slug", "index_name", "category", "factor_family", "parent_universe",
    "revision_id", "observed_utc", "previous_observed_utc", "snapshot_path",
    "constituent_count", "source_type", "source_url", "revision_type",
    "added", "removed", "weight_changed", "symbol_changed",
]
CHANGE_FIELDS = [
    "event_id", "observed_utc", "previous_observed_utc", "index_slug",
    "index_name", "category", "factor_family", "parent_universe", "change_type",
    "company_name", "symbol", "previous_symbol", "isin", "company_identity",
    "old_weight_pct", "new_weight_pct", "previous_revision_id", "revision_id",
    "source_url", "source_type",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _write_csv_atomic(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", delete=False,
                                     dir=path.parent, prefix=".history-pending-", suffix=".csv") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        pending = f.name
    os.replace(pending, path)


def _identity(row: dict) -> str:
    isin = str(row.get("isin") or "").strip().upper()
    symbol = str(row.get("symbol") or "").strip().upper()
    return "ISIN:" + isin if isin else "SYMBOL:" + symbol


def _normalized(row: dict) -> dict:
    return {key: str(row.get(key) or "").strip() for key in SNAPSHOT_FIELDS}


def _fingerprint(rows: Iterable[dict]) -> str:
    # Independent of downloaded CSV row order or company-name typography.
    values = sorted(((_identity(r), str(r.get("symbol") or "").upper(),
                       str(r.get("weight_pct") or "")) for r in rows))
    data = json.dumps(values, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def snapshot_fingerprint(rows: Iterable[dict]) -> str:
    """Public membership/weight fingerprint, independent of source row ordering."""
    return _fingerprint(rows)


def _match_rows(old: list[dict], new: list[dict]):
    """Match by ISIN, or one-to-one symbol if ISINs do not conflict.

    An added ISIN for an otherwise unchanged symbol must not become a false
    constituent addition/removal; conflicting explicit ISINs never match.
    """
    pairs = []
    used_old = set()
    used_new = set()
    old_by_isin = {r["isin"].upper(): i for i, r in enumerate(old) if r.get("isin")}
    new_by_isin = {r["isin"].upper(): j for j, r in enumerate(new) if r.get("isin")}
    for isin in sorted(set(old_by_isin) & set(new_by_isin)):
        i, j = old_by_isin[isin], new_by_isin[isin]
        used_old.add(i)
        used_new.add(j)
        pairs.append((old[i], new[j]))
    old_sym: dict[str, list[int]] = {}
    new_sym: dict[str, list[int]] = {}
    for i, r in enumerate(old):
        if i not in used_old:
            old_sym.setdefault(r["symbol"].upper(), []).append(i)
    for j, r in enumerate(new):
        if j not in used_new:
            new_sym.setdefault(r["symbol"].upper(), []).append(j)
    for symbol in sorted(set(old_sym) & set(new_sym)):
        if len(old_sym[symbol]) != 1 or len(new_sym[symbol]) != 1:
            continue
        i, j = old_sym[symbol][0], new_sym[symbol][0]
        if old[i].get("isin") and new[j].get("isin") and old[i]["isin"] != new[j]["isin"]:
            continue
        used_old.add(i)
        used_new.add(j)
        pairs.append((old[i], new[j]))
    gone = [r for i, r in enumerate(old) if i not in used_old]
    arrived = [r for j, r in enumerate(new) if j not in used_new]
    return pairs, gone, arrived


def _weight_change(old_weight: str, new_weight: str) -> bool:
    if not old_weight or not new_weight:
        return False  # unknown vs known is data coverage, not a measured weight change
    try:
        return abs(Decimal(old_weight) - Decimal(new_weight)) >= Decimal("0.01")
    except InvalidOperation:
        return False


def compare_snapshots(old: list[dict], new: list[dict]) -> list[dict]:
    """Compute unlabelled delta rows for two known-valid snapshots."""
    old = [_normalized(r) for r in old]
    new = [_normalized(r) for r in new]
    pairs, gone, arrived = _match_rows(old, new)
    events: list[dict] = []
    for r in sorted(gone, key=lambda x: (x["symbol"], x["isin"])):
        events.append({"change_type": "Removed", "company_name": r["company_name"],
                       "symbol": r["symbol"], "previous_symbol": r["symbol"],
                       "isin": r["isin"], "company_identity": _identity(r),
                       "old_weight_pct": r["weight_pct"], "new_weight_pct": ""})
    for r in sorted(arrived, key=lambda x: (x["symbol"], x["isin"])):
        events.append({"change_type": "Added", "company_name": r["company_name"],
                       "symbol": r["symbol"], "previous_symbol": "",
                       "isin": r["isin"], "company_identity": _identity(r),
                       "old_weight_pct": "", "new_weight_pct": r["weight_pct"]})
    for before, after in sorted(pairs, key=lambda x: x[1]["symbol"]):
        shared = {"company_name": after["company_name"], "symbol": after["symbol"],
                  "previous_symbol": before["symbol"], "isin": after["isin"] or before["isin"],
                  "company_identity": _identity(after) if after["isin"] else _identity(before),
                  "old_weight_pct": before["weight_pct"], "new_weight_pct": after["weight_pct"]}
        if before["symbol"].upper() != after["symbol"].upper():
            events.append({**shared, "change_type": "Symbol Changed"})
        if _weight_change(before["weight_pct"], after["weight_pct"]):
            events.append({**shared, "change_type": "Weight Changed"})
    return events


def _guard_unexpected_change(old: list[dict], new: list[dict], *, allow_large_changes: bool) -> None:
    if not old or allow_large_changes:
        return
    pairs, gone, arrived = _match_rows(old, new)
    # A partial NSE/HTML-like CSV must not generate a mass-deletion event.
    if len(old) >= 10 and len(new) < len(old) * 0.70:
        raise ValueError(f"Suspicious index size drop: {len(old)} -> {len(new)}; "
                         "review source or use --allow-large-changes")
    if len(old) >= 10 and (len(gone) + len(arrived)) / (len(old) + len(new)) > 0.60:
        raise ValueError("Suspicious constituent turnover (>60% combined membership); "
                         "review source or use --allow-large-changes")


def _save_revision(data_dir: Path, index, rows: list[dict], observed: str,
                   source_type: str, previous: dict | None, events: list[dict],
                   revision_type: str) -> dict:
    directory = data_dir / "history" / index.slug
    old_id = previous["revision_id"] if previous else ""
    signature = _fingerprint(rows)
    revision_id = hashlib.sha256(f"{observed}|{signature}|{old_id}".encode()).hexdigest()[:20]
    csv_name = revision_id + ".csv"
    old_at = previous["observed_utc"] if previous else ""
    revision = {
        "index_slug": index.slug, "index_name": index.name, "category": index.category,
        "factor_family": index.family, "parent_universe": index.parent_universe,
        "revision_id": revision_id, "observed_utc": observed,
        "previous_observed_utc": old_at,
        "snapshot_path": f"history/{index.slug}/{csv_name}",
        "constituent_count": len(rows), "source_type": source_type,
        "source_url": index.url, "revision_type": revision_type,
        "added": sum(e["change_type"] == "Added" for e in events),
        "removed": sum(e["change_type"] == "Removed" for e in events),
        "weight_changed": sum(e["change_type"] == "Weight Changed" for e in events),
        "symbol_changed": sum(e["change_type"] == "Symbol Changed" for e in events),
    }
    snapshot = [_normalized(r) for r in rows]
    snapshot.sort(key=lambda x: (x["isin"], x["symbol"]))
    _write_csv_atomic(directory / csv_name, snapshot, SNAPSHOT_FIELDS)
    _write_csv_atomic(directory / "revisions.csv", _read_csv(directory / "revisions.csv") + [revision], REVISION_FIELDS)
    if events:
        event_rows = _read_csv(directory / "events.csv")
        for e in events:
            event_id = hashlib.sha256(
                f'{revision_id}|{e["change_type"]}|{e["company_identity"]}'.encode()
            ).hexdigest()[:20]
            event_rows.append({**e, "event_id": event_id,
                               "observed_utc": observed, "previous_observed_utc": old_at,
                               "index_slug": index.slug, "index_name": index.name,
                               "category": index.category, "factor_family": index.family,
                               "parent_universe": index.parent_universe,
                               "previous_revision_id": old_id, "revision_id": revision_id,
                               "source_url": index.url, "source_type": source_type})
        _write_csv_atomic(directory / "events.csv", event_rows, CHANGE_FIELDS)
    return revision


def record_verified_snapshot(data_dir: Path, index, rows: list[dict],
                             observed_utc: str, source_type: str, *,
                             previous_rows: list[dict] | None = None,
                             previous_utc: str = "", previous_source_type: str = "cached_legacy",
                             allow_large_changes: bool = False) -> dict:
    """Record baseline/revisions; return counts for this observed retrieval.

    previous_rows is required for upgrade from an existing, pre-tracker cache;
    otherwise the initial freshly collected file is the baseline. On failure,
    callers must NOT replace their previously validated latest file.
    """
    data_dir = Path(data_dir)
    if not rows:
        raise ValueError("Cannot record an empty constituent snapshot")
    directory = data_dir / "history" / index.slug
    revisions = _read_csv(directory / "revisions.csv")
    if previous_rows and not revisions:
        baseline_time = previous_utc or observed_utc
        _save_revision(data_dir, index, previous_rows, baseline_time,
                       previous_source_type, None, [], "legacy_baseline")
        revisions = _read_csv(directory / "revisions.csv")
    if not revisions:
        _save_revision(data_dir, index, rows, observed_utc, source_type, None, [], "baseline")
        return {"change_status": "baseline", "added": 0, "removed": 0,
                "weight_changed": 0, "symbol_changed": 0}
    latest = revisions[-1]
    last_rows = _read_csv(data_dir / latest["snapshot_path"])
    if not last_rows:
        raise ValueError("Historical snapshot missing/empty for " + index.slug)
    if _fingerprint(last_rows) == _fingerprint(rows):
        return {"change_status": "unchanged", "added": 0, "removed": 0,
                "weight_changed": 0, "symbol_changed": 0}
    _guard_unexpected_change(last_rows, [_normalized(r) for r in rows],
                             allow_large_changes=allow_large_changes)
    events = compare_snapshots(last_rows, rows)
    _save_revision(data_dir, index, rows, observed_utc, source_type, latest, events,
                   "changed" if events else "metadata_revision")
    return {"change_status": "changed" if events else "metadata_revision",
            **{kind: sum(e["change_type"] == typ for e in events)
               for kind, typ in (("added", "Added"), ("removed", "Removed"),
                                 ("weight_changed", "Weight Changed"),
                                 ("symbol_changed", "Symbol Changed"))}}


def rebuild_history_exports(data_dir: Path) -> dict:
    """Materialize compact, Streamlit-ready logs from immutable per-index history."""
    from india_constituents import INDIA_INDICES
    data_dir = Path(data_dir)
    revisions: list[dict] = []
    events: list[dict] = []
    for index in INDIA_INDICES:
        directory = data_dir / "history" / index.slug
        revisions.extend(_read_csv(directory / "revisions.csv"))
        events.extend(_read_csv(directory / "events.csv"))
    revisions.sort(key=lambda r: (r["observed_utc"], r["index_slug"], r["revision_id"]))
    events.sort(key=lambda r: (r["observed_utc"], r["index_slug"], r["change_type"], r["symbol"]))
    _write_csv_atomic(data_dir / "index_revisions.csv", revisions, REVISION_FIELDS)
    _write_csv_atomic(data_dir / "holding_changes.csv", events, CHANGE_FIELDS)
    return {"history_revisions": len(revisions), "total_observed_changes": len(events),
            "added_events": sum(e["change_type"] == "Added" for e in events),
            "removed_events": sum(e["change_type"] == "Removed" for e in events),
            "weight_change_events": sum(e["change_type"] == "Weight Changed" for e in events),
            "symbol_change_events": sum(e["change_type"] == "Symbol Changed" for e in events)}
