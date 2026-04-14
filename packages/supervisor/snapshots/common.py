from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from packages.supervisor.common.db import dict_cursor

VN_UNIVERSE_WHERE = "(exchange IN ('HOSE','HNX','UPCOM') OR exchange IS NULL) AND (active IS TRUE OR active IS NULL)"


@dataclass(frozen=True)
class HealthContext:
    snapshot_id: str | None
    overall_status: str
    freshness_status: str
    issue_count: int
    blocking_issue_count: int
    issues: list[dict[str, Any]]


@dataclass(frozen=True)
class MarketContext:
    health: HealthContext
    freshness: dict[str, dict[str, Any]]
    market_stats: dict[str, dict[str, Any]]


def as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return (current / previous) - 1.0


def ratio_gap(current: float | None, baseline: float | None) -> float | None:
    if current is None or baseline in (None, 0):
        return None
    return (current / baseline) - 1.0


def liquidity_bucket(turnover_last: float | None) -> str:
    if turnover_last is None:
        return 'unknown'
    if turnover_last >= 100_000_000_000:
        return 'high'
    if turnover_last >= 20_000_000_000:
        return 'medium'
    return 'low'


def iso_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    return value


def get_latest_health_context(conn) -> HealthContext:
    with dict_cursor(conn) as cur:
        cur.execute(
            '''
            SELECT snapshot_id, overall_status, freshness_status, created_at, notes_json
            FROM system_health_snapshots
            ORDER BY created_at DESC
            LIMIT 1
            '''
        )
        snapshot = cur.fetchone()
        if not snapshot:
            return HealthContext(
                snapshot_id=None,
                overall_status='unknown',
                freshness_status='unknown',
                issue_count=0,
                blocking_issue_count=0,
                issues=[],
            )
        cur.execute(
            '''
            SELECT issue_id, severity, scope_type, scope_key, issue_code, issue_message, blocking, created_at
            FROM system_health_issues
            WHERE snapshot_id = %s
            ORDER BY blocking DESC, severity DESC, created_at DESC
            ''',
            (snapshot['snapshot_id'],),
        )
        issues = [dict(row) for row in cur.fetchall()]
        return HealthContext(
            snapshot_id=snapshot['snapshot_id'],
            overall_status=snapshot['overall_status'] or 'unknown',
            freshness_status=snapshot['freshness_status'] or 'unknown',
            issue_count=len(issues),
            blocking_issue_count=sum(1 for issue in issues if issue.get('blocking')),
            issues=issues,
        )


def get_freshness_map(conn) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with dict_cursor(conn) as cur:
        cur.execute(
            '''
            SELECT dataset_name, ticker, tf, freshness_status, freshness_seconds, max_event_ts, max_ingested_at, updated_at
            FROM dataset_freshness
            ORDER BY dataset_name ASC, tf ASC NULLS FIRST
            '''
        )
        for row in cur.fetchall():
            key = f"{row['dataset_name']}:{row['tf'] or 'all'}"
            out[key] = dict(row)
    return out


def get_market_stats_map(conn) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with dict_cursor(conn) as cur:
        cur.execute(
            '''
            SELECT metric, value_numeric, value_text, asof_ts, updated_at
            FROM market_stats
            ORDER BY metric ASC
            '''
        )
        for row in cur.fetchall():
            out[row['metric']] = dict(row)
    return out


def get_market_context(conn) -> MarketContext:
    return MarketContext(
        health=get_latest_health_context(conn),
        freshness=get_freshness_map(conn),
        market_stats=get_market_stats_map(conn),
    )
