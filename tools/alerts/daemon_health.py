#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time
import psycopg2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--pg-url', required=True)
    ap.add_argument('--warn-pending', type=int, default=1000)
    ap.add_argument('--warn-error', type=int, default=10)
    args = ap.parse_args()

    out = {'ok': True, 'at': int(time.time()), 'checks': {}}
    with psycopg2.connect(args.pg_url) as conn, conn.cursor() as cur:
      cur.execute("select count(*) from alert_events where processing_state='pending'")
      pending = cur.fetchone()[0]
      cur.execute("select count(*) from alert_events where processing_state='error'")
      error = cur.fetchone()[0]
      cur.execute("select count(*) from alert_events where processing_state='processing' and created_at < now() - interval '5 minutes'")
      stuck = cur.fetchone()[0]
      out['checks']={'pending':pending,'error':error,'stuck_processing':stuck}
      if pending > args.warn_pending or error > args.warn_error or stuck > 0:
          out['ok'] = False

    print(json.dumps(out, ensure_ascii=False))
    return 0 if out['ok'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
