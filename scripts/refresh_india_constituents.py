#!/usr/bin/env python3
"""Refresh NSE sector/factor constituent snapshots and dashboard-ready CSVs.

Usage:
    python scripts/refresh_india_constituents.py
    python scripts/refresh_india_constituents.py --offline --from-dir data/india_holdings/manual
    python scripts/refresh_india_constituents.py --index nifty500_value_50

The Streamlit page NEVER makes NSE HTTP requests; they belong in this job.
On download failure a previously verified local snapshot is retained and marked
cached. HTML/403 pages are rejected, never counted as successful constituents.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import csv
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import time
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from india_constituents import (
    INDIA_INDICES, INDEX_BY_SLUG, MEMBERSHIP_FIELDS, COMPANY_FIELDS, STATUS_FIELDS,
    consolidate_memberships, parse_nse_csv, utc_now,
)
from india_holdings_history import record_verified_snapshot, rebuild_history_exports, snapshot_fingerprint

try:
    import requests
except ImportError:
    requests = None

DATA_DIR = ROOT / "data" / "india_holdings"


def atomic_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", delete=False,
                                     dir=path.parent, prefix=".pending-", suffix=".csv") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        tmp = Path(f.name)
    os.replace(tmp, path)


def atomic_bytes(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=path.parent,
                                     prefix=".pending-") as f:
        f.write(raw)
        tmp = Path(f.name)
    os.replace(tmp, path)


def atomic_json(path: Path, value: dict) -> None:
    content = json.dumps(value, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    atomic_bytes(path, content)


def download_csv(session, url: str, timeout: int, attempts: int) -> bytes:
    last_error = "Unknown network failure"
    for attempt in range(attempts):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            if len(response.content) > 4_000_000:
                raise ValueError("Unexpectedly large constituent response")
            return response.content
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {str(exc)[:250]}"
            # Do not aggressively retry access-denied and non-retryable errors.
            if getattr(getattr(exc, "response", None), "status_code", None) in (401, 403, 404):
                break
            if attempt < attempts - 1:
                time.sleep(min(8.0, 1.5 * (attempt + 1)))
    raise RuntimeError(last_error)


def refresh(*, data_dir: Path = DATA_DIR, offline: bool = False,
            from_dir: Optional[Path] = None, selected: Optional[set[str]] = None,
            timeout: int = 20, attempts: int = 2, delay: float = 1.0,
            session=None, allow_large_changes: bool = False,
            prefer_manual: bool = False) -> dict:
    data_dir = Path(data_dir)
    snapshots = data_dir / "snapshots"
    snapshot_meta = data_dir / "snapshot_meta"
    snapshots.mkdir(parents=True, exist_ok=True)
    snapshot_meta.mkdir(parents=True, exist_ok=True)
    if from_dir:
        from_dir = Path(from_dir)
    if not offline and session is None:
        if requests is None:
            raise RuntimeError("Install requests from requirements.txt")
        session = requests.Session()
        session.headers.update({
            "User-Agent": (os.getenv("NSE_REQUEST_USER_AGENT") or "GlobalIndustryCycleIntelligence/1.0 (NSE constituent research)"),
            "Accept": "text/csv,text/plain,*/*",
            "Referer": "https://www.niftyindices.com/",
        })
    collected = []
    statuses = []
    freshly_updated = 0
    run_changes = {"added": 0, "removed": 0, "weight_changed": 0, "symbol_changed": 0}
    changed_indices = 0
    for index in INDIA_INDICES:
        if selected is not None and index.slug not in selected:
            # Important: still include older snapshots for all other indices.
            should_fetch = False
        else:
            should_fetch = True
        cached_path = snapshots / f"{index.slug}.csv"
        meta_path = snapshot_meta / f"{index.slug}.json"
        cached_meta = {}
        if meta_path.is_file():
            try:
                cached_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                pass
        raw = None
        stamp = cached_meta.get("retrieved_utc", "")
        source_type = cached_meta.get("source_type", "cached_unknown")
        error = ""
        status = "not_collected"
        change_status = "not_checked"
        current_changes = {"added": 0, "removed": 0, "weight_changed": 0, "symbol_changed": 0}
        if should_fetch:
            try:
                manual_file = None
                if from_dir is not None:
                    for name in (f"{index.slug}.csv", index.filename):
                        candidate = from_dir / name
                        if candidate.is_file():
                            manual_file = candidate
                            break
                # Scheduled runs prefer live NSE data. A manual file is a
                # fallback, not a permanent override that prevents updates.
                # Offline / --prefer-manual deliberately choose local import.
                if (offline or prefer_manual) and manual_file is not None:
                    raw = manual_file.read_bytes()
                    origin = "manual_import"
                elif offline:
                    raise FileNotFoundError("No matching local file; expected " + str(from_dir / (index.slug + '.csv') if from_dir else cached_path))
                else:
                    try:
                        raw = download_csv(session, index.url, timeout, attempts)
                        origin = "direct_nse"
                    except RuntimeError:
                        if manual_file is None:
                            raise
                        raw = manual_file.read_bytes()
                        origin = "manual_fallback_after_nse_error"
                new_stamp = datetime.now(timezone.utc).isoformat(timespec="microseconds")
                new_rows = parse_nse_csv(raw, index, new_stamp, origin)
                # Migrate an existing verified latest snapshot into immutable history
                # before replacing it; never compare against a failed download.
                old_rows_for_history = (
                    parse_nse_csv(cached_path.read_bytes(), index, stamp or "unknown", source_type)
                    if cached_path.is_file() else []
                )
                # A potentially stale manual fallback must not roll back a
                # previously verified direct-NSE state during an HTTP failure.
                if (origin == "manual_fallback_after_nse_error" and
                        source_type == "direct_nse" and old_rows_for_history and
                        snapshot_fingerprint(new_rows) != snapshot_fingerprint(old_rows_for_history)):
                    raise ValueError("Manual fallback differs from previously verified direct-NSE snapshot; "
                                     "validate manual file and import explicitly with --prefer-manual")
                delta = record_verified_snapshot(
                    data_dir, index, new_rows, new_stamp, origin,
                    previous_rows=old_rows_for_history, previous_utc=stamp,
                    previous_source_type=source_type,
                    allow_large_changes=allow_large_changes,
                )
                change_status = delta["change_status"]
                for key in current_changes:
                    current_changes[key] = delta[key]
                    run_changes[key] += delta[key]
                if change_status in ("changed", "metadata_revision"):
                    changed_indices += 1
                # Only replace previously successful snapshot after validation & change safety checks.
                atomic_bytes(cached_path, raw)
                atomic_json(meta_path, {"retrieved_utc": new_stamp, "source_type": origin,
                                        "source_url": index.url, "constituent_count": len(new_rows)})
                stamp = new_stamp
                source_type = origin
                status = "updated"
                freshly_updated += 1
            except Exception as exc:
                # Do not overwrite valid cached files on failed retrieval.
                error = f"{type(exc).__name__}: {str(exc)[:260]}"
                status = "cached_after_error" if cached_path.is_file() else "error"
            if delay and not offline and status == "updated":
                time.sleep(delay)
        elif cached_path.is_file():
            status = "cached"
        if cached_path.is_file():
            try:
                old_rows = parse_nse_csv(cached_path.read_bytes(), index,
                                         stamp or "unknown", source_type)
                collected.extend(old_rows)
                if status == "not_collected":
                    status = "cached"
            except (OSError, ValueError) as exc:
                error = (error + " | " if error else "") + f"Invalid cached file: {exc}"
                status = "error"
                old_rows = []
        else:
            old_rows = []
        statuses.append({
            "index_slug": index.slug, "index_name": index.name,
            "category": index.category, "factor_family": index.family,
            "parent_universe": index.parent_universe, "status": status,
            "constituent_count": len(old_rows), "retrieved_utc": stamp,
            "snapshot_utc": stamp, "source_type": source_type if old_rows else "",
            "source_url": index.url, "error": error,
            "change_status": change_status if status == "updated" else "not_compared",
            "additions": current_changes["added"], "removals": current_changes["removed"],
            "weight_changes": current_changes["weight_changed"],
            "symbol_changes": current_changes["symbol_changed"],
        })
    members, companies = consolidate_memberships(collected)
    atomic_csv(data_dir / "constituents.csv", members, MEMBERSHIP_FIELDS)
    atomic_csv(data_dir / "companies.csv", companies, COMPANY_FIELDS)
    atomic_csv(data_dir / "index_status.csv", statuses, STATUS_FIELDS)
    historical = rebuild_history_exports(data_dir)
    summary = {
        "indices_with_observed_changes_this_run": changed_indices,
        "changes_this_run": run_changes,
        **historical,
        "built_utc": utc_now(),
        "tracked_indices": len(INDIA_INDICES),
        "loaded_indices": sum(bool(s["constituent_count"]) for s in statuses),
        "newly_updated_indices": freshly_updated,
        "failed_indices": sum(s["status"] in ("error", "cached_after_error") for s in statuses),
        "unique_companies_or_securities": len(companies),
        "index_constituent_memberships": len(members),
        "known_constituent_weight_entries": sum(bool(r.get("weight_pct")) for r in members),
        "methodology": "descriptive membership only; no ranking, penalties, or imputed weights",
    }
    atomic_json(data_dir / "build_summary.json", summary)
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offline", action="store_true", help="Do not contact NSE; read local CSVs only")
    p.add_argument("--from-dir", type=Path, default=None,
                   help="Local manual CSV directory with files named <index_slug>.csv")
    p.add_argument("--index", action="append", default=[],
                   help="Limit refresh to a registered index slug; may repeat")
    p.add_argument("--data-dir", type=Path, default=DATA_DIR)
    p.add_argument("--timeout", type=int, default=20)
    p.add_argument("--attempts", type=int, default=2)
    p.add_argument("--delay", type=float, default=0.8)
    p.add_argument("--allow-large-changes", action="store_true",
                   help="Permit large source size drops/turnover only after manual verification")
    p.add_argument("--prefer-manual", action="store_true",
                   help="Explicitly use local source files first (default is live NSE with manual fallback)")
    p.add_argument("--require-data", action="store_true",
                   help="Exit nonzero after writing diagnostics if no valid index snapshots exist")
    args = p.parse_args()
    unknown = set(args.index) - set(INDEX_BY_SLUG)
    if unknown:
        p.error("Unknown index slug(s): " + ", ".join(sorted(unknown)))
    summary = refresh(data_dir=args.data_dir, offline=args.offline,
                      from_dir=args.from_dir, selected=set(args.index) if args.index else None,
                      timeout=args.timeout, attempts=args.attempts, delay=args.delay,
                      allow_large_changes=args.allow_large_changes,
                      prefer_manual=args.prefer_manual)
    print(json.dumps(summary, indent=2))
    print("Files: data/india_holdings/{constituents.csv, companies.csv, index_status.csv, build_summary.json, index_revisions.csv, holding_changes.csv}")
    if not summary["loaded_indices"]:
        print("WARNING: No valid constituent files available. Dashboard will show source diagnostics, not invented data.")
        if args.require_data:
            raise SystemExit("ERROR: Zero NSE index constituent snapshots loaded. Check index_status.csv or import authentic source CSVs.")


if __name__ == "__main__":
    main()
