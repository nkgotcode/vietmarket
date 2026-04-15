from __future__ import annotations

import json
from statistics import median
from typing import Any, Iterable

import psycopg2.extras


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, default=str, ensure_ascii=False)


def fetch_all_dicts(cur) -> list[dict[str, Any]]:
    return [dict(row) for row in cur.fetchall()]


def execute_values(cur, sql: str, rows: Iterable[tuple]) -> None:
    rows = list(rows)
    if not rows:
        return
    psycopg2.extras.execute_values(cur, sql, rows)


def safe_median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(median(values))
