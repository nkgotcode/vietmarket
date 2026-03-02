#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

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


def build_resolver(watchlists: dict, portfolio: dict, account: str):
    def resolve_symbols(rule: dict):
        scope = rule.get('scope', {})
        selector = scope.get('symbol_selector', 'static')
        if selector == 'all':
            return ['*']
        if selector == 'static':
            return sorted(set(scope.get('symbols') or []))
        if selector == 'watchlist':
            wid = scope.get('watchlist_id')
            return sorted(set((watchlists.get(wid) or {}).get('symbols') or []))
        if selector == 'portfolio':
            pf = scope.get('portfolio_filter') or {}
            account_ids = pf.get('account_ids') or [account]
            min_w = float(pf.get('min_weight_pct', 0) or 0)
            symbols = set()
            for aid in account_ids:
                pos = (portfolio.get('accounts', {}).get(aid, {}) or {}).get('positions', [])
                for p in pos:
                    if float(p.get('weight_pct', 0) or 0) >= min_w and p.get('symbol'):
                        symbols.add(p['symbol'])
            return sorted(symbols)
        return []

    return resolve_symbols


def process_one_event(event: dict, rules: list[dict], resolver, store, channels_cfg: dict, firelog: Path | None):
    results = process_event(event, rules, resolver, store, channels_cfg)
    rows = [r.__dict__ for r in results]
    if firelog is not None:
        for r in rows:
            if r.get('fired'):
                append_jsonl(firelog, {
                    'ts': int(time.time()),
                    'event_id': event.get('event_id'),
                    'event_type': event.get('event_type'),
                    'symbol': event.get('symbol'),
                    **r,
                })
    return rows


def tail_jsonl(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    with path.open('r', encoding='utf-8') as f:
        f.seek(0, 2)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.3)
                continue
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--rules', default='config/alerts/rules.v1.yaml')
    ap.add_argument('--watchlists', default='config/alerts/watchlists.json')
    ap.add_argument('--portfolio', default='config/alerts/portfolio_symbols_current.json')
    ap.add_argument('--channels', default='config/alerts/channels.json')
    ap.add_argument('--event-file', default=None, help='Path to one JSON event')
    ap.add_argument('--events-jsonl', default=None, help='Tail this JSONL file as daemon input')
    ap.add_argument('--state', default='runtime/alerts/state.json')
    ap.add_argument('--firelog', default='runtime/alerts/fires.jsonl')
    ap.add_argument('--account', default='primary')
    args = ap.parse_args()

    if not args.event_file and not args.events_jsonl:
        raise SystemExit('Provide --event-file or --events-jsonl')

    rules_doc = load_yaml(Path(args.rules))
    rules = rules_doc.get('rules', [])
    watchlists = load_json(Path(args.watchlists), {})
    portfolio = load_json(Path(args.portfolio), {'accounts': {}})
    channels_cfg = load_json(Path(args.channels), {})
    resolver = build_resolver(watchlists, portfolio, args.account)
    store = JsonStateStore(args.state)
    firelog = Path(args.firelog) if args.firelog else None

    if args.event_file:
        event = load_json(Path(args.event_file), {})
        rows = process_one_event(event, rules, resolver, store, channels_cfg, firelog)
        print(json.dumps(rows, indent=2))
        return 0

    # daemon mode
    print(f'[alert-engine] tailing {args.events_jsonl}')
    for event in tail_jsonl(Path(args.events_jsonl)):
        rows = process_one_event(event, rules, resolver, store, channels_cfg, firelog)
        fired = [r for r in rows if r.get('fired')]
        if fired:
            print(json.dumps({'event_id': event.get('event_id'), 'fired': fired}, ensure_ascii=False))

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
