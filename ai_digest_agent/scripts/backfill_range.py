from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


SLOTS = ("AM", "PM", "Evening")


@dataclass(frozen=True)
class RunResult:
    date: str
    slot: str
    status: str
    path: str
    items: int


def _iter_dates(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _repo_digest_path(day: str, slot: str) -> Path:
    return _repo_root() / "digests" / "archive" / day / f"{slot}.json"


def _read_item_count(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    items = payload.get("items")
    return len(items) if isinstance(items, list) else 0


def _run_one(*, day: str, slot: str, mode: str, timezone: str, email: bool) -> RunResult:
    cmd = [
        sys.executable,
        "ai_digest_agent/scripts/run_scheduled.py",
        "--slot",
        slot,
        "--mode",
        mode,
        "--timezone",
        timezone,
        "--date",
        day,
    ]
    if email:
        cmd.append("--email")

    before_exists = _repo_digest_path(day, slot).exists()
    rc = subprocess.call(cmd, cwd=_repo_root())

    path = _repo_digest_path(day, slot)
    after_exists = path.exists()
    items = _read_item_count(path) if after_exists else 0

    if rc != 0:
        return RunResult(date=day, slot=slot, status=f"error(rc={rc})", path=str(path), items=items)
    if not after_exists:
        return RunResult(date=day, slot=slot, status="missing_output", path=str(path), items=0)
    if before_exists:
        return RunResult(date=day, slot=slot, status="updated", path=str(path), items=items)
    return RunResult(date=day, slot=slot, status="created", path=str(path), items=items)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--end", help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--timezone", default="America/Chicago")
    parser.add_argument("--mode", choices=["brief", "detailed"], default="brief")
    parser.add_argument("--email", action="store_true")
    parser.add_argument("--force", action="store_true", help="Re-run even if digest JSON exists")
    args = parser.parse_args()

    today = datetime.now().date()

    repo_index_path = _repo_root() / "digests" / "archive" / "index.json"
    repo_index = json.loads(repo_index_path.read_text(encoding="utf-8")) if repo_index_path.exists() else {}
    days = repo_index.get("days") if isinstance(repo_index, dict) else None
    latest = None
    if isinstance(days, list) and days:
        for entry in days:
            if isinstance(entry, dict) and isinstance(entry.get("date"), str):
                d = entry["date"]
                if latest is None or d > latest:
                    latest = d

    default_start = date.fromisoformat(latest) + timedelta(days=1) if latest else today - timedelta(days=3)
    default_end = today - timedelta(days=1)

    start = date.fromisoformat(args.start) if args.start else default_start
    end = date.fromisoformat(args.end) if args.end else default_end

    if end < start:
        print(json.dumps({"ok": True, "message": "No dates to backfill", "start": start.isoformat(), "end": end.isoformat()}))
        return 0

    results: list[RunResult] = []
    for d in _iter_dates(start, end):
        day = d.isoformat()
        for slot in SLOTS:
            out_path = _repo_digest_path(day, slot)
            if out_path.exists() and not args.force:
                results.append(
                    RunResult(date=day, slot=slot, status="skipped(existing)", path=str(out_path), items=_read_item_count(out_path))
                )
                continue
            results.append(
                _run_one(day=day, slot=slot, mode=args.mode, timezone=args.timezone, email=args.email)
            )

    total_created = sum(1 for r in results if r.status == "created")
    total_updated = sum(1 for r in results if r.status == "updated")
    total_skipped = sum(1 for r in results if r.status.startswith("skipped"))
    total_errors = [r for r in results if r.status.startswith("error") or r.status == "missing_output"]

    report = {
        "ok": len(total_errors) == 0,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "created": total_created,
        "updated": total_updated,
        "skipped": total_skipped,
        "errors": [r.__dict__ for r in total_errors],
        "results": [r.__dict__ for r in results],
    }
    print(json.dumps(report, indent=2))

    return 1 if total_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
