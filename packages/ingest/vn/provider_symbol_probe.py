#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone

from vnstock import Vnstock

SYMBOLS = ["EMC", "TS4", "X77"]


def probe(symbol: str):
    try:
        q = Vnstock().stock(symbol=symbol, source='VCI').quote
        df = q.history(symbol=symbol, start='2024-01-01', interval='1D')
        rows = 0 if df is None else int(len(df))
        return {
            'symbol': symbol,
            'provider': 'VCI/vnstock',
            'ok': rows > 0,
            'rows': rows,
            'status': 'present' if rows > 0 else 'provider-hard-missing',
            'error': None,
        }
    except Exception as e:
        return {
            'symbol': symbol,
            'provider': 'VCI/vnstock',
            'ok': False,
            'rows': 0,
            'status': 'provider-hard-missing',
            'error': str(e),
        }


def main():
    out = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'results': [probe(s) for s in SYMBOLS],
    }
    out['all_hard_missing'] = all((not r['ok']) for r in out['results'])
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
