from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timezone", default="America/Chicago")
    parser.add_argument("--mode", choices=["brief", "detailed"], default="brief")
    parser.add_argument("--email", action="store_true")
    args = parser.parse_args()

    tz = ZoneInfo(args.timezone)
    now = datetime.now(tz)

    schedule = [(8, "AM"), (14, "PM"), (20, "Evening")]
    date_key = now.date().isoformat()
    repo_root = Path(__file__).resolve().parents[2]

    slot = None
    for hour, candidate in schedule:
        due = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if now < due:
            break
        repo_digest = repo_root / "digests" / "archive" / date_key / f"{candidate}.json"
        if not repo_digest.exists():
            slot = candidate
            break
    if not slot:
        return 0

    repo_digest = repo_root / "digests" / "archive" / date_key / f"{slot}.json"

    cmd = [
        sys.executable,
        "ai_digest_agent/scripts/run_scheduled.py",
        "--slot",
        slot,
        "--mode",
        args.mode,
        "--timezone",
        args.timezone,
    ]
    if args.email:
        cmd.append("--email")

    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
