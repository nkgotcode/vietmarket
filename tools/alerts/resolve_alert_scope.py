#!/usr/bin/env python3
"""Resolve dynamic rule scopes (static/watchlist/portfolio/all).

Input files are JSON for deterministic, dependency-light operation.

Usage:
  python scripts/resolve_alert_scope.py \
    --rules config/alerts/rules.v1.yaml \
    --watchlists config/alerts/watchlists.json \
    --portfolio config/alerts/portfolio_symbols_current.json \
    --account primary
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_yaml(path: Path):
    try:
        import yaml  # type: ignore
    except Exception as e:
        raise RuntimeError("PyYAML is required. Install with: pip install pyyaml") from e
    return yaml.safe_load(path.read_text())


def load_json_or_default(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def resolve_rule_symbols(rule: dict, watchlists: dict, portfolio: dict, account: str | None):
    scope = rule.get("scope", {})
    selector = scope.get("symbol_selector", "static")

    if selector == "all":
        return ["*"]

    if selector == "static":
        return sorted(set(scope.get("symbols") or []))

    if selector == "watchlist":
        wid = scope.get("watchlist_id")
        return sorted(set((watchlists.get(wid) or {}).get("symbols") or []))

    if selector == "portfolio":
        pf = scope.get("portfolio_filter") or {}
        account_ids = pf.get("account_ids") or ([account] if account else [])
        min_w = float(pf.get("min_weight_pct", 0) or 0)
        symbols = set()
        for aid in account_ids:
            rows = (portfolio.get("accounts", {}).get(aid, {}) or {}).get("positions", [])
            for r in rows:
                sym = r.get("symbol")
                w = float(r.get("weight_pct", 0) or 0)
                if sym and w >= min_w:
                    symbols.add(sym)
        return sorted(symbols)

    return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", default="config/alerts/rules.v1.yaml")
    ap.add_argument("--watchlists", default="config/alerts/watchlists.json")
    ap.add_argument("--portfolio", default="config/alerts/portfolio_symbols_current.json")
    ap.add_argument("--account", default="primary")
    ap.add_argument("--rule-id", default=None)
    args = ap.parse_args()

    rules_doc = load_yaml(Path(args.rules))
    watchlists = load_json_or_default(Path(args.watchlists), default={})
    portfolio = load_json_or_default(Path(args.portfolio), default={"accounts": {}})

    out = {}
    for r in rules_doc.get("rules", []):
        rid = r.get("id")
        if args.rule_id and rid != args.rule_id:
            continue
        out[rid] = {
            "name": r.get("name"),
            "symbol_selector": (r.get("scope") or {}).get("symbol_selector", "static"),
            "resolved_symbols": resolve_rule_symbols(r, watchlists, portfolio, args.account),
        }

    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
