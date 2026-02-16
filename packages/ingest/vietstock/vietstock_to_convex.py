#!/usr/bin/env python3
"""Sync Vietstock archive (local SQLite + cleaned text files) into Convex.

Reads /Users/lenamkhanh/vietstock-archive-data/archive.sqlite (or VIETSTOCK_ARCHIVE_DB) and for fetched articles
pushes metadata + full cleaned text into Convex File Storage via a mutation.

Env:
  CONVEX_URL=https://<deployment>.convex.cloud

Cursor:
  Writes tmp/vietmarket_vietstock_cursor.json by default.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests


def convex_url() -> str:
    u = os.environ.get('CONVEX_URL') or os.environ.get('NEXT_PUBLIC_CONVEX_URL')
    if not u:
        raise RuntimeError('Missing CONVEX_URL')
    return u.rstrip('/')


def convex_mutation(path: str, args: dict, timeout_s: int = 60) -> dict:
    url = convex_url() + '/api/mutation'
    r = requests.post(url, json={'path': path, 'args': args}, timeout=timeout_s)
    r.raise_for_status()
    return r.json()


@dataclass
class Article:
    url: str
    title: str
    published_at: Optional[str]
    source: str
    text_path: Optional[str]
    lang: Optional[str]
    word_count: Optional[int]
    discovered_at: Optional[str]


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument('--db', default=os.environ.get('VIETSTOCK_ARCHIVE_DB', str(Path('/Users/lenamkhanh/vietstock-archive-data/archive.sqlite'))))
    p.add_argument('--cursor-file', default='tmp/vietmarket_vietstock_cursor.json')
    p.add_argument('--limit', type=int, default=50)
    p.add_argument('--since', help='ISO timestamp to start from (overrides cursor)')
    return p.parse_args(argv)


def read_cursor(path: Path) -> dict:
    try:
        return json.loads(path.read_text('utf-8'))
    except Exception:
        return {}


def write_cursor(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding='utf-8')


def load_batch(con: sqlite3.Connection, since: str | None, limit: int) -> list[Article]:
    cur = con.cursor()
    q = (
        "SELECT url, title, published_at, source, text_path, lang, word_count, discovered_at "
        "FROM articles "
        "WHERE fetch_status='fetched' AND text_path IS NOT NULL "
    )
    args: list = []
    if since:
        q += " AND discovered_at > ? "
        args.append(since)
    q += " ORDER BY discovered_at ASC LIMIT ?"
    args.append(limit)

    rows = []
    for r in cur.execute(q, args):
        rows.append(Article(
            url=r[0],
            title=r[1] or '',
            published_at=r[2],
            source=r[3] or 'vietstock',
            text_path=r[4],
            lang=r[5],
            word_count=r[6],
            discovered_at=r[7],
        ))
    return rows


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    cursor_path = Path(args.cursor_file)
    cursor = read_cursor(cursor_path)

    since = args.since or cursor.get('since')

    db_path = Path(args.db)
    con = sqlite3.connect(str(db_path))

    batch = load_batch(con, since, args.limit)
    if not batch:
        print(json.dumps({'ok': True, 'synced': 0, 'since': since}))
        return 0

    synced = 0
    last_discovered = since

    for art in batch:
        text_file = Path(art.text_path).expanduser()
        if not text_file.exists():
            continue
        text = text_file.read_text('utf-8', errors='replace')
        if not text.strip():
            continue

        payload = {
            'url': art.url,
            'source': 'vietstock',
            'title': art.title or art.url,
            'publishedAt': art.published_at,
            'lang': art.lang,
            'wordCount': int(art.word_count) if art.word_count is not None else None,
            'text': text,
        }
        # Convex validators treat optional fields as "undefined"; avoid sending JSON null.
        payload = {k: v for k, v in payload.items() if v is not None}

        out = convex_mutation('articles:upsertWithText', payload, timeout_s=90)
        _ = out.get('value', out)

        synced += 1
        last_discovered = art.discovered_at or last_discovered

    write_cursor(cursor_path, {
        'since': last_discovered,
        'lastRun': cursor.get('lastRun'),
        'syncedTotalLastRun': synced,
    })

    print(json.dumps({'ok': True, 'synced': synced, 'since': since, 'nextSince': last_discovered}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(os.sys.argv[1:]))
