from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="ai_digest_agent/output/monitor.json")
    parser.add_argument("--fail-on-alert", action="store_true")
    args = parser.parse_args()

    monitor_path = Path(args.path)
    if not monitor_path.exists():
        print("monitor_missing=1")
        return 0

    payload = json.loads(monitor_path.read_text(encoding="utf-8"))
    alerts = payload.get("alerts") or []
    print(f"alerts={len(alerts)}")
    if alerts:
        print("monitor_alert=1")

    if args.fail_on_alert and alerts:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
