#!/usr/bin/env python3
"""Vietstock RSS ingest + fetch → TimescaleDB.

Option 2 (strict): No sqlite archive.

What it does:
- Reads RSS feed(s)
- Upserts articles metadata into Timescale `articles`
- Fetches article HTML and extracts rough text (best-effort)
- Stores full text into Timescale `articles.text`

Env:
- PG_URL (required)

This is a minimal v1. We'll harden parsing and add seed/crawl_state later.
"""

from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import requests
import psycopg2
import psycopg2.extras


def pg_url() -> str:
    u = os.environ.get('PG_URL')
    if not u:
        raise RuntimeError('Missing PG_URL')
    return u


def db():
    return psycopg2.connect(pg_url())


@dataclass
class RssItem:
    url: str
    title: str
    published_at: datetime | None


def parse_rss(xml: str) -> list[RssItem]:
    # Minimal RSS parser without extra deps.
    # Good enough for Vietstock feeds; we can swap to feedparser later.
    def find_all(tag: str) -> list[str]:
        return re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", xml, flags=re.S | re.I)

    items = re.findall(r"<item>(.*?)</item>", xml, flags=re.S | re.I)
    out: list[RssItem] = []
    for block in items:
        title = re.findall(r"<title[^>]*>(.*?)</title>", block, flags=re.S | re.I)
        link = re.findall(r"<link[^>]*>(.*?)</link>", block, flags=re.S | re.I)
        pub = re.findall(r"<pubDate[^>]*>(.*?)</pubDate>", block, flags=re.S | re.I)

        t = (title[0] if title else '').strip()
        u = (link[0] if link else '').strip()
        p = (pub[0] if pub else '').strip()

        dt = None
        if p:
            # Example: Tue, 16 Feb 2026 00:00:00 +0700
            try:
                dt = datetime.strptime(p, "%a, %d %b %Y %H:%M:%S %z")
            except Exception:
                dt = None

        if u:
            out.append(RssItem(url=u, title=t or u, published_at=dt))
    return out


def strip_html(html: str) -> str:
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    txt = re.sub(r"<[^>]+>", " ", html)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def upsert_article_meta(*, url: str, title: str, published_at: datetime | None, feed_url: str):
    sql = """
    INSERT INTO articles (url, source, title, published_at, feed_url, fetch_status)
    VALUES (%(url)s, 'rss', %(title)s, %(published_at)s, %(feed_url)s, 'pending')
    ON CONFLICT (url) DO UPDATE SET
      title = EXCLUDED.title,
      published_at = COALESCE(EXCLUDED.published_at, articles.published_at),
      feed_url = COALESCE(EXCLUDED.feed_url, articles.feed_url),
      ingested_at = now();
    """.strip()

    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {
                'url': url,
                'title': title,
                'published_at': published_at,
                'feed_url': feed_url,
            })


def mark_fetched(*, url: str, text: str):
    sql = """
    UPDATE articles
    SET fetch_status='fetched', fetched_at=now(), text=%(text)s
    WHERE url=%(url)s;
    """.strip()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {'url': url, 'text': text})


def mark_failed(*, url: str, err: str):
    sql = """
    UPDATE articles
    SET fetch_status='failed', fetched_at=now(), fetch_error=%(err)s
    WHERE url=%(url)s;
    """.strip()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {'url': url, 'err': err[:800]})


def main(argv: list[str]) -> int:
    feeds = os.environ.get('VIETSTOCK_RSS_FEEDS', '').strip().split()
    if not feeds:
        raise RuntimeError('Missing VIETSTOCK_RSS_FEEDS (space-separated URLs)')

    limit = int(os.environ.get('LIMIT', '30'))
    sleep_s = float(os.environ.get('SLEEP', '0.2'))

    sess = requests.Session()
    discovered = 0
    fetched = 0
    failed = 0

    for feed_url in feeds:
        r = sess.get(feed_url, timeout=30)
        r.raise_for_status()
        items = parse_rss(r.text)

        for it in items[:limit]:
            upsert_article_meta(url=it.url, title=it.title, published_at=it.published_at, feed_url=feed_url)
            discovered += 1

            try:
                rr = sess.get(it.url, timeout=45)
                rr.raise_for_status()
                text = strip_html(rr.text)
                # keep it bounded for now; we can store full HTML later if needed
                text = text[:200_000]
                mark_fetched(url=it.url, text=text)
                fetched += 1
            except Exception as e:
                mark_failed(url=it.url, err=str(e))
                failed += 1

            time.sleep(sleep_s)

    print({
        'ok': True,
        'feeds': len(feeds),
        'discovered': discovered,
        'fetched': fetched,
        'failed': failed,
    })
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
