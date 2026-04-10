from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import websockets
from dotenv import load_dotenv


def _pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_port(port: int, timeout_s: float = 15.0) -> None:
    started = time.time()
    while time.time() - started < timeout_s:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.4)
            try:
                sock.connect(("127.0.0.1", port))
                return
            except Exception:
                time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for server on port {port}")


async def _run_once(ws_url: str, prompt: str) -> str:
    async with websockets.connect(ws_url, max_size=20_000_000) as ws:
        await ws.send(
            json.dumps({"jsonrpc": "2.0", "id": "1", "method": "start_run", "params": {"prompt": prompt}})
        )

        final_text: Optional[str] = None
        while True:
            msg = json.loads(await ws.recv())
            method = msg.get("method")

            if method == "client_request":
                params = msg.get("params", {})
                if params.get("function") == "ui.request_tool_approval":
                    request_id = params.get("request_id")
                    if request_id:
                        await ws.send(
                            json.dumps(
                                {
                                    "jsonrpc": "2.0",
                                    "method": "client_response",
                                    "params": {
                                        "request_id": request_id,
                                        "ok": True,
                                        "result": {"approved": True, "always_approve": True},
                                    },
                                }
                            )
                        )

            if method == "message_output":
                text = msg.get("params", {}).get("content")
                if isinstance(text, str) and text.strip():
                    final_text = text

            if method in {"tool_called", "tool_result", "run_error"}:
                print(json.dumps(msg, indent=2)[:4000])

            if method == "run_end":
                break

        return final_text or ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slot", choices=["AM", "PM", "Evening"], required=True)
    parser.add_argument("--mode", choices=["brief", "detailed"], default="brief")
    parser.add_argument("--email", action="store_true")
    parser.add_argument("--timezone", default=os.getenv("TIMEZONE", "America/Chicago"))
    args = parser.parse_args()

    agent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agent_yml = os.path.join(agent_dir, "agent.yml")
    output_dir = Path(agent_dir) / "output"
    latest_json = output_dir / "latest.json"

    load_dotenv(Path(agent_dir) / ".env", override=True)

    child_env = os.environ.copy()

    port = _pick_port()

    prompt = (
        f"Generate the {args.slot} AI digest in timezone {args.timezone}. "
        f"Primary output should be {args.mode}. "
        + ("Send the email." if args.email else "Do not send the email.")
    )

    server_cmd = [
        sys.executable,
        "-m",
        "omniagents",
        "run",
        "-c",
        agent_yml,
        "--mode",
        "server",
        "--port",
        str(port),
        "--approvals",
        "skip",
        "--debug",
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    server_log = output_dir / f"server_{args.slot.lower()}_{int(time.time())}.log"
    log_fp = server_log.open("w", encoding="utf-8")

    proc = subprocess.Popen(
        server_cmd,
        cwd=agent_dir,
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        env=child_env,
    )

    try:
        _wait_for_port(port, timeout_s=20.0)
        ws_url = f"ws://127.0.0.1:{port}/ws"
        result = asyncio.run(_run_once(ws_url, prompt))
        if result.strip():
            print(result)

        if not latest_json.exists():
            print(
                f"Warning: Run completed but {latest_json} was not written "
                f"(search APIs may be unavailable). See logs: {server_log}"
            )
            return 2
        return 0
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

        try:
            log_fp.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
