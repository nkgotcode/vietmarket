#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--rules', default='config/alerts/rules.v1.yaml')
    ap.add_argument('--watchlists', default='config/alerts/watchlists.json')
    ap.add_argument('--portfolio', default='config/alerts/portfolio_symbols_current.json')
    ap.add_argument('--channels', default='config/alerts/channels.json')
    ap.add_argument('--event-file', required=True, help='Path to JSON event')
    ap.add_argument('--state', default='runtime/alerts/state.json')
    ap.add_argument('--account', default='primary')
    args = ap.parse_args()

    rules_doc = load_yaml(Path(args.rules))
    rules = rules_doc.get('rules', [])
    watchlists = load_json(Path(args.watchlists), {})
    portfolio = load_json(Path(args.portfolio), {'accounts': {}})
    channels_cfg = load_json(Path(args.channels), {})
    event = load_json(Path(args.event_file), {})

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
            account_ids = pf.get('account_ids') or [args.account]
            min_w = float(pf.get('min_weight_pct', 0) or 0)
            symbols = set()
            for aid in account_ids:
                pos = (portfolio.get('accounts', {}).get(aid, {}) or {}).get('positions', [])
                for p in pos:
                    if float(p.get('weight_pct', 0) or 0) >= min_w and p.get('symbol'):
                        symbols.add(p['symbol'])
            return sorted(symbols)
        return []

    store = JsonStateStore(args.state)
    results = process_event(event, rules, resolve_symbols, store, channels_cfg)
    print(json.dumps([r.__dict__ for r in results], indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
