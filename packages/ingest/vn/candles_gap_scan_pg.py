#!/usr/bin/env python3
"""Scan Timescale candles for obvious gaps and enqueue repairs in Timescale.

This replaces the Convex-based repair queue.

Current behavior (v1):
- For each (ticker, tf) in a recent window, scan consecutive candles ordered by ts.
- If delta between consecutive bars exceeds 2x expected interval, enqueue a repair window.

Env:
- PG_URL (required)

Args:
- --tf 1d|1h|15m
- --lookback-days N (default 30)
- --limit-tickers N (default 200)
"""

from __future__ import annotations

import argparse
import os

import psycopg2

INTERVAL_MS = {
    '1d': 24 * 60 * 60 * 1000,
    '1h': 60 * 60 * 1000,
    '15m': 15 * 60 * 1000,
}


def pg_url() -> str:
    u = os.environ.get('PG_URL')
    if not u:
        raise RuntimeError('Missing PG_URL')
    return u


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--tf', default='1d')
    p.add_argument('--lookback-days', type=int, default=30)
    p.add_argument('--limit-tickers', type=int, default=200)
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    tf = args.tf
    interval = INTERVAL_MS.get(tf)
    if not interval:
        raise RuntimeError('bad tf')

    with psycopg2.connect(pg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ticker
                FROM candles
                WHERE tf = %s
                ORDER BY ticker
                LIMIT %s
                """,
                (tf, args.limit_tickers),
            )
            tickers = [r[0] for r in cur.fetchall()]

            enq = 0
            for t in tickers:
                cur.execute(
                    """
                    SELECT ts
                    FROM candles
                    WHERE ticker=%s AND tf=%s
                      AND ts >= (extract(epoch from now() - (%s || ' days')::interval) * 1000)::bigint
                    ORDER BY ts ASC
                    """,
                    (t, tf, args.lookback_days),
                )
                ts_rows = [r[0] for r in cur.fetchall()]
                if len(ts_rows) < 2:
                    continue

                for a, b in zip(ts_rows, ts_rows[1:]):
                    if (b - a) > (2 * interval):
                        # enqueue repair for missing region (a,b)
                        ws = a + interval
                        we = b - interval
                        cur.execute(
                            """
                            INSERT INTO candle_repair_queue (ticker, tf, window_start_ts, window_end_ts, reason)
                            VALUES (%s,%s,%s,%s,%s)
                            ON CONFLICT (ticker, tf, window_start_ts, window_end_ts) DO NOTHING
                            """,
                            (t, tf, ws, we, f"gap {a}->{b}"),
                        )
                        enq += 1

            print({"ok": True, "tf": tf, "enqueued": enq, "tickers": len(tickers)})

    return 0


if __name__ == '__main__':
    raise SystemExit(main(os.sys.argv[1:]))
