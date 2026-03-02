#!/usr/bin/env python3
"""Emit normalized alert events from VietMarket Postgres into JSONL.

This is a lightweight producer for the alert engine daemon.
"""
from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

import psycopg2
from engine.schema_validate import validate_event


def append_jsonl(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_state(path: Path, state: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def ns_now() -> int:
    return int(time.time() * 1_000_000_000)

def emit_event(cur, events_path: Path, event: dict, args):
    ok, err = validate_event(event, args.event_schema)
    if not ok:
      log_ingress_error(cur, event, err or 'invalid_event')
      if args.strict_ingress:
          return False
    append_jsonl(events_path, event)
    if args.db_queue and ok:
        enqueue_db_event(cur, event)
    return True



def log_ingress_error(cur, event: dict, error: str):
    cur.execute(
        """
        INSERT INTO ingress_errors (event_id, source, event_type, payload, error)
        VALUES (%s,%s,%s,%s::jsonb,%s)
        """,
        (
            event.get('event_id'),
            event.get('source'),
            event.get('event_type'),
            json.dumps(event, ensure_ascii=False),
            str(error)[:2000],
        ),
    )


def enqueue_db_event(cur, event: dict):
    cur.execute(
        """
        INSERT INTO alert_events (
          event_id, event_type, source, symbol, tf, account_id, venue, ts_ns, payload, tags, processing_state
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,'pending')
        ON CONFLICT (event_id) DO NOTHING
        """,
        (
            event.get('event_id'), event.get('event_type'), event.get('source'), event.get('symbol'),
            event.get('tf'), event.get('account_id'), event.get('venue'), int(event.get('ts_ns') or 0),
            json.dumps(event.get('payload') or {}, ensure_ascii=False),
            json.dumps(event.get('tags') or [], ensure_ascii=False),
        ),
    )
    if cur.rowcount > 0:
        cur.execute("SELECT pg_notify('alert_events', %s)", (str(event.get('event_id')),))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--pg-url', required=True)
    ap.add_argument('--events-jsonl', default='runtime/alerts/events.jsonl')
    ap.add_argument('--state', default='runtime/alerts/producer_state.json')
    ap.add_argument('--symbol', action='append', default=[])
    ap.add_argument('--emit-news', action='store_true')
    ap.add_argument('--emit-health', action='store_true')
    ap.add_argument('--db-queue', action='store_true', help='Also enqueue events into alert_events and NOTIFY')
    ap.add_argument('--event-schema', default='docs/schemas/alert-event.schema.json')
    ap.add_argument('--strict-ingress', action='store_true', default=True)
    args = ap.parse_args()

    events_path = Path(args.events_jsonl)
    state_path = Path(args.state)
    state = load_state(state_path)

    sym_filter = tuple(args.symbol) if args.symbol else None

    with psycopg2.connect(args.pg_url) as conn, conn.cursor() as cur:
        # indicator.update from technical_indicators delta by asof_ts
        q = """
        SELECT ticker, tf, asof_ts, close, sma20, sma50, ema20, rsi14, macd, macd_signal, macd_hist, atr14
        FROM technical_indicators
        WHERE asof_ts > %s
        """
        params = [int(state.get('last_asof_ts', 0) or 0)]
        if sym_filter:
            q += " AND ticker = ANY(%s)"
            params.append(list(sym_filter))
        q += " ORDER BY asof_ts ASC LIMIT 5000"
        cur.execute(q, tuple(params))
        rows = cur.fetchall()

        max_asof = state.get('last_asof_ts', 0)
        for r in rows:
            ticker, tf, asof_ts, close, sma20, sma50, ema20, rsi14, macd, macd_signal, macd_hist, atr14 = r
            evt = {
                'event_id': f"evt-ind-{uuid.uuid4().hex[:12]}",
                'event_type': 'indicator.update',
                'source': 'vietmarket',
                'symbol': ticker,
                'tf': tf,
                'ts_ns': int(asof_ts) * 1_000_000,
                'payload': {
                    'close': close,
                    'sma20': sma20,
                    'sma50': sma50,
                    'ema20': ema20,
                    'rsi14': rsi14,
                    'macd': macd,
                    'macd_signal': macd_signal,
                    'macd_hist': macd_hist,
                    'atr14': atr14,
                },
                'tags': []
            }
            emit_event(cur, events_path, evt, args)
            if int(asof_ts) > int(max_asof):
                max_asof = int(asof_ts)

        state['last_asof_ts'] = int(max_asof)

        # news.item from article publish time
        if args.emit_news:
            q2 = """
            SELECT a.url, a.published_at, a.source, a.title, s.ticker
            FROM articles a
            JOIN article_symbols s ON s.article_url = a.url
            WHERE a.fetch_status='fetched'
              AND a.published_at IS NOT NULL
              AND extract(epoch from a.published_at) > %s
            """
            p2 = [float(state.get('last_news_epoch', 0) or 0)]
            if sym_filter:
                q2 += " AND s.ticker = ANY(%s)"
                p2.append(list(sym_filter))
            q2 += " ORDER BY a.published_at ASC LIMIT 2000"
            cur.execute(q2, tuple(p2))
            rows2 = cur.fetchall()
            max_ep = float(state.get('last_news_epoch', 0) or 0)
            for url, pub, src, title, ticker in rows2:
                ep = pub.timestamp()
                evt = {
                    'event_id': f"evt-news-{uuid.uuid4().hex[:12]}",
                    'event_type': 'news.item',
                    'source': 'vietmarket',
                    'symbol': ticker,
                    'tf': None,
                    'ts_ns': int(ep * 1_000_000_000),
                    'payload': {
                        'headline': title,
                        'url': url,
                        'impact_score': 0.5,
                        'novelty_score': 0.5,
                        'source': src,
                    },
                    'tags': []
                }
                emit_event(cur, events_path, evt, args)
                if ep > max_ep:
                    max_ep = ep
            state['last_news_epoch'] = max_ep

        # system.health from market_stats
        if args.emit_health:
            cur.execute("""
            SELECT metric, value_numeric, value_text, extract(epoch from updated_at)
            FROM market_stats
            WHERE metric in ('candles_frontier_lag_ms')
            ORDER BY updated_at DESC
            LIMIT 10
            """)
            for metric, vn, vt, upd_ep in cur.fetchall():
                evt = {
                    'event_id': f"evt-health-{uuid.uuid4().hex[:12]}",
                    'event_type': 'system.health',
                    'source': 'ops',
                    'symbol': None,
                    'tf': None,
                    'ts_ns': int(float(upd_ep) * 1_000_000_000) if upd_ep else ns_now(),
                    'payload': {
                        'metric': metric,
                        'value': vn,
                        'value_text': vt,
                        'threshold_ms': 60 * 60 * 1000
                    },
                    'tags': ['health']
                }
                emit_event(cur, events_path, evt, args)

    save_state(state_path, state)
    print(json.dumps({'ok': True, 'state': state}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
