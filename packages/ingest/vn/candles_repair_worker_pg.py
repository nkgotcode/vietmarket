#!/usr/bin/env python3
"""Consume Timescale candle_repair_queue and fill gaps using vnstock VCI.

Env:
- PG_URL (required)

Args:
- --limit N (default 5)

Note:
- This uses the same vnstock fetcher as candles_backfill.py and upserts into Timescale.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime

import psycopg2

# Container runs with cwd=/app; make repo root importable.
VIETMARKET_ROOT = os.environ.get('VIETMARKET_ROOT', '/app')
if VIETMARKET_ROOT not in sys.path:
    sys.path.insert(0, VIETMARKET_ROOT)

from packages.ingest.db.pg import upsert_candles
from packages.ingest.vn.candles_backfill import fetch_candles_vci, tf_to_interval, ms_to_date, ts_to_ms


def pg_url() -> str:
    u = os.environ.get('PG_URL')
    if not u:
        raise RuntimeError('Missing PG_URL')
    return u


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--limit', type=int, default=5)
    p.add_argument('--sleep', type=float, default=0.2)
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    with psycopg2.connect(pg_url()) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, ticker, tf, window_start_ts, window_end_ts, attempts
                FROM candle_repair_queue
                WHERE status='queued'
                ORDER BY created_at ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED
                """,
                (args.limit,),
            )
            rows = cur.fetchall()
            if not rows:
                print({"ok": True, "processed": 0, "reason": "no queued"})
                conn.commit()
                return 0

            # mark running
            ids = [r[0] for r in rows]
            cur.execute(
                """
                UPDATE candle_repair_queue
                SET status='running', attempts=attempts+1, updated_at=now()
                WHERE id = ANY(%s)
                """,
                (ids,),
            )
            conn.commit()

    processed = 0
    for (qid, ticker, tf, ws, we, _attempts) in rows:
        try:
            interval = tf_to_interval(tf)
            start_str = ms_to_date(int(ws))
            end_str = ms_to_date(int(we))
            df = fetch_candles_vci(ticker, interval, start_str, end_str)

            out = []
            for _, r in df.iterrows():
                o, h, l, c = r.get('open'), r.get('high'), r.get('low'), r.get('close')
                if o is None or h is None or l is None or c is None:
                    continue
                out.append({
                    'ts': ts_to_ms(r.get('time')),
                    'o': float(o),
                    'h': float(h),
                    'l': float(l),
                    'c': float(c),
                    'v': float(r.get('volume')) if r.get('volume') is not None else None,
                    'source': 'vci-repair',
                })

            upsert_candles(ticker=ticker, tf=tf, rows=out)

            with psycopg2.connect(pg_url()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE candle_repair_queue SET status='done', updated_at=now(), last_error=NULL WHERE id=%s",
                        (qid,),
                    )
            processed += 1
            time.sleep(args.sleep)
        except Exception as e:
            with psycopg2.connect(pg_url()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE candle_repair_queue SET status='error', updated_at=now(), last_error=%s WHERE id=%s",
                        (str(e)[:800], qid),
                    )

    print({"ok": True, "processed": processed})
    return 0


if __name__ == '__main__':
    raise SystemExit(main(os.sys.argv[1:]))
