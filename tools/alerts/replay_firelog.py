#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--firelog', default='runtime/alerts/fires.jsonl')
    ap.add_argument('--rule-id', default=None)
    args = ap.parse_args()

    p = Path(args.firelog)
    if not p.exists():
        print(json.dumps({'count': 0, 'by_rule': {}}, indent=2))
        return 0

    rows = []
    for line in p.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if args.rule_id and r.get('rule_id') != args.rule_id:
            continue
        rows.append(r)

    by_rule = Counter(r.get('rule_id') for r in rows)
    out = {
        'count': len(rows),
        'by_rule': dict(by_rule),
        'last_5': rows[-5:],
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
