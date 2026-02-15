#!/usr/bin/env python3
"""Backfill VN candles (1D/1H/15m) from public VCI provider via vnstock -> Convex.

This is the "B" plan: use a public VN data source for candles, keep Simplize for fundamentals.

Requirements:
- Run from repo root with venv: ./.venv
- pip install vnstock pytz (already installed in ./ .venv)

Env:
- CONVEX_URL or NEXT_PUBLIC_CONVEX_URL (e.g. https://opulent-hummingbird-838.convex.cloud)

Usage examples:
  . .venv/bin/activate
  python scripts/vietmarket_candles_backfill.py --tickers VCB,FPT --tfs 1d,1h,15m --start 2000-01-01

  python scripts/vietmarket_candles_backfill.py --universe data/simplize/universe.latest.json --tfs 1d --start 2000-01-01 --limit-tickers 50

Notes:
- Convex mutation path: candles:upsertMany
- We currently call the mutation without admin auth. If you want to lock it down,
  we can add an ingest-only auth token check in Convex.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime
from typing import Iterable

import requests
from vnstock import Vnstock


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--tickers', help='Comma-separated tickers (e.g. VCB,FPT).')
    p.add_argument('--universe', help='Path to universe.latest.json (Simplize) or a plain text list.')
    p.add_argument('--limit-tickers', type=int, default=0, help='Limit number of tickers for testing.')
    p.add_argument('--tfs', default='1d,1h,15m', help='Timeframes: 1d,1h,15m (comma-separated).')
    p.add_argument('--start', default='2000-01-01', help='Start date (YYYY-MM-DD)')
    p.add_argument('--end', default=None, help='End date (YYYY-MM-DD) optional')
    p.add_argument('--chunk', type=int, default=1000, help='Candles per Convex call')
    p.add_argument('--sleep', type=float, default=0.15, help='Sleep seconds between Convex calls')
    p.add_argument('--dry-run', action='store_true')
    return p.parse_args(argv)


def load_tickers(args: argparse.Namespace) -> list[str]:
    tickers: list[str] = []
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(',') if t.strip()]
    elif args.universe:
        path = args.universe
        text = open(path, 'r', encoding='utf-8').read().strip()
        if text.startswith('{'):
            obj = json.loads(text)
            cand = obj.get('tickers') or []
            tickers = [str(t).strip().upper() for t in cand if str(t).strip()]
        else:
            tickers = [t.strip().upper() for t in text.split() if t.strip()]

    # add a few VN indices (vnstock expects names containing INDEX)
    # We'll start with the common ones; adjust later if needed.
    idx = ['VNINDEX', 'HNXINDEX', 'UPCOMINDEX']
    for x in idx:
        if x not in tickers:
            tickers.append(x)

    # uniq preserve order
    seen = set()
    out = []
    for t in tickers:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)

    if args.limit_tickers and args.limit_tickers > 0:
        out = out[: args.limit_tickers]
    return out


def tf_to_interval(tf: str) -> str:
    tf = tf.lower().strip()
    if tf == '1d':
        return '1D'
    if tf == '1h':
        return '1H'
    if tf == '15m':
        return '15m'
    raise ValueError(f'Unsupported tf: {tf}')


def ts_to_ms(x) -> int:
    # vnstock returns pandas timestamps in either date or datetime; stringify and parse.
    if isinstance(x, (int, float)):
        # assume seconds
        return int(x) * 1000
    s = str(x)
    # handle 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
    if len(s) == 10:
        dt = datetime.strptime(s, '%Y-%m-%d')
    else:
        dt = datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    return int(dt.timestamp() * 1000)


def convex_url() -> str:
    u = os.environ.get('CONVEX_URL') or os.environ.get('NEXT_PUBLIC_CONVEX_URL')
    if not u:
        raise RuntimeError('Missing CONVEX_URL or NEXT_PUBLIC_CONVEX_URL')
    return u.rstrip('/')


def convex_mutation(path: str, args: dict) -> dict:
    url = convex_url() + '/api/mutation'
    r = requests.post(url, json={'path': path, 'args': args}, timeout=60)
    r.raise_for_status()
    return r.json()


def chunked(xs: list, n: int):
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


def fetch_candles_vci(symbol: str, interval: str, start: str, end: str | None):
    q = Vnstock().stock(symbol=symbol, source='VCI').quote
    # vnstock requires start or length; we always pass start.
    df = q.history(symbol=symbol, start=start, end=end, interval=interval)
    # columns: time, open, high, low, close, volume
    return df


def suppress_vnstock_info_logs() -> None:
    """vnstock logs a lot of INFO lines; suppress to keep cron output readable."""
    import logging

    # Root/basic config can still emit; reduce overall noise too.
    logging.getLogger().setLevel(logging.WARNING)

    for name in [
        'vnstock',
        'vnstock.common.data',
        'vnai',
        'vnai.beam.quota',
    ]:
        try:
            logging.getLogger(name).setLevel(logging.ERROR)
        except Exception:
            pass


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    suppress_vnstock_info_logs()
    tfs = [t.strip().lower() for t in args.tfs.split(',') if t.strip()]
    tickers = load_tickers(args)

    print(json.dumps({
        'ok': True,
        'tickers': len(tickers),
        'tfs': tfs,
        'start': args.start,
        'end': args.end,
        'dryRun': args.dry_run,
    }, indent=2))

    for ti, ticker in enumerate(tickers):
        for tf in tfs:
            interval = tf_to_interval(tf)
            try:
                df = fetch_candles_vci(ticker, interval, args.start, args.end)
            except Exception as e:
                print(f'ERROR fetch {ticker} {tf}: {e}', file=sys.stderr)
                continue

            # drop NaNs
            rows = []
            for _, r in df.iterrows():
                o = r.get('open')
                h = r.get('high')
                l = r.get('low')
                c = r.get('close')
                if any(x is None or (isinstance(x, float) and math.isnan(x)) for x in [o, h, l, c]):
                    continue
                rows.append({
                    'ts': ts_to_ms(r.get('time')),
                    'o': float(o),
                    'h': float(h),
                    'l': float(l),
                    'c': float(c),
                    'v': float(r.get('volume')) if r.get('volume') is not None else None,
                    'source': 'vci',
                })

            print(f'{ticker} {tf}: fetched={len(df)} kept={len(rows)}')
            if args.dry_run:
                continue

            # upsert in chunks
            for batch in chunked(rows, args.chunk):
                payload = {
                    'ticker': ticker,
                    'tf': tf,
                    'candles': batch,
                }
                try:
                    out = convex_mutation('candles:upsertMany', payload)
                except Exception as e:
                    print(f'ERROR convex upsert {ticker} {tf}: {e}', file=sys.stderr)
                    break

                # convex returns {status:'success', value:...} or similar; print minimal
                if isinstance(out, dict) and 'value' in out:
                    v = out.get('value')
                    print(f'  upserted: {v}')
                time.sleep(args.sleep)

    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
