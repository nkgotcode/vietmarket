#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import psycopg2


def write_atomic(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False))
    tmp.replace(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--pg-url', required=True)
    ap.add_argument('--watchlists-file', default='config/alerts/watchlists.json')
    ap.add_argument('--portfolio-file', default='config/alerts/portfolio_symbols_current.json')
    ap.add_argument('--watchlists-json', default=None, help='JSON string to write then notify watchlist_updates')
    ap.add_argument('--portfolio-json', default=None, help='JSON string to write then notify portfolio_updates')
    args = ap.parse_args()

    with psycopg2.connect(args.pg_url) as conn, conn.cursor() as cur:
        if args.watchlists_json:
            obj = json.loads(args.watchlists_json)
            write_atomic(Path(args.watchlists_file), obj)
            cur.execute("SELECT pg_notify('watchlist_updates', 'watchlists')")
        if args.portfolio_json:
            obj = json.loads(args.portfolio_json)
            write_atomic(Path(args.portfolio_file), obj)
            cur.execute("SELECT pg_notify('portfolio_updates', 'portfolio')")

    print(json.dumps({'ok': True}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
