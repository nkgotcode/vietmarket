#!/usr/bin/env python3
"""Sync Simplize fundamentals (from local SQLite) into Timescale `fi_latest`.

Source of truth for fetched Simplize FI points is the local SQLite database produced by:
- scripts/simplize_sqlite_sync.mjs (writes data/simplize/simplize.db)

This job extracts *latest period_date per (ticker, period, statement, metric)* and upserts into:
- fi_latest(ticker, period, statement, period_date, metric, value, fetched_at, ingested_at)

Env:
- PG_URL (required)
- SIMPLIZE_DB (optional, default: data/simplize/simplize.db)
- PERIOD (optional, default: Q)

Notes:
- This is idempotent.
- Keeps `ingested_at=now()` on update.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def pg_url() -> str:
    u = os.environ.get("PG_URL")
    if not u:
        raise RuntimeError("Missing PG_URL")
    return u


def simplize_db_path() -> Path:
    return Path(os.environ.get("SIMPLIZE_DB", "data/simplize/simplize.db")).resolve()


def main() -> int:
    period = (os.environ.get("PERIOD") or "Q").strip().upper()
    if period not in ("Q", "Y"):
        raise RuntimeError("PERIOD must be Q or Y")

    dbp = simplize_db_path()
    if not dbp.exists():
        raise RuntimeError(f"simplize db not found: {dbp}")

    sconn = sqlite3.connect(str(dbp))
    sconn.row_factory = sqlite3.Row

    # Schema assumption: fi_points(ticker, period, statement, periodDate, metric, value, fetchedAt)
    # Pull latest periodDate per (ticker,period,statement,metric)
    rows = sconn.execute(
        """
        SELECT f.ticker, f.period, f.statement, f.periodDate AS period_date,
               f.metric, f.value, f.fetchedAt AS fetched_at
        FROM fi_points f
        JOIN (
          SELECT ticker, period, statement, metric, MAX(periodDate) AS maxPeriodDate
          FROM fi_points
          WHERE period = ?
          GROUP BY ticker, period, statement, metric
        ) x
        ON f.ticker = x.ticker
        AND f.period = x.period
        AND f.statement = x.statement
        AND f.metric = x.metric
        AND f.periodDate = x.maxPeriodDate
        """,
        (period,),
    )

    payload = []
    for r in rows:
        ticker = (r["ticker"] or "").strip().upper()
        if not ticker:
            continue
        pd = r["period_date"]
        # Normalize Simplize periodDate into ISO date for Postgres DATE.
        # Observed formats: YYYY-MM-DD, YYYY-MM, YYYY
        if isinstance(pd, str):
            s = pd.strip()
            if len(s) == 7 and s[4] == '-':
                pd = s + '-01'
            elif len(s) == 4 and s.isdigit():
                pd = s + '-01-01'
            else:
                pd = s

        payload.append(
            {
                "ticker": ticker,
                "period": (r["period"] or period).strip().upper(),
                "statement": (r["statement"] or "").strip().lower(),
                "period_date": pd,
                "metric": (r["metric"] or "").strip(),
                "value": r["value"],
                "fetched_at": r["fetched_at"],
            }
        )

    sconn.close()

    sql = """
    INSERT INTO fi_latest (ticker, period, statement, period_date, metric, value, fetched_at, ingested_at)
    VALUES (%(ticker)s, %(period)s, %(statement)s, %(period_date)s, %(metric)s, %(value)s, %(fetched_at)s, now())
    ON CONFLICT (ticker, period, statement, metric) DO UPDATE SET
      period_date = EXCLUDED.period_date,
      value = EXCLUDED.value,
      fetched_at = COALESCE(EXCLUDED.fetched_at, fi_latest.fetched_at),
      ingested_at = now();
    """.strip()

    with psycopg2.connect(pg_url()) as pg:
        with pg.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, payload, page_size=1000)

    print(
        {
            "ok": True,
            "period": period,
            "simplize_db": str(dbp),
            "rows_upserted": len(payload),
            "at": now_utc().isoformat(timespec="seconds"),
        }
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
