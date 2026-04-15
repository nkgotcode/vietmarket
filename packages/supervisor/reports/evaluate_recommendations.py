#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_outcome_id, new_run_id
from packages.supervisor.common.time import utc_now

HORIZON_DAYS = 5

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute('DELETE FROM recommendation_outcomes')
        cur.execute(
            '''
            SELECT recommendation_id, ticker, forward_return, excess_return, max_drawdown, label_json
            FROM ticker_forward_outcomes
            WHERE horizon_days = %s
              AND recommendation_id IS NOT NULL
            ORDER BY created_at DESC, ticker ASC
            ''',
            (HORIZON_DAYS,),
        )
        rows = cur.fetchall()
        out = []
        for recommendation_id, ticker, forward_return, excess_return, max_drawdown, label_json in rows:
            ret = float(forward_return) if forward_return is not None else None
            status = 'pending'
            if ret is not None:
                status = 'positive' if ret > 0 else ('negative' if ret < 0 else 'flat')
            payload = {
                'ticker': ticker,
                'horizon_days': HORIZON_DAYS,
                'forward_return': ret,
                'excess_return': float(excess_return) if excess_return is not None else None,
                'max_drawdown': float(max_drawdown) if max_drawdown is not None else None,
                'label_json': label_json or {},
            }
            cur.execute(
                '''
                INSERT INTO recommendation_outcomes (
                  outcome_id, recommendation_id, outcome_status, outcome_json, created_at
                ) VALUES (%s,%s,%s,%s,%s)
                ''',
                (new_outcome_id(), recommendation_id, status, json.dumps(payload, default=str), utc_now()),
            )
            out.append({'ticker': ticker, 'status': status, 'forward_return': ret})
        print(json.dumps({'ok': True, 'count': len(out), 'horizon_days': HORIZON_DAYS, 'preview': out[:10]}, ensure_ascii=False))
