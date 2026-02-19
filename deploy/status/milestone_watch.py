#!/usr/bin/env python3
"""Milestone watcher for VietMarket.

Runs on the Mac mini (or wherever OpenClaw runs) and uses SSH to query:
- Timescale candles count + max/min ts
- Nomad job status for key jobs

It prints a short update only when something changed since the last run,
otherwise prints NO_REPLY.

State file: deploy/status/milestone_state.json (local).

Env (optional overrides):
- OPTIPLEX_HOST (default: itsnk@100.83.150.39)
- NOMAD_ADDR (default: http://100.83.150.39:4646)
- PG_URL (default: postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable)
- SIMPLIZE_HEALTH_URL (default: http://127.0.0.1:18991/health)
- HISTORY_API_HEALTH_URL (default: "" disabled)

Notes:
- Do NOT default History API to Optiplex localhost. In current topology it is hosted on Vultr,
  so Optiplex checks against 127.0.0.1:8787 are false negatives.
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent / "milestone_state.json"

OPTIPLEX_HOST = os.environ.get("OPTIPLEX_HOST", "itsnk@100.83.150.39")
NOMAD_ADDR = os.environ.get("NOMAD_ADDR", "http://100.83.150.39:4646")
PG_URL = os.environ.get(
    "PG_URL",
    "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable",
)
SIMPLIZE_HEALTH_URL = os.environ.get("SIMPLIZE_HEALTH_URL", "http://127.0.0.1:18991/health")
HISTORY_API_HEALTH_URL = os.environ.get("HISTORY_API_HEALTH_URL", "").strip()

KEY_JOBS = [
    "etcd",
    "timescaledb-ha",
    "pg-haproxy",
    "vietmarket-candles-timescale-latest",
    "vietmarket-candles-timescale-backfill",
    "vietmarket-vietstock-timescale",
]


def sh(cmd: list[str], *, timeout: int = 25) -> str:
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"cmd failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr.strip()}\n{p.stdout.strip()}")
    return p.stdout


def ssh(cmd: str, *, timeout: int = 25) -> str:
    return sh([
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=8",
        OPTIPLEX_HOST,
        cmd,
    ], timeout=timeout)


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text("utf-8"))
    except Exception:
        return {}


def save_state(st: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(st, indent=2, sort_keys=True), encoding="utf-8")


def get_candles_stats() -> dict:
    q = "select count(*) as candles, min(ts) as min_ts, max(ts) as max_ts from candles;"
    out = ssh(
        f"psql \"{PG_URL}\" -t -A -F',' -c \"{q}\""
    ).strip()
    # format: candles,min_ts,max_ts
    parts = out.split(",") if out else ["0", "", ""]
    return {
        "candles": int(parts[0] or 0),
        "min_ts": int(parts[1]) if len(parts) > 1 and parts[1] else None,
        "max_ts": int(parts[2]) if len(parts) > 2 and parts[2] else None,
    }


def get_job_statuses() -> dict:
    statuses: dict[str, str] = {}
    for j in KEY_JOBS:
        try:
            out = ssh(f"export NOMAD_ADDR={NOMAD_ADDR}; nomad job status {j} 2>/dev/null | sed -n '1,25p'")
            # Find Status line
            st = "unknown"
            for line in out.splitlines():
                if line.strip().startswith("Status"):
                    st = line.split("=", 1)[-1].strip() if "=" in line else line.strip()
                    break
            statuses[j] = st
        except Exception:
            statuses[j] = "missing"
    return statuses


def http_ok(url: str, timeout_s: int = 4) -> tuple[bool, str]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read(1024).decode("utf-8", errors="replace")
            return (200 <= resp.status < 300, body[:120])
    except Exception as e:
        return (False, str(e)[:120])


def get_endpoint_statuses() -> dict:
    out: dict[str, dict] = {}

    ok, detail = http_ok(SIMPLIZE_HEALTH_URL)
    out["simplize_api"] = {
        "url": SIMPLIZE_HEALTH_URL,
        "ok": ok,
        "detail": detail,
    }

    if HISTORY_API_HEALTH_URL:
        ok, detail = http_ok(HISTORY_API_HEALTH_URL)
        out["history_api"] = {
            "url": HISTORY_API_HEALTH_URL,
            "ok": ok,
            "detail": detail,
        }
    else:
        out["history_api"] = {
            "url": None,
            "ok": None,
            "detail": "disabled (set HISTORY_API_HEALTH_URL to explicit non-Optiplex target)",
        }

    return out


def main() -> int:
    prev = load_state()

    now = {
        "candles": get_candles_stats(),
        "jobs": get_job_statuses(),
        "endpoints": get_endpoint_statuses(),
    }

    changed = prev != now
    if not changed:
        print("NO_REPLY")
        return 0

    # Compute a concise diff-ish message.
    lines: list[str] = []

    pc = (prev.get("candles") or {}) if isinstance(prev, dict) else {}
    nc = now["candles"]
    if pc != nc:
        lines.append(
            f"Timescale candles: {pc.get('candles','?')} → {nc['candles']} (max_ts={nc.get('max_ts')})"
        )

    pj = (prev.get("jobs") or {}) if isinstance(prev, dict) else {}
    nj = now["jobs"]
    job_changes = []
    for k, v in nj.items():
        if pj.get(k) != v:
            job_changes.append(f"{k}: {pj.get(k,'?')} → {v}")
    if job_changes:
        lines.append("Nomad: " + "; ".join(job_changes[:6]) + ("" if len(job_changes) <= 6 else " …"))

    pe = (prev.get("endpoints") or {}) if isinstance(prev, dict) else {}
    ne = now["endpoints"]
    endpoint_changes = []
    for k, v in ne.items():
        if pe.get(k) != v:
            endpoint_changes.append(f"{k}: ok={v.get('ok')} url={v.get('url')}")
    if endpoint_changes:
        lines.append("Endpoints: " + "; ".join(endpoint_changes))

    save_state(now)

    msg = "\n".join(lines).strip() or "State changed."
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
