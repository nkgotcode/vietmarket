#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


import json
from packages.supervisor.common.db import connect

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT decision_id, cycle_id, ticker, decision_type, status, created_at FROM supervisor_decisions ORDER BY created_at DESC LIMIT 100")
        rows = [
            {'decision_id': r[0], 'cycle_id': r[1], 'ticker': r[2], 'decision_type': r[3], 'status': r[4], 'created_at': r[5].isoformat() if r[5] else None}
            for r in cur.fetchall()
        ]
        print(json.dumps({'ok': True, 'rows': rows}, ensure_ascii=False))
