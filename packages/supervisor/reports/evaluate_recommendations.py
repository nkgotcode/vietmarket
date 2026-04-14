#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


import json
from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_outcome_id
from packages.supervisor.common.time import utc_now

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute('DELETE FROM recommendation_outcomes')
        cur.execute('SELECT recommendation_id, ticker FROM recommendations ORDER BY created_at DESC LIMIT 100')
        recs = cur.fetchall()
        out = []
        for recommendation_id, ticker in recs:
            cur.execute('SELECT ret_5d FROM ticker_snapshots WHERE cycle_id = (select cycle_id from market_state_cycles order by created_at desc limit 1) AND ticker = %s LIMIT 1', (ticker,))
            row = cur.fetchone()
            ret_5d = float(row[0]) if row and row[0] is not None else 0.0
            status = 'positive' if ret_5d > 0 else ('negative' if ret_5d < 0 else 'flat')
            cur.execute('INSERT INTO recommendation_outcomes (outcome_id, recommendation_id, outcome_status, outcome_json, created_at) VALUES (%s,%s,%s,%s,%s)', (new_outcome_id(), recommendation_id, status, json.dumps({'ret_5d': ret_5d, 'ticker': ticker}), utc_now()))
            out.append({'ticker': ticker, 'status': status, 'ret_5d': ret_5d})
        print(json.dumps({'ok': True, 'count': len(out), 'preview': out[:10]}, ensure_ascii=False))
