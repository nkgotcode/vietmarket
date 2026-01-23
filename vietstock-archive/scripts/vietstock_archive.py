#!/usr/bin/env python3
"""Vietstock local-first archiver.

Commands:
  init                Create DB + seed category list from RSS feeds list.
  rss                 Parse RSS cached feeds and enqueue article URLs.
  backfill            Crawl category listing pages (pagination) and enqueue article URLs.
  fetch               Fetch pending article URLs, store HTML+text.
  status              Show progress including oldest published_at seen.

Design goals:
- Zero non-stdlib dependencies.
- Gentle crawling with explicit rate limit.
- Store big content on disk, metadata in SQLite.

"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable, Optional

ROOT = Path("/Users/lenamkhanh/.clawdbot/vietstock-archive")
DB_PATH = ROOT / "archive.sqlite"
HTML_DIR = ROOT / "html"
TEXT_DIR = ROOT / "text"
LOG_DIR = ROOT / "logs"

# RSS relay
RELAY_INDEX = "http://127.0.0.1:18999/index.txt"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

ARTICLE_URL_RE = re.compile(r"https?://(?:www\.)?(?:vietstock\.vn|fili\.vn)/\d{4}/\d{2}/[^\s\"']+?\.htm", re.I)
REL_URL_RE = re.compile(r"/\d{4}/\d{2}/[^\s\"']+?\.htm", re.I)

# crude pagination patterns
PAGE_QS_RE = re.compile(r"[?&]page=(\d+)", re.I)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def apply_schema(conn: sqlite3.Connection, schema_sql: str) -> None:
    conn.executescript(schema_sql)
    conn.commit()


def http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def normalize_url(url: str) -> str:
    # normalize http->https for vietstock.vn
    url = url.strip()
    if url.startswith("http://vietstock.vn/"):
        url = "https://vietstock.vn/" + url[len("http://vietstock.vn/"):]
    return url


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def store_content(published_at: Optional[str], url: str, raw_html: bytes, cleaned_text: str) -> tuple[str, str, str, int]:
    # Partition by YYYY/MM based on published_at when possible.
    if published_at:
        try:
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            yyyy = f"{dt.year:04d}"
            mm = f"{dt.month:02d}"
        except Exception:
            yyyy, mm = "unknown", "unknown"
    else:
        yyyy, mm = "unknown", "unknown"

    h = sha256_bytes(raw_html)
    html_path = HTML_DIR / yyyy / mm / f"{h}.html"
    text_path = TEXT_DIR / yyyy / mm / f"{h}.txt"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.parent.mkdir(parents=True, exist_ok=True)

    if not html_path.exists():
        html_path.write_bytes(raw_html)
    if not text_path.exists():
        text_path.write_text(cleaned_text, encoding="utf-8")

    wc = len([w for w in cleaned_text.split() if w.strip()])
    return str(html_path), str(text_path), h, wc


def strip_tags(html_str: str) -> str:
    # super simple tag stripper
    html_str = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html_str)
    html_str = re.sub(r"(?is)<br\s*/?>", "\n", html_str)
    html_str = re.sub(r"(?is)</p\s*>", "\n", html_str)
    text = re.sub(r"(?is)<[^>]+>", " ", html_str)
    text = html.unescape(text)
    text = re.sub(r"[\t\r ]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_title(html_bytes: bytes) -> Optional[str]:
    s = html_bytes.decode("utf-8", errors="ignore")
    m = re.search(r"(?is)<meta\s+property=\"og:title\"\s+content=\"([^\"]+)\"", s)
    if m:
        return html.unescape(m.group(1)).strip()
    m = re.search(r"(?is)<title>(.*?)</title>", s)
    if m:
        return html.unescape(m.group(1)).strip()
    return None


def extract_published(html_bytes: bytes) -> Optional[str]:
    s = html_bytes.decode("utf-8", errors="ignore")
    # try dc.created or article:published_time
    for pat in [
        r"(?is)<meta\s+name=\"dc.created\"\s+content=\"([^\"]+)\"",
        r"(?is)<meta\s+property=\"article:published_time\"\s+content=\"([^\"]+)\"",
    ]:
        m = re.search(pat, s)
        if m:
            val = m.group(1).strip()
            # dc.created might be YYYY-MM-DD
            try:
                dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                return dt.isoformat(timespec="seconds")
            except Exception:
                pass
    return None


def rss_list_from_index(index_text: str) -> list[str]:
    # lines: "https://vietstock.vn/... -> /feeds/..."
    feeds = []
    for line in index_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        left = line.split("->", 1)[0].strip()
        if left.startswith("http") and left.endswith(".rss"):
            feeds.append(left)
    return feeds


def derive_seed_from_feed(feed_url: str) -> Optional[str]:
    # https://vietstock.vn/761/kinh-te/vi-mo.rss -> https://vietstock.vn/kinh-te/vi-mo.htm
    # https://vietstock.vn/144/chung-khoan.rss -> https://vietstock.vn/chung-khoan.htm
    u = urllib.parse.urlparse(feed_url)
    path = u.path
    path = path.replace("//", "/")
    # remove leading /<id>/
    m = re.match(r"^/(\d+)(/.*)$", path)
    if m:
        path = m.group(2)
    if not path.endswith(".rss"):
        return None
    path = path[:-4] + ".htm"
    return f"https://vietstock.vn{path}"


def upsert_article(conn: sqlite3.Connection, url: str, **fields) -> None:
    cols = ["url"] + list(fields.keys())
    placeholders = ",".join(["?"] * len(cols))
    updates = ",".join([f"{k}=excluded.{k}" for k in fields.keys()])
    sql = f"INSERT INTO articles ({','.join(cols)}) VALUES ({placeholders}) ON CONFLICT(url) DO UPDATE SET {updates}"
    conn.execute(sql, [url] + list(fields.values()))


def cmd_init(args: argparse.Namespace) -> int:
    # docs live at: clawd/vietstock-archive/docs
    docs_dir = Path(__file__).resolve().parents[1] / "docs"
    schema_path = docs_dir / "SCHEMA.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    conn = connect()
    apply_schema(conn, schema_sql)

    # load RSS feed list from relay index
    idx = http_get(RELAY_INDEX).decode("utf-8", errors="ignore")
    feed_urls = rss_list_from_index(idx)

    for f_url in feed_urls:
        conn.execute(
            "INSERT OR IGNORE INTO feeds(feed_url, kind) VALUES (?, 'rss')",
            (f_url,),
        )
        seed = derive_seed_from_feed(f_url)
        if seed:
            conn.execute(
                "INSERT OR IGNORE INTO seeds(seed_url, feed_url, kind, note) VALUES (?, ?, 'category', ?)",
                (seed, f_url, "derived from rss"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO crawl_state(seed_url, next_page) VALUES (?, 1)",
                (seed,),
            )

    conn.commit()
    print(f"Initialized DB at {DB_PATH} (feeds={len(feed_urls)})")
    return 0


def parse_rss_xml(xml_bytes: bytes) -> list[dict]:
    # minimal RSS parser using regex (no xml lib to keep it robust on bad feeds)
    s = xml_bytes.decode("utf-8", errors="ignore")
    items = []
    for m in re.finditer(r"(?is)<item>(.*?)</item>", s):
        block = m.group(1)
        link = None
        pub = None
        title = None

        lm = re.search(r"(?is)<link>(.*?)</link>", block)
        if lm:
            link = html.unescape(lm.group(1)).strip()
        tm = re.search(r"(?is)<title>(.*?)</title>", block)
        if tm:
            title = html.unescape(tm.group(1)).strip()
        pm = re.search(r"(?is)<pubDate>(.*?)</pubDate>", block)
        if pm:
            raw = pm.group(1).strip()
            try:
                dt = parsedate_to_datetime(raw)
                pub = dt.isoformat(timespec="seconds")
            except Exception:
                pub = None

        if link and ("vietstock.vn" in link or "fili.vn" in link):
            items.append({"url": normalize_url(link), "published_at": pub, "title": title})
    return items


def cmd_rss(args: argparse.Namespace) -> int:
    conn = connect()
    feeds = [row["feed_url"] for row in conn.execute("SELECT feed_url FROM feeds").fetchall()]

    # read directly from local relay cached files (faster than refetching public)
    # Use the relay index mapping to locate /feeds/*.xml
    idx = http_get(RELAY_INDEX).decode("utf-8", errors="ignore")
    mapping = {}
    for line in idx.splitlines():
        if "->" not in line:
            continue
        left, right = [x.strip() for x in line.split("->", 1)]
        if left.startswith("http") and right.startswith("/feeds/"):
            mapping[left] = "http://127.0.0.1:18999" + right

    total = 0
    for f_url in feeds:
        rss_url = mapping.get(f_url)
        if not rss_url:
            continue
        try:
            xml = http_get(rss_url, timeout=15)
        except Exception as e:
            conn.execute("UPDATE feeds SET last_checked_at=?, title=?, last_seen_published_at=? WHERE feed_url=?", (now_iso(), None, None, f_url))
            continue

        items = parse_rss_xml(xml)
        for it in items[: args.limit]:
            upsert_article(
                conn,
                it["url"],
                title=it.get("title"),
                published_at=it.get("published_at"),
                source="rss",
                feed_url=f_url,
                fetch_status="pending",
            )
            total += 1

        # update feed bookkeeping
        max_pub = None
        for it in items:
            if it.get("published_at"):
                if not max_pub or it["published_at"] > max_pub:
                    max_pub = it["published_at"]
        conn.execute(
            "UPDATE feeds SET last_checked_at=?, last_seen_published_at=? WHERE feed_url=?",
            (now_iso(), max_pub, f_url),
        )
        conn.commit()

    print(f"RSS enqueue done (upserted ~{total} items)")
    return 0


def extract_links_from_listing(html_bytes: bytes) -> set[str]:
    s = html_bytes.decode("utf-8", errors="ignore")
    links = set()

    # absolute URLs
    for m in ARTICLE_URL_RE.finditer(s):
        links.add(normalize_url(m.group(0)))

    # relative URLs
    for m in REL_URL_RE.finditer(s):
        links.add("https://vietstock.vn" + m.group(0))

    return links


def find_next_page(html_bytes: bytes, current: int) -> Optional[int]:
    s = html_bytes.decode("utf-8", errors="ignore")
    candidates = set()
    for m in PAGE_QS_RE.finditer(s):
        try:
            candidates.add(int(m.group(1)))
        except Exception:
            pass
    # prefer the smallest page > current
    nxt = sorted([p for p in candidates if p > current])
    return nxt[0] if nxt else None


def build_page_url(seed_url: str, page: int) -> str:
    u = urllib.parse.urlparse(seed_url)
    q = urllib.parse.parse_qs(u.query)
    q["page"] = [str(page)]
    new_q = urllib.parse.urlencode(q, doseq=True)
    return urllib.parse.urlunparse((u.scheme, u.netloc, u.path, u.params, new_q, u.fragment))


def cmd_backfill(args: argparse.Namespace) -> int:
    conn = connect()
    seeds = [row["seed_url"] for row in conn.execute("SELECT seed_url FROM seeds WHERE enabled=1").fetchall()]

    budget_pages = args.budget_pages
    pages_done = 0

    for seed in seeds:
        row = conn.execute("SELECT next_page FROM crawl_state WHERE seed_url=?", (seed,)).fetchone()
        next_page = int(row[0]) if row else 1

        while pages_done < budget_pages:
            url = build_page_url(seed, next_page)
            try:
                body = http_get(url, timeout=20)
            except Exception as e:
                conn.execute(
                    "UPDATE crawl_state SET last_crawled_at=?, last_error=? WHERE seed_url=?",
                    (now_iso(), str(e), seed),
                )
                conn.commit()
                break

            found = extract_links_from_listing(body)
            for a_url in found:
                upsert_article(
                    conn,
                    a_url,
                    source="backfill",
                    feed_url=None,
                    fetch_status="pending",
                )

            pages_done += 1
            conn.execute(
                "UPDATE crawl_state SET last_crawled_at=?, next_page=? WHERE seed_url=?",
                (now_iso(), next_page + 1, seed),
            )
            conn.commit()

            nxt = find_next_page(body, next_page)
            if not nxt:
                # No further pagination detected; stop this seed.
                break
            next_page = nxt

            # polite delay
            time.sleep(max(0.0, 1.0 / max(0.1, args.rate)))

        if pages_done >= budget_pages:
            break

    print(f"Backfill crawl done (pages={pages_done})")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    conn = connect()
    rows = conn.execute(
        "SELECT url FROM articles WHERE fetch_status='pending' ORDER BY COALESCE(published_at, discovered_at) DESC LIMIT ?",
        (args.limit,),
    ).fetchall()

    fetched = 0
    failed = 0

    for r in rows:
        url = r["url"]
        try:
            raw = http_get(url, timeout=30)
            title = extract_title(raw)
            pub = extract_published(raw)
            text = strip_tags(raw.decode("utf-8", errors="ignore"))
            html_path, text_path, h, wc = store_content(pub, url, raw, text)

            upsert_article(
                conn,
                url,
                title=title,
                published_at=pub,
                fetched_at=now_iso(),
                fetch_status="fetched",
                fetch_error=None,
                html_path=html_path,
                text_path=text_path,
                content_sha256=h,
                word_count=wc,
            )
            fetched += 1
        except Exception as e:
            upsert_article(
                conn,
                url,
                fetched_at=now_iso(),
                fetch_status="failed",
                fetch_error=str(e),
            )
            failed += 1

        conn.commit()
        time.sleep(max(0.0, 1.0 / max(0.1, args.rate)))

    print(f"Fetch done (fetched={fetched}, failed={failed})")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    conn = connect()

    def q1(sql: str, params=()):
        return conn.execute(sql, params).fetchone()[0]

    stats = {
        "db": str(DB_PATH),
        "articles": {
            "total": q1("SELECT COUNT(*) FROM articles"),
            "pending": q1("SELECT COUNT(*) FROM articles WHERE fetch_status='pending'"),
            "fetched": q1("SELECT COUNT(*) FROM articles WHERE fetch_status='fetched'"),
            "failed": q1("SELECT COUNT(*) FROM articles WHERE fetch_status='failed'"),
            "oldest_published_at": q1("SELECT MIN(published_at) FROM articles WHERE published_at IS NOT NULL"),
            "newest_published_at": q1("SELECT MAX(published_at) FROM articles WHERE published_at IS NOT NULL"),
        },
        "backfill": {
            "seeds": q1("SELECT COUNT(*) FROM seeds WHERE enabled=1"),
            "pages_state": [
                dict(row)
                for row in conn.execute(
                    "SELECT seed_url, next_page, last_crawled_at, last_error FROM crawl_state ORDER BY last_crawled_at DESC LIMIT 10"
                ).fetchall()
            ],
        },
    }

    if args.json:
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    else:
        print(f"DB: {stats['db']}")
        print(
            f"Articles total={stats['articles']['total']} pending={stats['articles']['pending']} fetched={stats['articles']['fetched']} failed={stats['articles']['failed']}"
        )
        print(
            f"Published range: oldest={stats['articles']['oldest_published_at']} newest={stats['articles']['newest_published_at']}"
        )
        print(f"Seeds enabled: {stats['backfill']['seeds']}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="vietstock-archive")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")

    p_rss = sub.add_parser("rss")
    p_rss.add_argument("--limit", type=int, default=500)

    p_b = sub.add_parser("backfill")
    p_b.add_argument("--budget-pages", type=int, default=100)
    p_b.add_argument("--rate", type=float, default=1.0, help="requests per second")

    p_f = sub.add_parser("fetch")
    p_f.add_argument("--limit", type=int, default=50)
    p_f.add_argument("--rate", type=float, default=1.0, help="requests per second")

    p_s = sub.add_parser("status")
    p_s.add_argument("--json", action="store_true")

    return p


def main(argv: list[str]) -> int:
    p = build_parser()
    args = p.parse_args(argv)

    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "rss":
        return cmd_rss(args)
    if args.cmd == "backfill":
        return cmd_backfill(args)
    if args.cmd == "fetch":
        return cmd_fetch(args)
    if args.cmd == "status":
        return cmd_status(args)

    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
