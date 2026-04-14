from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import psycopg2.extras

from packages.supervisor.snapshots.common import (
    MarketContext,
    VN_UNIVERSE_WHERE,
    as_float,
    as_int,
    liquidity_bucket,
    pct_change,
    ratio_gap,
    to_jsonable,
)

BASE_SQL = f'''
WITH ranked_daily AS (
  SELECT c.ticker,
         c.ts,
         c.c,
         c.v,
         row_number() OVER (PARTITION BY c.ticker ORDER BY c.ts DESC) AS rn
  FROM candles c
  WHERE c.tf = '1d'
),
daily_pivot AS (
  SELECT ticker,
         max(CASE WHEN rn = 1 THEN ts END) AS ts_last,
         max(CASE WHEN rn = 1 THEN c END) AS price_last,
         max(CASE WHEN rn = 1 THEN v END) AS volume_last,
         max(CASE WHEN rn = 2 THEN c END) AS prev_1d,
         max(CASE WHEN rn = 6 THEN c END) AS prev_5d,
         max(CASE WHEN rn = 21 THEN c END) AS prev_20d
  FROM ranked_daily
  WHERE rn <= 21
  GROUP BY ticker
),
returns_window AS (
  SELECT ticker,
         stddev_samp(ret) AS volatility_20d
  FROM (
    SELECT ticker,
           (c / NULLIF(lag(c) OVER (PARTITION BY ticker ORDER BY ts), 0)) - 1.0 AS ret,
           row_number() OVER (PARTITION BY ticker ORDER BY ts DESC) AS rn
    FROM candles
    WHERE tf = '1d'
  ) s
  WHERE rn <= 20
    AND ret IS NOT NULL
  GROUP BY ticker
),
article_counts AS (
  SELECT s.ticker,
         count(*)::int AS article_count_24h
  FROM article_symbols s
  JOIN articles a ON a.url = s.article_url
  WHERE a.published_at >= (now() - interval '24 hours')
  GROUP BY s.ticker
),
corporate_actions_recent AS (
  SELECT ticker,
         count(*)::int AS corporate_action_count
  FROM corporate_actions
  WHERE coalesce(ex_date, record_date, pay_date) >= (current_date - interval '14 days')
  GROUP BY ticker
),
financial_recency AS (
  SELECT ticker,
         max(period_date) AS financial_period_date
  FROM fundamentals
  GROUP BY ticker
)
SELECT s.ticker,
       s.name,
       s.exchange,
       s.sector_name,
       s.industry_name,
       s.icb_code,
       s.industry_code,
       p.ts_last,
       p.price_last,
       p.volume_last,
       p.prev_1d,
       p.prev_5d,
       p.prev_20d,
       ti.sma20,
       ti.sma50,
       ti.ema20,
       v.volatility_20d,
       ac.article_count_24h,
       ca.corporate_action_count,
       fr.financial_period_date
FROM symbols s
LEFT JOIN daily_pivot p ON p.ticker = s.ticker
LEFT JOIN technical_indicators ti ON ti.ticker = s.ticker AND ti.tf = '1d'
LEFT JOIN returns_window v ON v.ticker = s.ticker
LEFT JOIN article_counts ac ON ac.ticker = s.ticker
LEFT JOIN corporate_actions_recent ca ON ca.ticker = s.ticker
LEFT JOIN financial_recency fr ON fr.ticker = s.ticker
WHERE {VN_UNIVERSE_WHERE}
ORDER BY s.ticker ASC
'''


def _sector_for_row(row: dict[str, Any]) -> str | None:
    sector = row.get('sector_name')
    if sector:
        return str(sector).strip() or None
    return None


def _trend_state(price_last: float | None, sma20_gap: float | None, sma50_gap: float | None) -> str:
    if price_last is None:
        return 'unknown'
    if (sma20_gap or -999) > 0 and (sma50_gap or -999) > 0:
        return 'bullish'
    if (sma20_gap or 999) < 0 and (sma50_gap or 999) < 0:
        return 'bearish'
    return 'mixed'


def _momentum_state(ret_1d: float | None, ret_5d: float | None, ret_20d: float | None) -> str:
    r1 = ret_1d or 0.0
    r5 = ret_5d or 0.0
    r20 = ret_20d or 0.0
    if r5 >= 0.04 and r20 >= 0:
        return 'strong'
    if r5 <= -0.04 and r20 <= 0:
        return 'weak'
    if r1 >= 0.02:
        return 'improving'
    if r1 <= -0.02:
        return 'slipping'
    return 'neutral'


def _financial_recency_days(value: date | datetime | None, anchor: datetime) -> int | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return max(0, (anchor.date() - value.date()).days)
    return max(0, (anchor.date() - value).days)


def _health_status(context: MarketContext) -> str:
    health = context.health.overall_status
    frontier = (context.market_stats.get('candles_frontier_status') or {}).get('value_text')
    if health == 'blocked' or frontier == 'pipeline_stalled':
        return 'blocked'
    if health == 'degraded' or frontier == 'market_closed_or_source_limited':
        return 'degraded'
    if health == 'healthy' and frontier == 'fresh':
        return 'healthy'
    return health or 'unknown'


def _watchlist_score(*, ret_1d: float | None, ret_5d: float | None, ret_20d: float | None, sma20_gap: float | None,
                     ema20_gap: float | None, article_count_24h: int, corporate_action_flag: bool,
                     liquidity: str, health_status: str) -> float:
    score = 0.0
    score += (ret_1d or 0.0) * 100.0 * 0.18
    score += (ret_5d or 0.0) * 100.0 * 0.30
    score += (ret_20d or 0.0) * 100.0 * 0.20
    score += (sma20_gap or 0.0) * 100.0 * 0.14
    score += (ema20_gap or 0.0) * 100.0 * 0.08
    score += min(article_count_24h, 10) * 0.6
    if corporate_action_flag:
        score -= 1.0
    if liquidity == 'high':
        score += 1.5
    elif liquidity == 'low':
        score -= 1.0
    if health_status == 'blocked':
        score -= 3.0
    elif health_status == 'degraded':
        score -= 1.0
    return round(score, 4)


def build_ticker_snapshots(conn, *, cycle_id: str, created_at: datetime, context: MarketContext) -> dict[str, Any]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(BASE_SQL)
        rows = [dict(row) for row in cur.fetchall()]

    health_status = _health_status(context)
    output_rows: list[dict[str, Any]] = []
    insert_rows: list[tuple[Any, ...]] = []
    for row in rows:
        price_last = as_float(row.get('price_last'))
        if price_last is None:
            continue
        volume_last = as_float(row.get('volume_last'))
        turnover_last = (price_last * volume_last) if volume_last is not None else None
        ret_1d = pct_change(price_last, as_float(row.get('prev_1d')))
        ret_5d = pct_change(price_last, as_float(row.get('prev_5d')))
        ret_20d = pct_change(price_last, as_float(row.get('prev_20d')))
        sma20_gap = ratio_gap(price_last, as_float(row.get('sma20')))
        sma50_gap = ratio_gap(price_last, as_float(row.get('sma50')))
        ema20_gap = ratio_gap(price_last, as_float(row.get('ema20')))
        article_count_24h = as_int(row.get('article_count_24h')) or 0
        corporate_action_flag = (as_int(row.get('corporate_action_count')) or 0) > 0
        financial_days = _financial_recency_days(row.get('financial_period_date'), created_at)
        liquidity = liquidity_bucket(turnover_last)
        trend_state = _trend_state(price_last, sma20_gap, sma50_gap)
        momentum_state = _momentum_state(ret_1d, ret_5d, ret_20d)
        sector = _sector_for_row(row)
        industry = row.get('industry_name') or None
        snapshot_json = {
            'name': row.get('name'),
            'ts_last': row.get('ts_last'),
            'financial_period_date': row.get('financial_period_date'),
            'industry_name': industry,
            'industry_code': row.get('industry_code'),
            'icb_code': row.get('icb_code'),
            'classification_source': 'symbols',
            'health_context': {
                'overall_status': context.health.overall_status,
                'freshness_status': context.health.freshness_status,
                'blocking_issue_count': context.health.blocking_issue_count,
            },
            'market_frontier': {
                'status': (context.market_stats.get('candles_frontier_status') or {}).get('value_text'),
                'lag_ms': (context.market_stats.get('candles_frontier_lag_ms') or {}).get('value_numeric'),
            },
        }
        score = _watchlist_score(
            ret_1d=ret_1d,
            ret_5d=ret_5d,
            ret_20d=ret_20d,
            sma20_gap=sma20_gap,
            ema20_gap=ema20_gap,
            article_count_24h=article_count_24h,
            corporate_action_flag=corporate_action_flag,
            liquidity=liquidity,
            health_status=health_status,
        )
        record = {
            'cycle_id': cycle_id,
            'ticker': row['ticker'],
            'exchange': row.get('exchange'),
            'sector': sector or 'Unclassified',
            'price_last': price_last,
            'volume_last': volume_last,
            'turnover_last': turnover_last,
            'ret_1d': ret_1d,
            'ret_5d': ret_5d,
            'ret_20d': ret_20d,
            'sma20_gap': sma20_gap,
            'sma50_gap': sma50_gap,
            'ema20_gap': ema20_gap,
            'volatility_20d': as_float(row.get('volatility_20d')),
            'article_count_24h': article_count_24h,
            'corporate_action_flag': corporate_action_flag,
            'financial_recency_days': financial_days,
            'liquidity_bucket': liquidity,
            'trend_state': trend_state,
            'momentum_state': momentum_state,
            'watchlist_score': score,
            'health_status': health_status,
            'snapshot_json': to_jsonable(snapshot_json),
            'created_at': created_at,
        }
        output_rows.append(record)
        insert_rows.append((
            cycle_id,
            row['ticker'],
            row.get('exchange'),
            sector or 'Unclassified',
            price_last,
            volume_last,
            turnover_last,
            ret_1d,
            ret_5d,
            ret_20d,
            sma20_gap,
            sma50_gap,
            ema20_gap,
            as_float(row.get('volatility_20d')),
            article_count_24h,
            corporate_action_flag,
            financial_days,
            liquidity,
            trend_state,
            momentum_state,
            score,
            health_status,
            json.dumps(to_jsonable(snapshot_json), default=str),
            created_at,
        ))

    if insert_rows:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                '''
                INSERT INTO ticker_snapshots (
                  cycle_id, ticker, exchange, sector, price_last, volume_last, turnover_last,
                  ret_1d, ret_5d, ret_20d, sma20_gap, sma50_gap, ema20_gap, volatility_20d,
                  article_count_24h, corporate_action_flag, financial_recency_days,
                  liquidity_bucket, trend_state, momentum_state, watchlist_score,
                  health_status, snapshot_json, created_at
                ) VALUES %s
                ''',
                insert_rows,
            )

    ranked = sorted(output_rows, key=lambda item: (item['watchlist_score'], item['ret_5d'] or -999), reverse=True)
    return {
        'rows': output_rows,
        'count': len(output_rows),
        'watchlist_preview': [
            {
                'ticker': row['ticker'],
                'sector': row['sector'],
                'watchlist_score': row['watchlist_score'],
                'trend_state': row['trend_state'],
                'momentum_state': row['momentum_state'],
            }
            for row in ranked[:10]
        ],
    }
