from __future__ import annotations

import json

from packages.supervisor.common.db import connect
from packages.supervisor.common.ids import new_run_id
from packages.supervisor.common.time import utc_now


def record_delivery_event(*, delivery_kind: str, channel: str, delivery_status: str, target_ref: str | None, payload: dict, response: dict) -> dict:
    delivery_id = f'delivery_{new_run_id()}'
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO delivery_events (
                  delivery_id, delivery_kind, channel, delivery_status, target_ref,
                  payload_json, response_json, created_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ''',
                (
                    delivery_id,
                    delivery_kind,
                    channel,
                    delivery_status,
                    target_ref,
                    json.dumps(payload, default=str),
                    json.dumps(response, default=str),
                    utc_now(),
                ),
            )
    return {'delivery_id': delivery_id, 'delivery_status': delivery_status}
