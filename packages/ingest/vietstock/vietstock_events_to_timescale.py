#!/usr/bin/env python3
"""Ingest VietstockFinance event calendar into Timescale.

UI page:
  https://finance.vietstock.vn/lich-su-kien.htm?page=1

The HTML response does *not* contain the events table. The table is rendered by JS
which POSTs to:
  https://finance.vietstock.vn/data/eventstypedata

So this ingestor:
1) GETs the UI page to extract `__RequestVerificationToken`
2) POSTs to `/data/eventstypedata` to get JSON rows

We store rows in `corporate_actions`.

Env:
- PG_URL (required)
- EVENT_TYPE_ID (optional, default 1)  # tab id for "Cổ tức, thưởng và phát hành thêm"
- CHANNEL_ID (optional, default 0)     # group id; 0 = all
- PAGE_SIZE (optional, default 50)
- MAX_PAGES (optional, default 5)
- UNIVERSE_REGEX (optional, default '^[A-Z0-9]{3,4}$')

Notes:
- We intentionally ignore indices for ingest by regex.
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

UI_BASE = "https://finance.vietstock.vn/lich-su-kien.htm"
API_BASE = "https://finance.vietstock.vn/data/eventstypedata"


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


def fetch_ui_html(session: requests.Session) -> str:
    """Fetch the UI HTML used to extract the anti-forgery token.

    Important: must be fetched with the same session used for the subsequent
    POST, because Vietstock may require cookies/session state.
    """
    url = f"{UI_BASE}?page=1"
    r = session.get(
        url,
        timeout=30,
        headers={
            "user-agent": "Mozilla/5.0 (vietmarket; +https://github.com/nkgotcode/vietmarket)",
            "accept": "text/html,application/xhtml+xml",
        },
    )
    r.raise_for_status()
    return r.text


def extract_token(html: str) -> str:
    """Extract Vietstock anti-forgery token.

    Vietstock's markup is not stable and often uses unquoted attributes, e.g.:
      <input name=__RequestVerificationToken type=hidden value=...>

    So we match the <input ...> tag and accept quoted or unquoted forms.
    """

    # Prefer matching inside the input tag.
    patterns = [
        # quoted
        r"<input[^>]*\bname=['\"]?__RequestVerificationToken['\"]?[^>]*\bvalue=['\"]([^'\"]+)['\"]",
        # unquoted value
        r"<input[^>]*\bname=['\"]?__RequestVerificationToken['\"]?[^>]*\bvalue=([^\s>]+)",
    ]

    for pat in patterns:
        m = re.search(pat, html, re.I)
        if m:
            return m.group(1).strip()

    raise RuntimeError('Could not find __RequestVerificationToken in HTML')


def post_events_json(*, session: requests.Session, token: str, event_type_id: int, channel_id: int, page: int, page_size: int, from_date: str, to_date: str):
    """POST to Vietstock events endpoint and parse JSON.

    The endpoint is somewhat flaky and may return:
    - JSON with UTF-8 BOM
    - HTML (homepage) when missing required cookies/session
    - empty bodies with content-type application/json

    Set DEBUG_VIETSTOCK=1 to dump response headers + first bytes.
    """

    debug = os.environ.get('DEBUG_VIETSTOCK') == '1'

    # Mimic vst.io.post (form-encoded)
    payload = {
        'eventTypeID': str(event_type_id),
        'channelID': str(channel_id),
        'code': '',
        'catID': '',
        'fDate': from_date,
        'tDate': to_date,
        'page': str(page),
        'pageSize': str(page_size),
        'orderBy': 'Date1',
        'orderDir': 'DESC',
        '__RequestVerificationToken': token,
    }

    r = session.post(
        API_BASE,
        timeout=30,
        headers={
            'user-agent': 'Mozilla/5.0 (vietmarket; +https://github.com/nkgotcode/vietmarket)',
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'x-requested-with': 'XMLHttpRequest',
            'referer': f"{UI_BASE}?page=1",
        },
        data=payload,
    )

    if debug:
        head = r.content[:512]
        print(
            json.dumps(
                {
                    "debug": "vietstock_eventstypedata_response",
                    "status": r.status_code,
                    "url": r.url,
                    "content_type": r.headers.get("content-type", ""),
                    "content_length": r.headers.get("content-length", ""),
                    "encoding": r.encoding,
                    "cookies": {c.name: c.value for c in session.cookies},
                    "head_hex": head.hex(),
                    "head_text": head.decode("utf-8", errors="replace"),
                },
                ensure_ascii=False,
            )
        )

    r.raise_for_status()

    # Vietstock sometimes returns JSON with a UTF-8 BOM prefix.
    # requests' r.json() will fail with "Unexpected UTF-8 BOM".
    try:
        return r.json()
    except Exception:
        try:
            return json.loads(r.content.decode('utf-8-sig'))
        except Exception as e:
            snippet = (r.text or '')[:500]
            raise RuntimeError(
                f"Failed to parse events JSON: status={r.status_code} content_type={r.headers.get('content-type','')} snippet={snippet!r}"
            ) from e


def parse_events_from_json(obj, source_url: str, universe_re: re.Pattern) -> List[EventRow]:
    # API returns [rows, [[totalCount]]]
    rows = obj[0] if isinstance(obj, list) and len(obj) > 0 else []
    events: List[EventRow] = []

    for it in rows or []:
        ticker = str(it.get('Code') or '').strip().upper()
        if not universe_re.match(ticker):
            continue

        exchange = str(it.get('Exchange') or '').strip().upper()
        ex_date = it.get('GDKHQDate')
        record_date = it.get('NDKCCDate')
        pay_date = it.get('Time')
        headline = str(it.get('Note') or '').strip()
        event_type = str(it.get('Name') or '').strip()

        events.append(
            EventRow(
                ticker=ticker,
                exchange=exchange,
                ex_date=parse_ddmmyyyy(ex_date) if isinstance(ex_date, str) else None,
                record_date=parse_ddmmyyyy(record_date) if isinstance(record_date, str) else None,
                pay_date=parse_ddmmyyyy(pay_date) if isinstance(pay_date, str) else None,
                headline=headline,
                event_type=event_type,
                source_url=source_url,
            )
        )

    return events


def main() -> int:
    event_type_id = int(os.environ.get('EVENT_TYPE_ID', '1'))
    channel_id = int(os.environ.get('CHANNEL_ID', '0'))
    page_size = int(os.environ.get('PAGE_SIZE', '50'))
    max_pages = int(os.environ.get('MAX_PAGES', '5'))

    universe_regex = os.environ.get("UNIVERSE_REGEX", r"^[A-Z0-9]{3,4}$")
    universe_re = re.compile(universe_regex)

    session = requests.Session()
    html = fetch_ui_html(session)
    token = extract_token(html)

    # Vietstock expects dd/mm/yyyy
    # Default: +/- 60 days around now
    today = datetime.utcnow().date()
    from_date = os.environ.get('FROM_DATE') or (today.replace(day=1)).strftime('%d/%m/%Y')
    to_date = os.environ.get('TO_DATE') or (date(today.year + 1, today.month, 1)).strftime('%d/%m/%Y')

    all_events: List[EventRow] = []
    for page in range(1, max_pages + 1):
        source_url = f"{UI_BASE}?page=1&tab={event_type_id}&group={channel_id}"
        obj = post_events_json(
            session=session,
            token=token,
            event_type_id=event_type_id,
            channel_id=channel_id,
            page=page,
            page_size=page_size,
            from_date=from_date,
            to_date=to_date,
        )
        all_events.extend(parse_events_from_json(obj, source_url, universe_re))

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
