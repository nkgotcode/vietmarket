#!/usr/bin/env python3
"""Repair worker: consumes Convex candleRepairQueue and fills gaps using vnstock VCI.

Process:
- pull next queued items
- mark running
- fetch candles for window
- upsert to Convex
- mark done (or error)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime

import requests

# reuse existing backfill fetcher
from packages.ingest.vn.candles_backfill import fetch_candles_vci, tf_to_interval, ts_to_ms


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=2)
    p.add_argument('--sleep', type=float, default=0.1)
    return p.parse_args(argv)


def convex_url() -> str:
    u = os.environ.get('CONVEX_URL') or os.environ.get('NEXT_PUBLIC_CONVEX_URL')
    if not u:
        raise RuntimeError('Missing CONVEX_URL or NEXT_PUBLIC_CONVEX_URL')
    return u.rstrip('/')


def convex_query(path: str, args: dict) -> dict:
    url = convex_url() + '/api/query'
    r = requests.post(url, json={'path': path, 'args': args}, timeout=60)
    r.raise_for_status()
    return r.json()


def convex_mutation(path: str, args: dict) -> dict:
    url = convex_url() + '/api/mutation'
    r = requests.post(url, json={'path': path, 'args': args}, timeout=60)
    r.raise_for_status()
    return r.json()


def ms_to_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime('%Y-%m-%d %H:%M:%S')


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    out = convex_query('repairQueue:nextQueued', {'limit': args.limit})
    items = out.get('value') if isinstance(out, dict) and 'value' in out else out
    if not items:
        print(json.dumps({'ok': True, 'processed': 0, 'reason': 'no queued items'}))
        return 0

    processed = 0

    for it in items:
        qid = it['_id']
        ticker = it['ticker']
        tf = it['tf']
        ws = int(it['windowStartTs'])
        we = int(it['windowEndTs'])

        try:
            convex_mutation('repairQueue:markRunning', {'id': qid})

            interval = tf_to_interval(tf)
            # vnstock expects start/end strings
            start_str = ms_to_date(ws)
            end_str = ms_to_date(we)
            df = fetch_candles_vci(ticker, interval, start_str, end_str)

            rows = []
            for _, r in df.iterrows():
                o, h, l, c = r.get('open'), r.get('high'), r.get('low'), r.get('close')
                if o is None or h is None or l is None or c is None:
                    continue
                # skip NaNs
                try:
                    if any(str(x) == 'nan' for x in [o, h, l, c]):
                        continue
                except Exception:
                    pass
                rows.append({
                    'ts': ts_to_ms(r.get('time')),
                    'o': float(o),
                    'h': float(h),
                    'l': float(l),
                    'c': float(c),
                    'v': float(r.get('volume')) if r.get('volume') is not None else None,
                    'source': 'vci-repair',
                })

            convex_mutation('candles:upsertMany', {'ticker': ticker, 'tf': tf, 'candles': rows})

            # audit
            missing = max(int(it.get('expectedBars', 0)) - len(rows), 0)
            convex_mutation('repairs:logCandleRepair', {
                'ticker': ticker,
                'tf': tf,
                'windowStartTs': ws,
                'windowEndTs': we,
                'missingCount': missing,
                'note': f"repair fetched={len(rows)}",
            })

            convex_mutation('repairQueue:markDone', {'id': qid})
            processed += 1
            time.sleep(args.sleep)

        except Exception as e:
            convex_mutation('repairQueue:markError', {'id': qid, 'error': str(e)})

    print(json.dumps({'ok': True, 'processed': processed}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
