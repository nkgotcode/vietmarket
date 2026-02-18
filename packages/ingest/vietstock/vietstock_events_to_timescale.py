#!/usr/bin/env python3
"""Ingest VietstockFinance events calendar into Timescale.

Source page:
  https://finance.vietstock.vn/lich-su-kien.htm?page=N

We parse table #event-content which includes:
  Mã CK, Sàn, Ngày GDKHQ, Ngày ĐKCC, Ngày thực hiện, Nội dung sự kiện, Loại Sự kiện

We store rows in `corporate_actions`.

Env:
- PG_URL (required)
- MAX_PAGES (optional, default 5)
- START_PAGE (optional, default 1)
- UNIVERSE_REGEX (optional, default '^[A-Z0-9]{3,4}$')

Notes:
- We intentionally ignore indices for ingest (VNINDEX/HNXINDEX/UPCOMINDEX) by regex.
- id is stable md5 hash of key fields.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

import psycopg2
import psycopg2.extras
import requests

BASE = "https://finance.vietstock.vn/lich-su-kien.htm"


def pg_url() -> str:
    u = os.environ.get("PG_URL")
    if not u:
        raise RuntimeError("Missing PG_URL")
    return u


def parse_ddmmyyyy(s: str) -> Optional[date]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        # Vietstock uses dd/mm/yyyy
        return datetime.strptime(s, "%d/%m/%Y").date()
    except Exception:
        return None


def md5_id(*parts: str) -> str:
    h = hashlib.md5()
    for p in parts:
        h.update((p or "").encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()


def extract_table_rows(html: str) -> List[List[str]]:
    """Return list of rows; each row is list of cell strings.

    This is a dependency-free HTML table parser tuned for Vietstock's table markup.
    """
    # Narrow to the table by id.
    m = re.search(r"<table[^>]*id=\"event-content\"[^>]*>(.*?)</table>", html, re.I | re.S)
    if not m:
        return []
    table_html = m.group(1)

    # Extract <tr> blocks
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, re.I | re.S)
    out: List[List[str]] = []
    for tr in trs:
        # skip header rows (th)
        if re.search(r"<th\b", tr, re.I):
            continue
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.I | re.S)
        if not tds:
            continue

        cells = []
        for td in tds:
            # strip tags
            txt = re.sub(r"<[^>]+>", " ", td)
            txt = re.sub(r"\s+", " ", txt).strip()
            cells.append(txt)
        out.append(cells)
    return out


@dataclass
class EventRow:
    ticker: str
    exchange: str
    ex_date: Optional[date]
    record_date: Optional[date]
    pay_date: Optional[date]
    headline: str
    event_type: str
    source_url: str

    def to_pg(self) -> dict:
        _id = md5_id(
            self.ticker,
            self.exchange,
            self.ex_date.isoformat() if self.ex_date else "",
            self.record_date.isoformat() if self.record_date else "",
            self.pay_date.isoformat() if self.pay_date else "",
            self.headline,
            self.event_type,
            self.source_url,
        )
        return {
            "id": _id,
            "ticker": self.ticker,
            "exchange": self.exchange or None,
            "ex_date": self.ex_date,
            "record_date": self.record_date,
            "pay_date": self.pay_date,
            "headline": self.headline or None,
            "event_type": self.event_type or None,
            "source": "vietstock",
            "source_url": self.source_url,
            "raw_json": json.dumps(
                {
                    "ticker": self.ticker,
                    "exchange": self.exchange,
                    "ex_date": self.ex_date.isoformat() if self.ex_date else None,
                    "record_date": self.record_date.isoformat() if self.record_date else None,
                    "pay_date": self.pay_date.isoformat() if self.pay_date else None,
                    "headline": self.headline,
                    "event_type": self.event_type,
                    "source_url": self.source_url,
                },
                ensure_ascii=False,
            ),
        }


def fetch_page(page: int) -> str:
    url = f"{BASE}?page={page}"
    r = requests.get(
        url,
        timeout=20,
        headers={
            "user-agent": "vietmarket/1.0 (+https://github.com/nkgotcode/vietmarket)",
            "accept": "text/html,application/xhtml+xml",
        },
    )
    r.raise_for_status()
    return r.text


def parse_events(html: str, source_url: str, universe_re: re.Pattern) -> List[EventRow]:
    rows = extract_table_rows(html)
    events: List[EventRow] = []

    # expected columns:
    # [0]=STT, [1]=Ma CK, [2]=San, [3]=GDKHQ, [4]=DKCC, [5]=Ngay thuc hien, [6]=Noi dung, [7]=Loai su kien
    for cells in rows:
        if len(cells) < 8:
            continue
        ticker = (cells[1] or "").strip().upper()
        if not universe_re.match(ticker):
            continue

        exchange = (cells[2] or "").strip().upper()
        ex_date = parse_ddmmyyyy(cells[3])
        record_date = parse_ddmmyyyy(cells[4])
        pay_date = parse_ddmmyyyy(cells[5])
        headline = (cells[6] or "").strip()
        event_type = (cells[7] or "").strip()

        events.append(
            EventRow(
                ticker=ticker,
                exchange=exchange,
                ex_date=ex_date,
                record_date=record_date,
                pay_date=pay_date,
                headline=headline,
                event_type=event_type,
                source_url=source_url,
            )
        )

    return events


def main() -> int:
    start_page = int(os.environ.get("START_PAGE", "1"))
    max_pages = int(os.environ.get("MAX_PAGES", "5"))
    universe_regex = os.environ.get("UNIVERSE_REGEX", r"^[A-Z0-9]{3,4}$")
    universe_re = re.compile(universe_regex)

    all_events: List[EventRow] = []
    for p in range(start_page, start_page + max_pages):
        url = f"{BASE}?page={p}"
        html = fetch_page(p)
        all_events.extend(parse_events(html, url, universe_re))

    payload = [e.to_pg() for e in all_events]

    sql = """
INSERT INTO corporate_actions (id, ticker, exchange, ex_date, record_date, pay_date, headline, event_type, source, source_url, raw_json, ingested_at)
VALUES (%(id)s, %(ticker)s, %(exchange)s, %(ex_date)s, %(record_date)s, %(pay_date)s, %(headline)s, %(event_type)s, %(source)s, %(source_url)s, %(raw_json)s::jsonb, now())
ON CONFLICT (id) DO UPDATE SET
  exchange = EXCLUDED.exchange,
  ex_date = EXCLUDED.ex_date,
  record_date = EXCLUDED.record_date,
  pay_date = EXCLUDED.pay_date,
  headline = EXCLUDED.headline,
  event_type = EXCLUDED.event_type,
  source_url = EXCLUDED.source_url,
  raw_json = EXCLUDED.raw_json,
  ingested_at = now();
""".strip()

    with psycopg2.connect(pg_url()) as pg:
        with pg.cursor() as cur:
            psycopg2.extras.execute_batch(cur, sql, payload, page_size=200)

    print(
        json.dumps(
            {
                "ok": True,
                "pages": max_pages,
                "events": len(payload),
                "sample": payload[:2],
            },
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
