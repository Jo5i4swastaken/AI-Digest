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

    slot_map = {8: "AM", 14: "PM", 20: "Evening"}

    slot = slot_map.get(now.hour)
    if not slot:
        return 0

    window_minutes = 12
    if now.minute >= window_minutes:
        return 0

    repo_root = Path(__file__).resolve().parents[2]
    date_key = now.date().isoformat()
    repo_digest = repo_root / "digests" / "archive" / date_key / f"{slot}.json"
    if repo_digest.exists():
        return 0

    cmd = [
        sys.executable,
        "ai_digest_agent/scripts/run_scheduled.py",
        "--slot",
        slot,
        "--mode",
        args.mode,
    ]
    if args.email:
        cmd.append("--email")

    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
