#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import select
import time
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from engine.core import process_event
from engine.state_store import JsonStateStore


def load_yaml(path: Path):
    import yaml  # type: ignore
    return yaml.safe_load(path.read_text())


def load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def append_jsonl(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


def build_resolver(state_refs: dict, account: str):
    def resolve_symbols(rule: dict):
        scope = rule.get('scope', {})
        selector = scope.get('symbol_selector', 'static')
        if selector == 'all':
            return ['*']
        if selector == 'static':
            return sorted(set(scope.get('symbols') or []))
        if selector == 'watchlist':
            wid = scope.get('watchlist_id')
            watchlists = state_refs.get("watchlists", {})
            return sorted(set((watchlists.get(wid) or {}).get('symbols') or []))
        if selector == 'portfolio':
            pf = scope.get('portfolio_filter') or {}
            account_ids = pf.get('account_ids') or [account]
            min_w = float(pf.get('min_weight_pct', 0) or 0)
            symbols = set()
            portfolio = state_refs.get("portfolio", {"accounts": {}})
            for aid in account_ids:
                pos = (portfolio.get('accounts', {}).get(aid, {}) or {}).get('positions', [])
                for p in pos:
                    if float(p.get('weight_pct', 0) or 0) >= min_w and p.get('symbol'):
                        symbols.add(p['symbol'])
            return sorted(symbols)
        return []

    return resolve_symbols


def row_to_event(r):
    return {
        'event_id': r[1],
        'event_type': r[2],
        'source': r[3],
        'symbol': r[4],
        'tf': r[5],
        'account_id': r[6],
        'venue': r[7],
        'ts_ns': int(r[8]),
        'payload': r[9] or {},
        'tags': r[10] or [],
    }


def process_event_id(conn, event_id: str, rules, resolver, store, channels_cfg, firelog: Path):
    with conn.cursor() as cur:
        cur.execute("""
          UPDATE alert_events
          SET processing_state='processing', attempts=attempts+1
          WHERE event_id=%s AND processing_state IN ('pending','error')
          RETURNING id,event_id,event_type,source,symbol,tf,account_id,venue,ts_ns,payload,tags
        """, (event_id,))
        row = cur.fetchone()
        if not row:
            return False
        event = row_to_event(row)

    try:
        results = process_event(event, rules, resolver, store, channels_cfg)
        with conn.cursor() as cur:
            cur.execute("UPDATE alert_events SET processing_state='done', processed_at=now(), last_error=NULL WHERE event_id=%s", (event_id,))
        for r in results:
            if r.fired:
                append_jsonl(firelog, {
                    'ts': int(time.time()),
                    'event_id': event.get('event_id'),
                    'event_type': event.get('event_type'),
                    'symbol': event.get('symbol'),
                    'rule_id': r.rule_id,
                    'fired': True,
                    'reason': r.reason,
                })
        return True
    except Exception as e:
        with conn.cursor() as cur:
            cur.execute("UPDATE alert_events SET processing_state='error', last_error=%s WHERE event_id=%s", (str(e)[:1000], event_id))
        return False


def replay_pending(conn, limit: int, rules, resolver, store, channels_cfg, firelog: Path):
    n = 0
    with conn.cursor() as cur:
        cur.execute("""
          UPDATE alert_events
          SET processing_state='pending'
          WHERE processing_state='processing' AND created_at < now() - interval '5 minutes'
        """)
        cur.execute("""
          SELECT event_id FROM alert_events
          WHERE processing_state IN ('pending','error')
          ORDER BY created_at ASC
          LIMIT %s
        """, (limit,))
        ids = [r[0] for r in cur.fetchall()]
    for eid in ids:
        if process_event_id(conn, eid, rules, resolver, store, channels_cfg, firelog):
            n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--pg-url', required=True)
    ap.add_argument('--rules', default='config/alerts/rules.v1.yaml')
    ap.add_argument('--watchlists', default='config/alerts/watchlists.json')
    ap.add_argument('--portfolio', default='config/alerts/portfolio_symbols_current.json')
    ap.add_argument('--channels', default='config/alerts/channels.json')
    ap.add_argument('--state', default='runtime/alerts/state.json')
    ap.add_argument('--firelog', default='runtime/alerts/fires.jsonl')
    ap.add_argument('--account', default='primary')
    ap.add_argument('--replay-limit', type=int, default=1000)
    args = ap.parse_args()

    rules_doc = load_yaml(Path(args.rules))
    rules = rules_doc.get('rules', [])
    state_refs = {
        "watchlists": load_json(Path(args.watchlists), {}),
        "portfolio": load_json(Path(args.portfolio), {"accounts": {}}),
    }
    channels_cfg = load_json(Path(args.channels), {})
    resolver = build_resolver(state_refs, args.account)
    store = JsonStateStore(args.state)
    firelog = Path(args.firelog)

    conn = psycopg2.connect(args.pg_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    with conn.cursor() as cur:
        cur.execute('LISTEN alert_events;')
        cur.execute('LISTEN watchlist_updates;')
        cur.execute('LISTEN portfolio_updates;')

    replayed = replay_pending(conn, args.replay_limit, rules, resolver, store, channels_cfg, firelog)
    print(json.dumps({'ok': True, 'replayed': replayed, 'listen': 'alert_events'}))

    while True:
        if select.select([conn], [], [], 60) == ([], [], []):
            continue
        conn.poll()
        while conn.notifies:
            notify = conn.notifies.pop(0)
            if notify.channel == 'alert_events':
                event_id = notify.payload
                process_event_id(conn, event_id, rules, resolver, store, channels_cfg, firelog)
            elif notify.channel == 'watchlist_updates':
                state_refs['watchlists'] = load_json(Path(args.watchlists), {})
                print(json.dumps({'reloaded': 'watchlists'}))
            elif notify.channel == 'portfolio_updates':
                state_refs['portfolio'] = load_json(Path(args.portfolio), {'accounts': {}})
                print(json.dumps({'reloaded': 'portfolio'}))


if __name__ == '__main__':
    raise SystemExit(main())
