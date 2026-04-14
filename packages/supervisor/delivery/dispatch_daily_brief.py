#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


import json
from packages.supervisor.common.db import connect
from packages.supervisor.delivery.events import record_delivery_event
from packages.supervisor.delivery.formatter import format_daily_brief
from packages.supervisor.delivery.telegram import prepare_telegram_message, send_telegram_message

with connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT title, summary_text, brief_json FROM daily_briefs WHERE brief_type='daily' ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            raise SystemExit('no_daily_brief')
        brief = {'title': row[0], 'summary_text': row[1], 'brief_json': row[2]}
        message = prepare_telegram_message(format_daily_brief(brief))
        delivery = send_telegram_message(message)
        event = record_delivery_event(delivery_kind='daily_brief', channel='telegram', delivery_status=delivery['delivery_status'], target_ref=str(message.get('chat_id') or ''), payload=message, response=delivery)
        print(json.dumps({'ok': delivery.get('ok', False), 'message': message, 'delivery': delivery, 'event': event}, ensure_ascii=False))
