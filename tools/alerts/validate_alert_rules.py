#!/usr/bin/env python3
"""Validate alert rules YAML against schema + semantic checks.

Usage:
  python scripts/validate_alert_rules.py \
    --rules config/alerts/rules.v1.yaml \
    --schema docs/schemas/alert-rule.schema.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_yaml(path: Path):
    try:
        import yaml  # type: ignore
    except Exception as e:
        raise RuntimeError("PyYAML is required. Install with: pip install pyyaml") from e
    return yaml.safe_load(path.read_text())


def try_jsonschema_validate(instance, schema) -> list[str]:
    try:
        import jsonschema  # type: ignore
    except Exception:
        return ["jsonschema not installed; skipped structural schema validation (pip install jsonschema)"]

    errors = []
    v = jsonschema.Draft202012Validator(schema)
    for err in sorted(v.iter_errors(instance), key=lambda e: list(e.path)):
        loc = ".".join(map(str, err.absolute_path)) or "<root>"
        errors.append(f"{loc}: {err.message}")
    return errors


def semantic_checks(doc: dict) -> list[str]:
    errs: list[str] = []
    rules = doc.get("rules")
    if not isinstance(rules, list) or not rules:
        return ["rules must be a non-empty list"]

    seen_ids: set[str] = set()
    for i, r in enumerate(rules):
        rid = r.get("id")
        if rid in seen_ids:
            errs.append(f"rules[{i}].id duplicate: {rid}")
        seen_ids.add(rid)

        scope = r.get("scope", {})
        selector = scope.get("symbol_selector", "static")
        # static selector may omit symbols to mean "all symbols for matching event types"
        if selector == "watchlist" and not scope.get("watchlist_id"):
            errs.append(f"rules[{i}] ({rid}): watchlist selector requires scope.watchlist_id")

        trig = r.get("trigger", {})
        if trig.get("mode") == "once_until_reset" and not trig.get("reset_expr"):
            errs.append(f"rules[{i}] ({rid}): once_until_reset should provide trigger.reset_expr")

        routing = r.get("routing", {})
        if r.get("severity") == "critical" and routing.get("priority") != "timeSensitive":
            errs.append(f"rules[{i}] ({rid}): critical alerts should use routing.priority=timeSensitive")

    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", default="config/alerts/rules.v1.yaml")
    ap.add_argument("--schema", default="docs/schemas/alert-rule.schema.json")
    args = ap.parse_args()

    rules_p = Path(args.rules)
    schema_p = Path(args.schema)

    doc = load_yaml(rules_p)
    schema = json.loads(schema_p.read_text())

    all_errors = []
    if isinstance(doc, dict) and isinstance(doc.get("rules"), list):
        for i, rule in enumerate(doc["rules"]):
            for e in try_jsonschema_validate(rule, schema):
                all_errors.append(f"rules[{i}]: {e}")
    else:
        all_errors.append("rules YAML missing rules list")

    all_errors.extend(semantic_checks(doc if isinstance(doc, dict) else {}))

    hard_errors = [e for e in all_errors if not e.startswith("jsonschema not installed")]
    for e in all_errors:
        prefix = "WARN" if e.startswith("jsonschema not installed") else "ERROR"
        print(f"[{prefix}] {e}")

    if hard_errors:
        print(f"\nValidation failed with {len(hard_errors)} error(s).")
        return 1

    print("Validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
