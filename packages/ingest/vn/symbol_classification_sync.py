#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36'
)
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
FIREANT_URL = 'https://fireant.vn/ma-chung-khoan/{ticker}'
SSL_CONTEXT = ssl._create_unverified_context()

SECTOR_PREFIX_MAP = {
    '10': 'Technology',
    '15': 'Telecommunications',
    '20': 'Health Care',
    '30': 'Financials',
    '35': 'Real Estate',
    '40': 'Consumer Discretionary',
    '45': 'Consumer Staples',
    '50': 'Industrials',
    '55': 'Basic Materials',
    '60': 'Energy',
    '65': 'Utilities',
}


@dataclass(frozen=True)
class ClassificationRow:
    ticker: str
    exchange: str | None
    name: str | None
    icb_code: str | None
    industry_code: str | None
    sector_name: str | None
    industry_name: str | None
    classification_source: str


def pg_url() -> str:
    value = os.environ.get('PG_URL') or os.environ.get('DATABASE_URL')
    if not value:
        raise RuntimeError('Missing PG_URL or DATABASE_URL')
    return value


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sector_name_from_icb(icb_code: str | None) -> str | None:
    if not icb_code:
        return None
    return SECTOR_PREFIX_MAP.get(str(icb_code)[:2])


def _extract_blob(next_data: dict, ticker: str) -> tuple[dict, list[dict], list[dict]]:
    state = next_data['props']['pageProps']['initialState']['symbols']
    symbol_blob = state['symbols'][ticker]['data']
    financial_q = state.get('financialData', {}).get('Q', {}).get(ticker, [])
    financial_y = state.get('financialData', {}).get('Y', {}).get(ticker, [])
    return symbol_blob, financial_q, financial_y


def _industry_name_from_financials(financial_rows: list[dict]) -> str | None:
    for row in financial_rows:
        if isinstance(row, dict):
            if row.get('icbName'):
                return str(row['icbName']).strip() or None
            values = row.get('financialValues') or {}
            if isinstance(values, dict) and values.get('ICBName'):
                return str(values['ICBName']).strip() or None
    return None


def fetch_classification(ticker: str) -> ClassificationRow:
    req = urllib.request.Request(FIREANT_URL.format(ticker=ticker), headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=45) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
    match = NEXT_DATA_RE.search(html)
    if not match:
        raise RuntimeError(f'__NEXT_DATA__ missing for {ticker}')
    next_data = json.loads(match.group(1))
    symbol_blob, financial_q, financial_y = _extract_blob(next_data, ticker)
    industry_name = _industry_name_from_financials(financial_q) or _industry_name_from_financials(financial_y)
    icb_code = symbol_blob.get('icbCode')
    row = ClassificationRow(
        ticker=ticker,
        exchange=symbol_blob.get('exchange'),
        name=symbol_blob.get('name'),
        icb_code=str(icb_code).strip() if icb_code else None,
        industry_code=str(symbol_blob.get('industryCode')).strip() if symbol_blob.get('industryCode') else None,
        sector_name=_sector_name_from_icb(str(icb_code).strip() if icb_code else None),
        industry_name=industry_name,
        classification_source='fireant',
    )
    return row


def load_tickers(*, only_missing: bool) -> list[str]:
    with psycopg2.connect(pg_url()) as conn:
        with conn.cursor() as cur:
            if only_missing:
                cur.execute(
                    '''
                    SELECT ticker
                    FROM symbols
                    WHERE (active IS TRUE OR active IS NULL)
                      AND (sector_name IS NULL OR industry_name IS NULL)
                    ORDER BY ticker
                    '''
                )
            else:
                cur.execute(
                    '''
                    SELECT ticker
                    FROM symbols
                    WHERE (active IS TRUE OR active IS NULL)
                    ORDER BY ticker
                    '''
                )
            return [r[0] for r in cur.fetchall()]


def _payload(rows: list[ClassificationRow]) -> list[dict]:
    now = utc_now()
    return [
        {
            'ticker': row.ticker,
            'exchange': row.exchange,
            'name': row.name,
            'icb_code': row.icb_code,
            'industry_code': row.industry_code,
            'sector_name': row.sector_name,
            'industry_name': row.industry_name,
            'classification_source': row.classification_source,
            'classification_updated_at': now,
        }
        for row in rows
    ]


def upsert_rows(rows: list[ClassificationRow], *, page_size: int = 25) -> int:
    if not rows:
        return 0
    payload = _payload(rows)
    sql = '''
        INSERT INTO symbols (
          ticker, name, exchange, icb_code, industry_code, sector_name, industry_name,
          classification_source, classification_updated_at
        ) VALUES (
          %(ticker)s, %(name)s, %(exchange)s, %(icb_code)s, %(industry_code)s,
          %(sector_name)s, %(industry_name)s, %(classification_source)s, %(classification_updated_at)s
        )
        ON CONFLICT (ticker) DO UPDATE SET
          name = COALESCE(EXCLUDED.name, symbols.name),
          exchange = COALESCE(EXCLUDED.exchange, symbols.exchange),
          icb_code = COALESCE(EXCLUDED.icb_code, symbols.icb_code),
          industry_code = COALESCE(EXCLUDED.industry_code, symbols.industry_code),
          sector_name = COALESCE(EXCLUDED.sector_name, symbols.sector_name),
          industry_name = COALESCE(EXCLUDED.industry_name, symbols.industry_name),
          classification_source = COALESCE(EXCLUDED.classification_source, symbols.classification_source),
          classification_updated_at = EXCLUDED.classification_updated_at
    '''
    written = 0
    for i in range(0, len(payload), page_size):
        chunk = payload[i:i + page_size]
        with psycopg2.connect(pg_url()) as conn:
            with conn.cursor() as cur:
                psycopg2.extras.execute_batch(cur, sql, chunk, page_size=page_size)
            conn.commit()
        written += len(chunk)
    return written


def get_counts() -> tuple[int, int]:
    with psycopg2.connect(pg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT count(*) FILTER (WHERE sector_name IS NOT NULL),
                       count(*) FILTER (WHERE industry_name IS NOT NULL)
                FROM symbols
                WHERE active IS TRUE OR active IS NULL
                '''
            )
            return cur.fetchone()


def main() -> int:
    workers = int(os.environ.get('CLASSIFICATION_WORKERS', '8'))
    limit = int(os.environ.get('CLASSIFICATION_LIMIT', '0'))
    only_missing = os.environ.get('ONLY_MISSING', '1') != '0'
    sleep_s = float(os.environ.get('CLASSIFICATION_SLEEP', '0.02'))

    tickers = load_tickers(only_missing=only_missing)
    if limit > 0:
        tickers = tickers[:limit]

    ok_rows: list[ClassificationRow] = []
    errors: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futures = {ex.submit(fetch_classification, ticker): ticker for ticker in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                row = future.result()
                ok_rows.append(row)
            except Exception as exc:
                errors.append({'ticker': ticker, 'error': str(exc)[:400]})
            time.sleep(sleep_s)

    updated = upsert_rows(ok_rows, page_size=25)
    sector_count, industry_count = get_counts()

    print(json.dumps({
        'ok': True,
        'requested': len(tickers),
        'updated': updated,
        'errors': len(errors),
        'sector_name_count': sector_count,
        'industry_name_count': industry_count,
        'sample_errors': errors[:10],
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
