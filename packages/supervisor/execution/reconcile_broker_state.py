#!/usr/bin/env python3
from __future__ import annotations

import json
from packages.supervisor.common.db import connect

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute('DELETE FROM broker_positions_mirror')
        cur.execute("INSERT INTO broker_accounts (account_id, broker_name, account_label, account_status, created_at) VALUES ('paper_account','paper','Paper account','paper_only',now()) ON CONFLICT (account_id) DO NOTHING")
        cur.execute('SELECT ticker, qty, market_value FROM positions')
        rows = cur.fetchall()
        for ticker, qty, market_value in rows:
            cur.execute('INSERT INTO broker_positions_mirror (account_id, ticker, qty, market_value, mirror_json, updated_at) VALUES (%s,%s,%s,%s,%s,now())', ('paper_account', ticker, qty, market_value, json.dumps({'source': 'positions'})))
        print(json.dumps({'ok': True, 'count': len(rows)}, ensure_ascii=False))
