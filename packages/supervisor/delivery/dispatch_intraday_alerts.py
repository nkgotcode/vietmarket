#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


import json
from packages.supervisor.common.db import connect
from packages.supervisor.delivery.events import record_delivery_event
from packages.supervisor.delivery.formatter import format_intraday_alerts
from packages.supervisor.delivery.telegram import prepare_telegram_message, send_telegram_message

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT ticker, overall_result, blocking_flag FROM policy_results ORDER BY created_at DESC, ticker ASC LIMIT 20")
        alerts = [
            {'severity': 'warning' if row[2] else 'info', 'message': f'{row[0]} policy={row[1]}'}
            for row in cur.fetchall()
        ]
        message = prepare_telegram_message(format_intraday_alerts(alerts))
        delivery = send_telegram_message(message)
        event = record_delivery_event(delivery_kind='intraday_alerts', channel='telegram', delivery_status=delivery['delivery_status'], target_ref=str(message.get('chat_id') or ''), payload=message, response=delivery)
        print(json.dumps({'ok': delivery.get('ok', False), 'message': message, 'delivery': delivery, 'event': event}, ensure_ascii=False))
