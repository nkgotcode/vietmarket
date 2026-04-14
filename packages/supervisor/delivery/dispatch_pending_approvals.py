#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


import json
from packages.supervisor.common.db import connect
from packages.supervisor.delivery.events import record_delivery_event
from packages.supervisor.delivery.telegram import prepare_telegram_message, send_telegram_message

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            '''
            SELECT a.approval_id, a.staging_id, a.approval_status, s.ticker, s.side, s.qty
            FROM execution_approvals a
            JOIN broker_order_staging s ON s.staging_id = a.staging_id
            ORDER BY a.created_at DESC
            LIMIT 10
            '''
        )
        rows = cur.fetchall()
        lines = ['Pending approvals']
        for approval_id, staging_id, approval_status, ticker, side, qty in rows:
            lines.append(f'- {ticker} {side} qty={qty} approval={approval_status} staging={staging_id}')
        message = prepare_telegram_message('\n'.join(lines))
        delivery = send_telegram_message(message)
        event = record_delivery_event(delivery_kind='approval_queue', channel='telegram', delivery_status=delivery['delivery_status'], target_ref=str(message.get('chat_id') or ''), payload=message, response=delivery)
        print(json.dumps({'ok': delivery.get('ok', False), 'approval_count': len(rows), 'message': message, 'delivery': delivery, 'event': event}, ensure_ascii=False))
