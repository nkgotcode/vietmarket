#!/usr/bin/env python3
"""Vietstock discover (RSS + backfill crawl) → Timescale.

This ports the legacy sqlite workflow into Timescale-native tables:
- control_kv
- feeds
- seeds
- crawl_state
- articles

Env:
- PG_URL (required)

Budget knobs:
- RSS_LIMIT (default 500)
- BACKFILL_BUDGET_PAGES (default 200)
- RATE (requests/sec, default 1)
- NO_NEW_PAGES_STOP (default 3)

Notes:
- Uses Vietstock's ChannelContentPage endpoint for listing pages.
- Inserts discovered article URLs as articles(fetch_status='pending').
"""

from __future__ import annotations

import os
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime

import psycopg2

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

ARTICLE_URL_RE = re.compile(r"https?://(?:www\.)?(?:vietstock\.vn|fili\.vn)/\d{4}/\d{2}/[^\s\"']+?\.htm", re.I)
REL_URL_RE = re.compile(r"/\d{4}/\d{2}/[^\s\"']+?\.htm", re.I)


def pg_url() -> str:
    u = os.environ.get('PG_URL')
    if not u:
        raise RuntimeError('Missing PG_URL')
    return u


def http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def now() -> str:
    return datetime.now().isoformat(timespec='seconds')


def parse_rss(xml: str) -> list[tuple[str, str | None]]:
    """Return (url, published_at_iso?)"""
    items = re.findall(r"<item>(.*?)</item>", xml, flags=re.S | re.I)
    out = []
    for block in items:
        link = re.findall(r"<link[^>]*>(.*?)</link>", block, flags=re.S | re.I)
        pub = re.findall(r"<pubDate[^>]*>(.*?)</pubDate>", block, flags=re.S | re.I)
        u = (link[0] if link else '').strip()
        p = (pub[0] if pub else '').strip()
        dt_iso = None
        if p:
            try:
                dt_iso = parsedate_to_datetime(p).isoformat()
            except Exception:
                dt_iso = None
        if u:
            out.append((u, dt_iso))
    return out


def normalize_url(url: str) -> str:
    url = (url or '').strip()
    if url.startswith('http://vietstock.vn/'):
        url = 'https://vietstock.vn/' + url[len('http://vietstock.vn/') :]
    return url


def extract_urls(html: str) -> set[str]:
    urls = set(m.group(0) for m in ARTICLE_URL_RE.finditer(html))
    for m in REL_URL_RE.finditer(html):
        urls.add('https://vietstock.vn' + m.group(0))
    return {normalize_url(u) for u in urls if u}


def upsert_article_pending(cur, *, url: str, published_at: str | None, source: str, feed_url: str | None):
    cur.execute(
        """
        INSERT INTO articles (url, source, title, published_at, feed_url, fetch_status, discovered_at)
        VALUES (%s,%s,%s,%s,%s,'pending', now())
        ON CONFLICT (url) DO UPDATE SET
          published_at = COALESCE(EXCLUDED.published_at, articles.published_at),
          feed_url = COALESCE(EXCLUDED.feed_url, articles.feed_url),
          ingested_at = now();
        """,
        (url, source, url, published_at, feed_url),
    )


def main() -> int:
    rss_limit = int(os.environ.get('RSS_LIMIT', '500'))
    budget_pages = int(os.environ.get('BACKFILL_BUDGET_PAGES', '200'))
    rate = float(os.environ.get('RATE', '1'))
    stop_n = int(os.environ.get('NO_NEW_PAGES_STOP', '3'))

    sleep_s = 1.0 / max(rate, 0.1)

    discovered = 0
    backfill_pages = 0

    with psycopg2.connect(pg_url()) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            # RSS stage: read feeds from DB
            cur.execute("SELECT feed_url FROM feeds ORDER BY feed_url")
            feeds = [r[0] for r in cur.fetchall()]

            for feed_url in feeds:
                try:
                    xml = http_get(feed_url, timeout=30).decode('utf-8', errors='ignore')
                    items = parse_rss(xml)[:rss_limit]
                    newest = None
                    for (u, pub_iso) in items:
                        u = normalize_url(u)
                        upsert_article_pending(cur, url=u, published_at=pub_iso, source='rss', feed_url=feed_url)
                        discovered += 1
                        if pub_iso and (newest is None or pub_iso > newest):
                            newest = pub_iso
                    cur.execute(
                        "UPDATE feeds SET last_checked_at=now(), last_seen_published_at=COALESCE(%s,last_seen_published_at), updated_at=now() WHERE feed_url=%s",
                        (newest, feed_url),
                    )
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                time.sleep(sleep_s)

            # Backfill stage: crawl listing pages by channel_id
            # Ensure crawl_state rows exist
            cur.execute("SELECT seed_url FROM seeds WHERE enabled=true")
            seed_urls = [r[0] for r in cur.fetchall()]
            for su in seed_urls:
                cur.execute("INSERT INTO crawl_state(seed_url) VALUES(%s) ON CONFLICT DO NOTHING", (su,))
            conn.commit()

            cur.execute(
                """
                SELECT s.seed_url, s.channel_id, cs.next_page, cs.no_new_pages, cs.done
                FROM seeds s
                JOIN crawl_state cs ON cs.seed_url = s.seed_url
                WHERE s.enabled=true AND (cs.done=false)
                ORDER BY cs.last_crawled_at NULLS FIRST, s.seed_url
                """
            )
            seeds = cur.fetchall()

            for (seed_url, channel_id, next_page, no_new_pages, done) in seeds:
                if backfill_pages >= budget_pages:
                    break
                if not channel_id:
                    continue

                page = int(next_page or 1)
                url = f"https://vietstock.vn/StartPage/ChannelContentPage?channelID={int(channel_id)}&page={page}"
                try:
                    html = http_get(url, timeout=30).decode('utf-8', errors='ignore')
                    urls = extract_urls(html)
                    before = discovered
                    for u in urls:
                        upsert_article_pending(cur, url=u, published_at=None, source='backfill', feed_url=None)
                        discovered += 1

                    new_count = discovered - before
                    if new_count == 0:
                        no_new_pages = int(no_new_pages or 0) + 1
                    else:
                        no_new_pages = 0

                    page += 1
                    done_flag = (no_new_pages >= stop_n)

                    cur.execute(
                        """
                        UPDATE crawl_state
                        SET next_page=%s,
                            no_new_pages=%s,
                            done=%s,
                            last_crawled_at=now(),
                            last_error=NULL
                        WHERE seed_url=%s
                        """,
                        (page, no_new_pages, done_flag, seed_url),
                    )
                    conn.commit()
                except Exception as e:
                    cur.execute(
                        "UPDATE crawl_state SET last_error=%s, last_crawled_at=now() WHERE seed_url=%s",
                        (str(e)[:500], seed_url),
                    )
                    conn.commit()

                backfill_pages += 1
                time.sleep(sleep_s)

            # backfill_done flag
            cur.execute("SELECT COUNT(*) FROM crawl_state cs JOIN seeds s ON s.seed_url=cs.seed_url WHERE s.enabled=true AND cs.done=false")
            remaining = int(cur.fetchone()[0])
            if remaining == 0:
                cur.execute(
                    "INSERT INTO control_kv(key,value) VALUES('control.backfill_done','1') ON CONFLICT(key) DO UPDATE SET value='1', updated_at=now()"
                )
                conn.commit()

    print({
        'ok': True,
        'discovered': discovered,
        'backfill_pages': backfill_pages,
    })
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
