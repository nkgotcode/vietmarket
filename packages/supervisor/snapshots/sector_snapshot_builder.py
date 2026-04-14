from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

import psycopg2.extras

from packages.supervisor.snapshots.common import to_jsonable


def build_sector_snapshots(conn, *, cycle_id: str, created_at, ticker_rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ticker_rows:
        grouped[(row.get('sector') or 'Unclassified')].append(row)

    output_rows: list[dict[str, Any]] = []
    insert_rows: list[tuple[Any, ...]] = []
    for sector, rows in sorted(grouped.items()):
        valid_ret_1d = [row['ret_1d'] for row in rows if row.get('ret_1d') is not None]
        valid_ret_5d = [row['ret_5d'] for row in rows if row.get('ret_5d') is not None]
        adv_count = sum(1 for row in rows if (row.get('ret_1d') or 0.0) > 0)
        dec_count = sum(1 for row in rows if (row.get('ret_1d') or 0.0) < 0)
        names_count = len(rows)
        breadth_pct = (adv_count / names_count) if names_count else None
        leadership = [
            {
                'ticker': row['ticker'],
                'watchlist_score': row['watchlist_score'],
                'ret_5d': row.get('ret_5d'),
                'industry_name': (row.get('snapshot_json') or {}).get('industry_name'),
            }
            for row in sorted(rows, key=lambda item: (item['watchlist_score'], item.get('ret_5d') or -999), reverse=True)[:3]
        ]
        laggards = [
            {
                'ticker': row['ticker'],
                'watchlist_score': row['watchlist_score'],
                'ret_5d': row.get('ret_5d'),
                'industry_name': (row.get('snapshot_json') or {}).get('industry_name'),
            }
            for row in sorted(rows, key=lambda item: (item['watchlist_score'], item.get('ret_5d') or 999))[:3]
        ]
        industry_counter = Counter(((row.get('snapshot_json') or {}).get('industry_name') or 'Unknown') for row in rows)
        snapshot_json = {
            'industry_mix': [
                {
                    'industry_name': industry,
                    'count': count,
                }
                for industry, count in sorted(industry_counter.items(), key=lambda item: (-item[1], item[0]))[:8]
            ],
            'liquidity_mix': {
                'high': sum(1 for row in rows if row.get('liquidity_bucket') == 'high'),
                'medium': sum(1 for row in rows if row.get('liquidity_bucket') == 'medium'),
                'low': sum(1 for row in rows if row.get('liquidity_bucket') == 'low'),
            },
            'health_mix': {
                'healthy': sum(1 for row in rows if row.get('health_status') == 'healthy'),
                'degraded': sum(1 for row in rows if row.get('health_status') == 'degraded'),
                'blocked': sum(1 for row in rows if row.get('health_status') == 'blocked'),
            },
        }
        record = {
            'cycle_id': cycle_id,
            'sector': sector,
            'names_count': names_count,
            'adv_count': adv_count,
            'dec_count': dec_count,
            'breadth_pct': breadth_pct,
            'avg_ret_1d': (sum(valid_ret_1d) / len(valid_ret_1d)) if valid_ret_1d else None,
            'avg_ret_5d': (sum(valid_ret_5d) / len(valid_ret_5d)) if valid_ret_5d else None,
            'leadership_json': leadership,
            'laggards_json': laggards,
            'snapshot_json': snapshot_json,
            'created_at': created_at,
        }
        output_rows.append(record)
        insert_rows.append((
            cycle_id,
            sector,
            names_count,
            adv_count,
            dec_count,
            record['breadth_pct'],
            record['avg_ret_1d'],
            record['avg_ret_5d'],
            json.dumps(to_jsonable(leadership), default=str),
            json.dumps(to_jsonable(laggards), default=str),
            json.dumps(to_jsonable(snapshot_json), default=str),
            created_at,
        ))

    if insert_rows:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                '''
                INSERT INTO sector_snapshots (
                  cycle_id, sector, names_count, adv_count, dec_count, breadth_pct,
                  avg_ret_1d, avg_ret_5d, leadership_json, laggards_json, snapshot_json, created_at
                ) VALUES %s
                ''',
                insert_rows,
            )

    return {
        'rows': output_rows,
        'count': len(output_rows),
    }
