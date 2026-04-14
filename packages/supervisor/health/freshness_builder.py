from __future__ import annotations

import json
from dataclasses import dataclass

from packages.supervisor.common.db import connect, dict_cursor
from packages.supervisor.common.enums import FRESHNESS_FRESH, FRESHNESS_LAGGING, FRESHNESS_STALE, FRESHNESS_UNKNOWN
from packages.supervisor.common.ids import new_snapshot_id
from packages.supervisor.common.time import freshness_seconds, utc_now


@dataclass(frozen=True)
class DatasetRule:
    dataset_name: str
    event_sql: str
    lagging_after_s: int
    stale_after_s: int
    tf: str | None = None


DATASET_RULES = [
    DatasetRule('candles', "SELECT to_timestamp(max(ts)/1000.0), max(ingested_at) FROM candles WHERE tf = '15m'", 20 * 60, 60 * 60, '15m'),
    DatasetRule('candles', "SELECT to_timestamp(max(ts)/1000.0), max(ingested_at) FROM candles WHERE tf = '1h'", 2 * 60 * 60, 6 * 60 * 60, '1h'),
    DatasetRule('candles', "SELECT to_timestamp(max(ts)/1000.0), max(ingested_at) FROM candles WHERE tf = '1d'", 36 * 60 * 60, 72 * 60 * 60, '1d'),
    DatasetRule('symbols', "SELECT to_timestamp(max(updated_at)/1000.0), to_timestamp(max(updated_at)/1000.0) FROM symbols", 24 * 60 * 60, 72 * 60 * 60),
    DatasetRule('fi_latest', "SELECT max(period_date)::timestamp, max(ingested_at) FROM fi_latest", 36 * 60 * 60, 7 * 24 * 60 * 60),
    DatasetRule('corporate_actions', "SELECT max(coalesce(pay_date, record_date, ex_date))::timestamp, max(ingested_at) FROM corporate_actions", 24 * 60 * 60, 7 * 24 * 60 * 60),
    DatasetRule('articles', "SELECT max(published_at), max(fetched_at) FROM articles", 30 * 60, 2 * 60 * 60),
    DatasetRule('article_symbols', "SELECT max(a.published_at), max(a.fetched_at) FROM article_symbols s JOIN articles a ON a.url = s.article_url", 2 * 60 * 60, 6 * 60 * 60),
    DatasetRule('financials', "SELECT max(period_date)::timestamp, max(updated_at) FROM financials", 24 * 60 * 60, 7 * 24 * 60 * 60),
    DatasetRule('fundamentals', "SELECT max(period_date)::timestamp, max(updated_at) FROM fundamentals", 24 * 60 * 60, 7 * 24 * 60 * 60),
    DatasetRule('technical_indicators', "SELECT to_timestamp(max(asof_ts)/1000.0), max(updated_at) FROM technical_indicators", 2 * 60 * 60, 8 * 60 * 60),
    DatasetRule('indicators', "SELECT to_timestamp(max(asof_ts)/1000.0), max(updated_at) FROM indicators", 2 * 60 * 60, 8 * 60 * 60),
    DatasetRule('market_stats', "SELECT to_timestamp(max(asof_ts)/1000.0), max(updated_at) FROM market_stats", 60 * 60, 6 * 60 * 60),
]


def classify_freshness(seconds_old: int | None, *, lagging_after_s: int, stale_after_s: int) -> str:
    if seconds_old is None:
        return FRESHNESS_UNKNOWN
    if seconds_old >= stale_after_s:
        return FRESHNESS_STALE
    if seconds_old >= lagging_after_s:
        return FRESHNESS_LAGGING
    return FRESHNESS_FRESH


def build_freshness() -> dict:
    now = utc_now()
    rows_out: list[dict] = []
    with connect() as conn:
        with dict_cursor(conn) as cur:
            for rule in DATASET_RULES:
                cur.execute(rule.event_sql)
                row = cur.fetchone()
                values = list(row.values()) if row else [None, None]
                if len(values) < 2:
                    values = [values[0] if values else None, None]
                max_event_ts = values[0]
                max_ingested_at = values[1]
                latest = max_ingested_at or max_event_ts
                secs = freshness_seconds(latest, now)
                status = classify_freshness(secs, lagging_after_s=rule.lagging_after_s, stale_after_s=rule.stale_after_s)
                freshness_id = new_snapshot_id()
                ctx = {'lagging_after_s': rule.lagging_after_s, 'stale_after_s': rule.stale_after_s}
                cur.execute(
                    '''
                    INSERT INTO dataset_freshness (
                      freshness_id, dataset_name, ticker, tf, max_event_ts, max_ingested_at,
                      freshness_seconds, freshness_status, freshness_context_json, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (dataset_name, ticker, tf) DO UPDATE SET
                      freshness_id = EXCLUDED.freshness_id,
                      max_event_ts = EXCLUDED.max_event_ts,
                      max_ingested_at = EXCLUDED.max_ingested_at,
                      freshness_seconds = EXCLUDED.freshness_seconds,
                      freshness_status = EXCLUDED.freshness_status,
                      freshness_context_json = EXCLUDED.freshness_context_json,
                      updated_at = EXCLUDED.updated_at
                    ''',
                    (freshness_id, rule.dataset_name, '', rule.tf or '', max_event_ts, max_ingested_at, secs, status, json.dumps(ctx), now)
                )
                rows_out.append({
                    'dataset_name': rule.dataset_name,
                    'tf': rule.tf,
                    'max_event_ts': max_event_ts.isoformat() if max_event_ts else None,
                    'max_ingested_at': max_ingested_at.isoformat() if max_ingested_at else None,
                    'freshness_seconds': secs,
                    'freshness_status': status,
                })
    return {'ok': True, 'at': now.isoformat(timespec='seconds'), 'rows': rows_out, 'count': len(rows_out)}