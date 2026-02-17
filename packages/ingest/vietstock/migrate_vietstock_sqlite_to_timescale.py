#!/usr/bin/env python3
"""One-time migration: Vietstock archive SQLite → TimescaleDB.

This helps transition from the legacy local-first sqlite archive into the Timescale-first system.

What it migrates:
- feeds
- seeds
- crawl_state
- articles metadata
- article full text (reads text_path file when present)

Env:
- PG_URL (required)
- VIETSTOCK_ARCHIVE_DB (optional)
- TEXT_MAX_CHARS (optional, default 200000)

Usage:
  PG_URL=... python packages/ingest/vietstock/migrate_vietstock_sqlite_to_timescale.py
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import psycopg2
import psycopg2.extras


def pg_url() -> str:
    u = os.environ.get('PG_URL')
    if not u:
        raise RuntimeError('Missing PG_URL')
    return u


def archive_db() -> Path:
    return Path(os.environ.get('VIETSTOCK_ARCHIVE_DB', '/Users/lenamkhanh/vietstock-archive-data/archive.sqlite'))


def read_text_file(p: str | None, max_chars: int) -> str | None:
    if not p:
        return None
    try:
        return Path(p).read_text('utf-8', errors='ignore')[:max_chars]
    except Exception:
        return None


def main() -> int:
    dbp = archive_db()
    if not dbp.exists():
        raise RuntimeError(f'archive sqlite not found: {dbp}')

    max_chars = int(os.environ.get('TEXT_MAX_CHARS', '200000'))

    s = sqlite3.connect(str(dbp))
    s.row_factory = sqlite3.Row

    with psycopg2.connect(pg_url()) as pg:
        with pg.cursor() as cur:
            # feeds
            for r in s.execute('SELECT feed_url, kind, title, last_seen_published_at, last_checked_at FROM feeds'):
                cur.execute(
                    """
                    INSERT INTO feeds (feed_url, kind, title, last_seen_published_at, last_checked_at)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT (feed_url) DO UPDATE SET
                      kind=EXCLUDED.kind,
                      title=COALESCE(EXCLUDED.title, feeds.title),
                      last_seen_published_at=COALESCE(EXCLUDED.last_seen_published_at, feeds.last_seen_published_at),
                      last_checked_at=COALESCE(EXCLUDED.last_checked_at, feeds.last_checked_at),
                      updated_at=now();
                    """,
                    (r['feed_url'], r['kind'], r['title'], r['last_seen_published_at'], r['last_checked_at']),
                )

            # seeds
            for r in s.execute('SELECT seed_url, feed_url, channel_id, kind, note, enabled, created_at FROM seeds'):
                cur.execute(
                    """
                    INSERT INTO seeds (seed_url, feed_url, channel_id, kind, note, enabled, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (seed_url) DO UPDATE SET
                      feed_url=COALESCE(EXCLUDED.feed_url, seeds.feed_url),
                      channel_id=COALESCE(EXCLUDED.channel_id, seeds.channel_id),
                      kind=EXCLUDED.kind,
                      note=COALESCE(EXCLUDED.note, seeds.note),
                      enabled=EXCLUDED.enabled;
                    """,
                    (r['seed_url'], r['feed_url'], r['channel_id'], r['kind'], r['note'], bool(r['enabled']), r['created_at']),
                )

            # crawl_state
            for r in s.execute('SELECT seed_url, next_page, done, no_new_pages, last_crawled_at, oldest_seen_published_at, last_error FROM crawl_state'):
                cur.execute(
                    """
                    INSERT INTO crawl_state (seed_url, next_page, done, no_new_pages, last_crawled_at, oldest_seen_published_at, last_error)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (seed_url) DO UPDATE SET
                      next_page=EXCLUDED.next_page,
                      done=EXCLUDED.done,
                      no_new_pages=EXCLUDED.no_new_pages,
                      last_crawled_at=EXCLUDED.last_crawled_at,
                      oldest_seen_published_at=EXCLUDED.oldest_seen_published_at,
                      last_error=EXCLUDED.last_error;
                    """,
                    (
                        r['seed_url'],
                        int(r['next_page'] or 1),
                        bool(r['done'] or 0),
                        bool(r['no_new_pages'] or 0),
                        r['last_crawled_at'],
                        r['oldest_seen_published_at'],
                        r['last_error'],
                    ),
                )

            # articles: migrate metadata + full text
            # NOTE: this can be heavy; it is safe to re-run.
            rows = s.execute(
                """
                SELECT url, canonical_url, title, published_at, source, feed_url,
                       discovered_at, fetched_at, fetch_status, fetch_method, fetch_error,
                       text_path, content_sha256, word_count, lang
                FROM articles
                WHERE url IS NOT NULL
                """
            )

            batch = []
            for r in rows:
                text = read_text_file(r['text_path'], max_chars)
                batch.append((
                    r['url'], r['canonical_url'], r['source'] or 'rss', r['title'] or r['url'], r['published_at'], r['feed_url'],
                    r['discovered_at'], r['fetched_at'], r['fetch_status'] or 'pending', r['fetch_method'], r['fetch_error'],
                    text, r['content_sha256'], r['word_count'], r['lang'],
                ))

                if len(batch) >= 200:
                    psycopg2.extras.execute_values(
                        cur,
                        """
                        INSERT INTO articles (
                          url, canonical_url, source, title, published_at, feed_url,
                          discovered_at, fetched_at, fetch_status, fetch_method, fetch_error,
                          text, content_sha256, word_count, lang
                        ) VALUES %s
                        ON CONFLICT (url) DO UPDATE SET
                          canonical_url=COALESCE(EXCLUDED.canonical_url, articles.canonical_url),
                          title=EXCLUDED.title,
                          published_at=COALESCE(EXCLUDED.published_at, articles.published_at),
                          feed_url=COALESCE(EXCLUDED.feed_url, articles.feed_url),
                          fetched_at=COALESCE(EXCLUDED.fetched_at, articles.fetched_at),
                          fetch_status=EXCLUDED.fetch_status,
                          fetch_method=COALESCE(EXCLUDED.fetch_method, articles.fetch_method),
                          fetch_error=COALESCE(EXCLUDED.fetch_error, articles.fetch_error),
                          text=COALESCE(EXCLUDED.text, articles.text),
                          content_sha256=COALESCE(EXCLUDED.content_sha256, articles.content_sha256),
                          word_count=COALESCE(EXCLUDED.word_count, articles.word_count),
                          lang=COALESCE(EXCLUDED.lang, articles.lang),
                          ingested_at=now();
                        """.strip(),
                        batch,
                        page_size=200,
                    )
                    batch.clear()

            if batch:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO articles (
                      url, canonical_url, source, title, published_at, feed_url,
                      discovered_at, fetched_at, fetch_status, fetch_method, fetch_error,
                      text, content_sha256, word_count, lang
                    ) VALUES %s
                    ON CONFLICT (url) DO UPDATE SET
                      canonical_url=COALESCE(EXCLUDED.canonical_url, articles.canonical_url),
                      title=EXCLUDED.title,
                      published_at=COALESCE(EXCLUDED.published_at, articles.published_at),
                      feed_url=COALESCE(EXCLUDED.feed_url, articles.feed_url),
                      fetched_at=COALESCE(EXCLUDED.fetched_at, articles.fetched_at),
                      fetch_status=EXCLUDED.fetch_status,
                      fetch_method=COALESCE(EXCLUDED.fetch_method, articles.fetch_method),
                      fetch_error=COALESCE(EXCLUDED.fetch_error, articles.fetch_error),
                      text=COALESCE(EXCLUDED.text, articles.text),
                      content_sha256=COALESCE(EXCLUDED.content_sha256, articles.content_sha256),
                      word_count=COALESCE(EXCLUDED.word_count, articles.word_count),
                      lang=COALESCE(EXCLUDED.lang, articles.lang),
                      ingested_at=now();
                    """.strip(),
                    batch,
                    page_size=200,
                )

    print({"ok": True, "sqlite": str(dbp)})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
