#!/usr/bin/env python3
"""Sync VN stock symbols metadata into Timescale `symbols`.

Goal: build a full (active + inactive/delisted) universe with exchange + name.

Primary source: VNDIRECT finfo API (public).

Env:
- PG_URL (required)

Optional:
- SYMBOLS_SOURCE=vndirect (default)
- VN_STOCK_FLOORS=HOSE,HNX,UPCOM (default)
- PAGE_SIZE=500 (default)
- MAX_PAGES=200 (default safety)

Writes:
- symbols(ticker,name,exchange,active,updated_at)

Notes:
- `updated_at` stored as unix ms.
- If the upstream is unreachable, script exits non-zero.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


def now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def pg_url() -> str:
    u = os.environ.get('PG_URL')
    if not u:
        raise RuntimeError('Missing PG_URL')
    return u


def vndirect_fetch_all(*, floors: list[str], page_size: int, max_pages: int) -> list[dict]:
    if requests is None:
        raise RuntimeError('Missing requests (expected in ingest image)')

    # VNDIRECT finfo API query language: use q=type:stock~floor:HOSE,HNX,UPCOM
    q = f"type:stock~floor:{','.join(floors)}"
    base = "https://finfo-api.vndirect.com.vn/v4/stocks"

    sess = requests.Session()
    out: list[dict] = []
    for page in range(1, max_pages + 1):
        url = f"{base}?q={q}&size={page_size}&page={page}"
        r = sess.get(url, timeout=30)
        r.raise_for_status()
        obj = r.json()
        data = obj.get('data') or []
        if not data:
            break
        out.extend(data)
        # Heuristic: stop early if last page smaller than page_size
        if len(data) < page_size:
            break
        time.sleep(0.05)

    if not out:
        raise RuntimeError('VNDIRECT returned 0 symbols (unexpected)')

    return out


def status_to_active(s: str | None) -> bool | None:
    if s is None:
        return None
    x = str(s).strip().lower()
    if x in ('listed', 'trading', 'active'):
        return True
    if x in ('delisted', 'inactive', 'suspended', 'halted'):
        return False
    return None


def upsert_symbols(rows: list[dict]) -> dict:
    updated = 0
    ts = now_ms()

    sql = """
    INSERT INTO symbols (ticker, name, exchange, active, updated_at)
    VALUES (%(ticker)s, %(name)s, %(exchange)s, %(active)s, %(updated_at)s)
    ON CONFLICT (ticker) DO UPDATE SET
      name = COALESCE(EXCLUDED.name, symbols.name),
      exchange = COALESCE(EXCLUDED.exchange, symbols.exchange),
      active = COALESCE(EXCLUDED.active, symbols.active),
      updated_at = GREATEST(COALESCE(symbols.updated_at, 0), EXCLUDED.updated_at);
    """.strip()

    payload = []
    for r in rows:
        ticker = (r.get('code') or r.get('ticker') or '').strip().upper()
        if not ticker:
            continue
        name = (r.get('companyName') or r.get('name') or r.get('shortName') or None)
        exchange = (r.get('floor') or r.get('exchange') or None)
        active = status_to_active(r.get('status') or r.get('active'))
        payload.append({
            'ticker': ticker,
            'name': name,
            'exchange': exchange,
            'active': active,
            'updated_at': ts,
        })

    with psycopg2.connect(pg_url()) as conn:
        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, payload, page_size=1000)
            updated = cur.rowcount

    return {'ok': True, 'upserts': len(payload), 'updated_at': ts}


def main() -> int:
    source = os.environ.get('SYMBOLS_SOURCE', 'vndirect')
    floors = [x.strip().upper() for x in os.environ.get('VN_STOCK_FLOORS', 'HOSE,HNX,UPCOM').split(',') if x.strip()]
    page_size = int(os.environ.get('PAGE_SIZE', '500'))
    max_pages = int(os.environ.get('MAX_PAGES', '200'))

    if source != 'vndirect':
        raise RuntimeError(f'Unsupported SYMBOLS_SOURCE: {source}')

    rows = vndirect_fetch_all(floors=floors, page_size=page_size, max_pages=max_pages)
    res = upsert_symbols(rows)
    res['source'] = source
    res['symbols'] = len(rows)
    print(res)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
