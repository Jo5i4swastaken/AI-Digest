from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timezone", default="America/Chicago")
    parser.add_argument("--mode", choices=["brief", "detailed"], default="brief")
    parser.add_argument("--email", action="store_true")
    parser.add_argument("--slo-minutes", type=int, default=15)
    parser.add_argument("--max-backfill-hours", type=int, default=12)
    parser.add_argument("--max-delivery-minutes-default", type=int, default=90)
    parser.add_argument("--max-delivery-minutes-evening", type=int, default=60)
    args = parser.parse_args()

    tz = ZoneInfo(args.timezone)
    now = datetime.now(tz)

    repo_root = Path(__file__).resolve().parents[2]

    schedule = [(8, "AM"), (14, "PM"), (20, "Evening")]
    candidates = []
    for offset_days in (1, 0):
        day = (now.date() - timedelta(days=offset_days))
        for hour, slot in schedule:
            due = datetime.combine(day, datetime.min.time(), tzinfo=tz).replace(
                hour=hour, minute=0, second=0, microsecond=0
            )
            if due <= now:
                candidates.append((due, slot))
    candidates.sort(key=lambda t: t[0])

    chosen: tuple[datetime, str] | None = None
    for due, slot in candidates:
        date_key = due.date().isoformat()
        repo_digest = repo_root / "digests" / "archive" / date_key / f"{slot}.json"
        if not repo_digest.exists():
            if now - due <= timedelta(hours=args.max_backfill_hours):
                chosen = (due, slot)
            break

    monitor = {
        "ok": True,
        "timezone": args.timezone,
        "now": now.isoformat(),
        "slo_minutes": args.slo_minutes,
        "max_backfill_hours": args.max_backfill_hours,
        "max_delivery_minutes_default": args.max_delivery_minutes_default,
        "max_delivery_minutes_evening": args.max_delivery_minutes_evening,
        "action": "noop",
        "alerts": [],
    }

    if not chosen:
        monitor_path = repo_root / "ai_digest_agent" / "output" / "monitor.json"
        monitor_path.parent.mkdir(parents=True, exist_ok=True)
        monitor_path.write_text(json.dumps(monitor, indent=2, ensure_ascii=False), encoding="utf-8")
        return 0

    due, slot = chosen
    date_key = due.date().isoformat()
    drift_minutes = int((now - due).total_seconds() // 60)

    max_delivery = args.max_delivery_minutes_evening if slot == "Evening" else args.max_delivery_minutes_default
    monitor["max_delivery_minutes"] = max_delivery

    if drift_minutes > max_delivery:
        monitor["ok"] = False
        monitor["action"] = "skip_expired"
        monitor["slot"] = slot
        monitor["date"] = date_key
        monitor["due"] = due.isoformat()
        monitor["drift_minutes"] = drift_minutes
        monitor["alerts"].append(
            {
                "type": "digest_expired",
                "slot": slot,
                "date": date_key,
                "drift_minutes": drift_minutes,
                "max_delivery_minutes": max_delivery,
            }
        )
        monitor_path = repo_root / "ai_digest_agent" / "output" / "monitor.json"
        monitor_path.parent.mkdir(parents=True, exist_ok=True)
        monitor_path.write_text(json.dumps(monitor, indent=2, ensure_ascii=False), encoding="utf-8")
        return 0

    monitor["action"] = "run"
    monitor["slot"] = slot
    monitor["date"] = date_key
    monitor["due"] = due.isoformat()
    monitor["drift_minutes"] = drift_minutes
    if drift_minutes > args.slo_minutes:
        monitor["alerts"].append(
            {
                "type": "digest_late",
                "slot": slot,
                "date": date_key,
                "drift_minutes": drift_minutes,
                "slo_minutes": args.slo_minutes,
            }
        )

    cmd = [
        sys.executable,
        "ai_digest_agent/scripts/run_scheduled.py",
        "--slot",
        slot,
        "--mode",
        args.mode,
        "--timezone",
        args.timezone,
        "--date",
        date_key,
    ]
    if args.email:
        cmd.append("--email")

    rc = subprocess.call(cmd)

    monitor["run_exit_code"] = rc
    repo_digest = repo_root / "digests" / "archive" / date_key / f"{slot}.json"
    if not repo_digest.exists():
        monitor["ok"] = False
        monitor["alerts"].append({"type": "digest_missing_after_run", "slot": slot, "date": date_key})
    elif rc != 0:
        monitor["ok"] = False
        monitor["alerts"].append({"type": "digest_run_failed", "slot": slot, "date": date_key, "exit_code": rc})

    monitor_path = repo_root / "ai_digest_agent" / "output" / "monitor.json"
    monitor_path.parent.mkdir(parents=True, exist_ok=True)
    monitor_path.write_text(json.dumps(monitor, indent=2, ensure_ascii=False), encoding="utf-8")

    return rc


if __name__ == "__main__":
    raise SystemExit(main())
