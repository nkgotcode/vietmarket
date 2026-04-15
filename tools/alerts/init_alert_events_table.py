#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import psycopg2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--pg-url', required=True)
    ap.add_argument('--sql', default='tools/alerts/sql/alert_events.sql')
    args = ap.parse_args()

    sql = Path(args.sql).read_text()
    with psycopg2.connect(args.pg_url) as conn, conn.cursor() as cur:
        cur.execute(sql)
    print('ok')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
