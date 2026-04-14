from __future__ import annotations

import json
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def emit(event_type: str, **payload) -> None:
    body = {'event_type': event_type, 'at': utc_now_iso(), **payload}
    print(json.dumps(body, default=str, ensure_ascii=False))