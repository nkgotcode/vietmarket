#!/usr/bin/env python3
"""Backfill VN candles (1D/1H/15m) from public VCI provider via vnstock into Timescale/Postgres.

This is the Timescale/Postgres-only candle backfill path.

Requirements:
- Run from repo root with Python available.
- Install vnstock and psycopg2-compatible dependencies in the active environment.

Env:
- PG_URL (required)

Usage examples:
  python packages/ingest/vn/candles_backfill.py --tickers VCB,FPT --tfs 1d,1h,15m --start 2000-01-01
  python packages/ingest/vn/candles_backfill.py --universe data/simplize/universe.latest.json --tfs 1d --start 2000-01-01 --limit-tickers 50
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime

from vnstock import Vnstock

try:
    from pathlib import Path
    _root = Path(os.environ.get('VIETMARKET_ROOT', '')).resolve() if os.environ.get('VIETMARKET_ROOT') else None
    if _root and str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
except Exception:
    pass

os.environ.setdefault('VNSTOCK_SILENT', '1')


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--tickers', help='Comma-separated tickers (e.g. VCB,FPT).')
    p.add_argument('--universe', help='Path to universe.latest.json (Simplize) or a plain text list.')
    p.add_argument('--limit-tickers', type=int, default=0, help='Limit number of tickers for testing.')
    p.add_argument('--tfs', default='1d,1h,15m', help='Timeframes: 1d,1h,15m (comma-separated).')
    p.add_argument('--start', default='2000-01-01', help='Start date (YYYY-MM-DD)')
    p.add_argument('--end', default=None, help='End date (YYYY-MM-DD) optional')
    p.add_argument('--chunk', type=int, default=1000, help='Candles per PG batch')
    p.add_argument('--sleep', type=float, default=0.15, help='Sleep seconds between PG calls')
    p.add_argument('--include-indices', action='store_true', default=True, help='Include VN indices (VNINDEX/HNXINDEX/UPCOMINDEX)')
    p.add_argument('--exclude-indices', action='store_true', help='Do not include indices (useful for intraday)')
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

    include_indices = args.include_indices and (not args.exclude_indices)
    if include_indices:
        idx = ['VNINDEX', 'HNXINDEX', 'UPCOMINDEX']
        for x in idx:
            if x not in tickers:
                tickers.append(x)

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
    if isinstance(x, (int, float)):
        return int(x) * 1000
    s = str(x)
    if len(s) == 10:
        dt = datetime.strptime(s, '%Y-%m-%d')
    else:
        dt = datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    return int(dt.timestamp() * 1000)


def chunked(xs: list, n: int):
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


def fetch_candles_vci(symbol: str, interval: str, start: str, end: str | None, *, max_retries: int = 6):
    """Fetch candles from VCI via vnstock, with basic rate-limit backoff."""
    q = Vnstock().stock(symbol=symbol, source='VCI').quote

    last_err = None
    for attempt in range(max_retries + 1):
        try:
            df = q.history(symbol=symbol, start=start, end=end, interval=interval)
            return df
        except Exception as e:
            last_err = e
            msg = str(e)
            is_rl = ('Rate Limit' in msg) or ('GIỚI HẠN API' in msg) or ('20 requests' in msg)
            if is_rl and attempt < max_retries:
                sleep_s = 15 * (attempt + 1)
                time.sleep(sleep_s)
                continue
            raise

    raise last_err


def suppress_vnstock_info_logs() -> None:
    import logging

    logging.getLogger().setLevel(logging.ERROR)
    for name in [
        'vnstock',
        'vnstock.common.data',
        'vnstock.common.data.data_explorer',
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

    from packages.ingest.db.pg import upsert_candles

    for ticker in tickers:
        for tf in tfs:
            interval = tf_to_interval(tf)
            try:
                df = fetch_candles_vci(ticker, interval, args.start, args.end)
            except Exception as e:
                print(f'ERROR fetch {ticker} {tf}: {e}', file=sys.stderr)
                continue

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

            for batch in chunked(rows, args.chunk):
                try:
                    n = upsert_candles(ticker=ticker, tf=tf, rows=batch)
                    print(f'  pg upserted: {n}')
                except Exception as e:
                    print(f'ERROR pg upsert {ticker} {tf}: {e}', file=sys.stderr)
                    break
                time.sleep(args.sleep)

    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
