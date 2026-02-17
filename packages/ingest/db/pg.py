from __future__ import annotations

import os
from typing import Iterable, Sequence

import psycopg2
import psycopg2.extras


def pg_url() -> str:
    u = os.environ.get('PG_URL')
    if not u:
        raise RuntimeError('Missing PG_URL')
    return u


def pg_connect():
    return psycopg2.connect(pg_url())


def upsert_candles(*, ticker: str, tf: str, rows: Sequence[dict]) -> int:
    """Upsert candles into Timescale/Postgres.

    rows: [{ts,o,h,l,c,v,source}]
    ts is unix ms.
    """

    if not rows:
        return 0

    values = [
        (
            ticker,
            tf,
            int(r['ts']),
            float(r['o']),
            float(r['h']),
            float(r['l']),
            float(r['c']),
            None if r.get('v') is None else float(r.get('v')),
            r.get('source'),
        )
        for r in rows
    ]

    sql = """
    INSERT INTO candles (ticker, tf, ts, o, h, l, c, v, source)
    VALUES %s
    ON CONFLICT (ticker, tf, ts)
    DO UPDATE SET
      o = EXCLUDED.o,
      h = EXCLUDED.h,
      l = EXCLUDED.l,
      c = EXCLUDED.c,
      v = EXCLUDED.v,
      source = COALESCE(EXCLUDED.source, candles.source),
      ingested_at = now();
    """.strip()

    with pg_connect() as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(cur, sql, values, page_size=1000)
    return len(values)
