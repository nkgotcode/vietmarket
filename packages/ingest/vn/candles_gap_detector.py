#!/usr/bin/env python3
"""Gap detector: checks recent Convex candle windows and enqueues repairs.

Heuristic: for each ticker+tf, fetch last N bars and see if timestamps are continuous.
If not, enqueue a repair window covering the detected gap.

This runs locally; queue is stored in Convex (candleRepairQueue).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import requests


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--universe', default=os.environ.get('UNIVERSE_FILE', 'data/simplize/universe.latest.json'))
    p.add_argument('--limit-tickers', type=int, default=40)
    p.add_argument('--tfs', default='1d,1h,15m')
    p.add_argument('--bars', type=int, default=500)
    p.add_argument('--sleep', type=float, default=0.05)
    p.add_argument('--time-budget-sec', type=int, default=240, help='Hard stop so cron never hangs')
    p.add_argument('--query-timeout-sec', type=int, default=20)
    return p.parse_args(argv)


def convex_url() -> str:
    u = os.environ.get('CONVEX_URL') or os.environ.get('NEXT_PUBLIC_CONVEX_URL')
    if not u:
        raise RuntimeError('Missing CONVEX_URL or NEXT_PUBLIC_CONVEX_URL')
    return u.rstrip('/')


def convex_query(path: str, args: dict, *, timeout_s: int = 20) -> dict:
    url = convex_url() + '/api/query'
    r = requests.post(url, json={'path': path, 'args': args}, timeout=timeout_s)
    r.raise_for_status()
    return r.json()


def convex_mutation(path: str, args: dict) -> dict:
    url = convex_url() + '/api/mutation'
    r = requests.post(url, json={'path': path, 'args': args}, timeout=60)
    r.raise_for_status()
    return r.json()


def load_tickers(universe_path: str, limit: int) -> list[str]:
    obj = json.loads(open(universe_path, 'r', encoding='utf-8').read())
    tickers = [t.strip().upper() for t in obj.get('tickers', []) if str(t).strip()]
    # include indices
    for x in ['VNINDEX', 'HNXINDEX', 'UPCOMINDEX']:
        if x not in tickers:
            tickers.append(x)
    if limit and limit > 0:
        tickers = tickers[:limit]
    return tickers


def expected_step_ms(tf: str) -> int:
    if tf == '1d':
        return 24 * 60 * 60 * 1000
    if tf == '1h':
        return 60 * 60 * 1000
    if tf == '15m':
        return 15 * 60 * 1000
    raise ValueError(tf)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    tfs = [x.strip() for x in args.tfs.split(',') if x.strip()]
    tickers = load_tickers(args.universe, args.limit_tickers)

    started = time.time()
    deadline = started + max(10, args.time_budget_sec)

    enq = 0
    checked = 0
    errors = 0

    for ticker in tickers:
        for tf in tfs:
            if time.time() > deadline:
                print(json.dumps({'ok': True, 'checked': checked, 'enqueued': enq, 'errors': errors, 'stopped': 'time_budget'}))
                return 0

            checked += 1
            try:
                out = convex_query('candles:latest', {'ticker': ticker, 'tf': tf, 'limit': args.bars}, timeout_s=args.query_timeout_sec)
            except Exception as e:
                errors += 1
                # continue best-effort
                continue

            data = out.get('value') if isinstance(out, dict) and 'value' in out else out
            if not data or len(data) < 5:
                continue

            step = expected_step_ms(tf)

            # detect first gap
            gap_start = None
            gap_end = None
            for i in range(1, len(data)):
                prev = data[i - 1]['timestamp']
                cur = data[i]['timestamp']
                if cur - prev > step * 1.5:
                    gap_start = prev + step
                    gap_end = cur - step
                    break

            if gap_start is None:
                continue

            expected = int((gap_end - gap_start) / step) + 1 if gap_end >= gap_start else 0
            if expected <= 0:
                continue

            note = f'detected gap in latest window (bars={len(data)})'
            res = convex_mutation('repairQueue:enqueue', {
                'ticker': ticker,
                'tf': tf,
                'windowStartTs': int(gap_start),
                'windowEndTs': int(gap_end),
                'expectedBars': expected,
                'note': note,
            })
            enq += 1
            time.sleep(args.sleep)

    print(json.dumps({'ok': True, 'checked': checked, 'enqueued': enq}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
