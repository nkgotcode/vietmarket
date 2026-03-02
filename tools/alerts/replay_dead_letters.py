#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from engine.dispatch import send


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dead-letter', default='runtime/alerts/dead_letters.jsonl')
    ap.add_argument('--channels', default='config/alerts/channels.json')
    ap.add_argument('--channel', default=None, help='Replay only this channel')
    ap.add_argument('--limit', type=int, default=100)
    ap.add_argument('--truncate', action='store_true', help='truncate file after replay attempt')
    args = ap.parse_args()

    dl = Path(args.dead_letter)
    if not dl.exists():
        print(json.dumps({'ok': True, 'replayed': 0, 'reason': 'no_dead_letter_file'}))
        return 0

    cfg = json.loads(Path(args.channels).read_text()) if Path(args.channels).exists() else {}
    lines = [ln for ln in dl.read_text(encoding='utf-8').splitlines() if ln.strip()]
    rows = []
    for ln in lines:
        try:
            rows.append(json.loads(ln))
        except Exception:
            continue

    rows = rows[-args.limit:]
    n = 0
    for r in rows:
        ch = r.get('channel')
        if args.channel and ch != args.channel:
            continue
        msg = r.get('message', '')
        send(ch, f"[DLQ-REPLAY] {msg}", cfg)
        n += 1

    if args.truncate:
        dl.write_text('')

    print(json.dumps({'ok': True, 'replayed': n, 'input_rows': len(rows)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
