#!/usr/bin/env python3
"""Fetch pending Vietstock articles and store full text in Timescale.

Env:
- PG_URL (required)

Knobs:
- LIMIT (default 200)
- RATE (req/sec, default 3)

Behavior:
- Claims a batch with SELECT ... FOR UPDATE SKIP LOCKED
- Marks them running, fetches HTML, extracts Vietstock main text, stores into articles.text
"""

from __future__ import annotations

import html as _html
import os
import re
import time
import urllib.request

import psycopg2

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def pg_url() -> str:
    u = os.environ.get('PG_URL')
    if not u:
        raise RuntimeError('Missing PG_URL')
    return u


def http_get(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def strip_tags(html_str: str) -> str:
    html_str = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html_str)
    html_str = re.sub(r"(?is)<br\s*/?>", "\n", html_str)
    html_str = re.sub(r"(?is)</p\s*>", "\n", html_str)
    text = re.sub(r"(?is)<[^>]+>", " ", html_str)
    text = _html.unescape(text)
    text = re.sub(r"[\t\r ]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_main_text(html_bytes: bytes) -> str:
    s = html_bytes.decode('utf-8', errors='ignore')

    paras = []
    for cls in ("pTitle", "pHead", "pBody"):
        for m in re.finditer(rf"(?is)<p[^>]*class=\"{cls}\"[^>]*>(.*?)</p>", s):
            t = strip_tags(m.group(1))
            if t:
                paras.append(t)

    cleaned = []
    for p in paras:
        if not cleaned or cleaned[-1] != p:
            cleaned.append(p)

    if len(" ".join(cleaned).split()) >= 80:
        return "\n\n".join(cleaned).strip()

    return strip_tags(s)


def main() -> int:
    limit = int(os.environ.get('LIMIT', '200'))
    rate = float(os.environ.get('RATE', '3'))
    sleep_s = 1.0 / max(rate, 0.1)

    processed = 0

    with psycopg2.connect(pg_url()) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT url
                FROM articles
                WHERE fetch_status='pending'
                ORDER BY discovered_at ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED
                """,
                (limit,),
            )
            urls = [r[0] for r in cur.fetchall()]
            if not urls:
                print({"ok": True, "processed": 0, "reason": "no pending"})
                conn.commit()
                return 0

            cur.execute(
                "UPDATE articles SET fetch_status='running', fetched_at=now() WHERE url = ANY(%s)",
                (urls,),
            )
            conn.commit()

    for url in urls:
        try:
            raw = http_get(url)
            text = extract_main_text(raw)
            # cap for safety
            text = text[:500_000]
            wc = len([w for w in text.split() if w.strip()])

            with psycopg2.connect(pg_url()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE articles
                        SET fetch_status='fetched',
                            fetched_at=now(),
                            text=%s,
                            word_count=%s,
                            fetch_error=NULL
                        WHERE url=%s
                        """,
                        (text, wc, url),
                    )
            processed += 1
        except Exception as e:
            with psycopg2.connect(pg_url()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE articles SET fetch_status='failed', fetched_at=now(), fetch_error=%s WHERE url=%s",
                        (str(e)[:800], url),
                    )
        time.sleep(sleep_s)

    print({"ok": True, "processed": processed})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
