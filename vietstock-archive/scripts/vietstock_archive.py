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

    # Lightweight migrations for older DBs.
    def ensure_col(table: str, col: str, decl: str) -> None:
        cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if col not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

    ensure_col("articles", "fetch_method", "TEXT")
    ensure_col("seeds", "channel_id", "INTEGER")
    ensure_col("crawl_state", "done", "INTEGER NOT NULL DEFAULT 0")
    ensure_col("crawl_state", "no_new_pages", "INTEGER NOT NULL DEFAULT 0")

    conn.commit()


def http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_get_playwright(url: str, timeout_ms: int = 45000) -> bytes:
    """Fetch rendered HTML using Playwright (Node).

    Requires: `npm i playwright` (or already present in node_modules/global).
    """
    import subprocess

    js = r"""
const url = process.argv[1];
const timeoutMs = parseInt(process.argv[2], 10) || 45000;
(async () => {
  const { chromium } = require('playwright');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
  const html = await page.content();
  await browser.close();
  process.stdout.write(html);
})().catch(err => { console.error(String(err && err.stack || err)); process.exit(1); });
""".strip()

    p = subprocess.run(
        ["node", "-e", js, url, str(timeout_ms)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if p.returncode != 0:
        raise RuntimeError(f"playwright fetch failed: {p.stderr.decode('utf-8', errors='ignore')[:500]}")
    return p.stdout


def fetch_html(url: str, timeout: int = 30, playwright_fallback: bool = True) -> bytes:
    """Fetch HTML; fallback to Playwright on blocks or low-content responses."""
    try:
        return http_get(url, timeout=timeout)
    except Exception as e:
        if playwright_fallback:
            return http_get_playwright(url)
        raise


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


def extract_main_text(html_bytes: bytes) -> str:
    """Vietstock-specific-ish extractor.

    Prefer known paragraph classes (pHead/pBody/pTitle) found in Vietstock article pages.
    Fallback to full-page tag stripping.
    """
    s = html_bytes.decode("utf-8", errors="ignore")

    # Vietstock article body commonly uses <p class="pHead"> and <p class="pBody">.
    paras = []
    for cls in ("pTitle", "pHead", "pBody"):
        for m in re.finditer(rf"(?is)<p[^>]*class=\"{cls}\"[^>]*>(.*?)</p>", s):
            t = strip_tags(m.group(1))
            if t:
                paras.append(t)

    # Dedupe consecutive duplicates
    cleaned = []
    for p in paras:
        if not cleaned or cleaned[-1] != p:
            cleaned.append(p)

    # If we got a reasonable amount of content, return it.
    if len(" ".join(cleaned).split()) >= 80:
        return "\n\n".join(cleaned).strip()

    return strip_tags(s)


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

    # Prefer real article timestamps first.
    for pat in [
        r"(?is)<meta\s+property=\"article:published_time\"\s+content=\"([^\"]+)\"",
        r"(?is)<meta\s+itemprop=\"datePublished\"[^>]*content=\"([^\"]+)\"",
    ]:
        m = re.search(pat, s)
        if m:
            val = m.group(1).strip()
            try:
                dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                return dt.isoformat(timespec="seconds")
            except Exception:
                pass

    # Vietstock page markup often has a visible timestamp block.
    m = re.search(r"(?is)<span\s+class=\"datenew\"[^>]*>([^<]+)</span>", s)
    if m:
        raw = html.unescape(m.group(1)).strip()
        # e.g. 23-01-2026 22:15:00+07:00
        try:
            if re.match(r"^\d{2}-\d{2}-\d{4} ", raw):
                dd, mm, yyyy = raw[0:2], raw[3:5], raw[6:10]
                rest = raw[11:]
                iso = f"{yyyy}-{mm}-{dd}T{rest}"
                dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
                return dt.isoformat(timespec="seconds")
        except Exception:
            pass

    # dc.created is frequently present but often a site default (e.g. 2002-01-01). Only use if it's not the default.
    m = re.search(r"(?is)<meta\s+name=\"dc.created\"\s+content=\"([^\"]+)\"", s)
    if m:
        val = m.group(1).strip()
        if val and val != "2002-01-01":
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


def parse_feed_id(feed_url: str) -> Optional[int]:
    u = urllib.parse.urlparse(feed_url)
    m = re.match(r"^/(\d+)/", u.path or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def derive_seed_from_feed(feed_url: str) -> Optional[str]:
    # https://vietstock.vn/761/kinh-te/vi-mo.rss -> https://vietstock.vn/kinh-te/vi-mo.htm
    # https://vietstock.vn/144/chung-khoan.rss -> https://vietstock.vn/chung-khoan.htm
    u = urllib.parse.urlparse(feed_url)
    path = (u.path or "").replace("//", "/")
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


def bump_kv(conn: sqlite3.Connection, key: str, delta: int = 1) -> None:
    conn.execute(
        "INSERT INTO kv(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=CAST(value AS INTEGER)+?, updated_at=datetime('now')",
        (key, str(delta), delta),
    )


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
            channel_id = parse_feed_id(f_url)
            conn.execute(
                "INSERT OR IGNORE INTO seeds(seed_url, feed_url, channel_id, kind, note) VALUES (?, ?, ?, 'category', ?)",
                (seed, f_url, channel_id, "derived from rss"),
            )
            # Ensure channel_id is populated if the row existed already.
            if channel_id is not None:
                conn.execute(
                    "UPDATE seeds SET channel_id=COALESCE(channel_id, ?) WHERE seed_url=?",
                    (channel_id, seed),
                )
            conn.execute(
                "INSERT OR IGNORE INTO crawl_state(seed_url, next_page, done, no_new_pages) VALUES (?, 1, 0, 0)",
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
    feeds_rows = conn.execute(
        "SELECT feed_url, last_seen_published_at FROM feeds"
    ).fetchall()

    # read directly from local relay cached files (faster than refetching public)
    # Use the relay index mapping to locate /feeds/*.xml
    idx = http_get(RELAY_INDEX).decode("utf-8", errors="ignore")
    mapping: dict[str, str] = {}
    for line in idx.splitlines():
        if "->" not in line:
            continue
        left, right = [x.strip() for x in line.split("->", 1)]
        if left.startswith("http") and right.startswith("/feeds/"):
            mapping[left] = "http://127.0.0.1:18999" + right

    feeds_ok = 0
    feeds_err = 0
    scanned = 0
    inserted = 0
    meta_filled = 0
    skipped_old = 0
    skipped_dupe = 0

    per_feed: list[dict] = []

    for row in feeds_rows:
        f_url = row["feed_url"]
        last_seen = (row["last_seen_published_at"] or "").strip() or None

        rss_url = mapping.get(f_url)
        if not rss_url:
            continue

        st = {
            "feed_url": f_url,
            "last_seen": last_seen,
            "items_in_feed": 0,
            "scanned": 0,
            "inserted": 0,
            "meta_filled": 0,
            "skipped_dupe": 0,
            "skipped_old_early": 0,
            "error": None,
            "max_pub": None,
        }

        try:
            xml = http_get(rss_url, timeout=15)
        except Exception as e:
            feeds_err += 1
            st["error"] = (str(e) or "rss fetch error")[:120]
            conn.execute(
                "UPDATE feeds SET last_checked_at=? WHERE feed_url=?",
                (now_iso(), f_url),
            )
            per_feed.append(st)
            continue

        feeds_ok += 1
        items = parse_rss_xml(xml)
        st["items_in_feed"] = len(items)

        # Feeds are usually newest-first. Stop early once we reach items we have already seen.
        for it in items[: args.limit]:
            scanned += 1
            st["scanned"] += 1

            pub = it.get("published_at")
            if pub and (not st["max_pub"] or pub > st["max_pub"]):
                st["max_pub"] = pub

            if last_seen and pub and pub <= last_seen:
                skipped_old += 1
                st["skipped_old_early"] += 1
                break

            url = it["url"]

            # Insert new row only; never clobber fetch_status.
            cur = conn.execute(
                "INSERT OR IGNORE INTO articles(url, title, published_at, source, feed_url, fetch_status) "
                "VALUES (?, ?, ?, 'rss', ?, 'pending')",
                (url, it.get("title"), pub, f_url),
            )
            if cur.rowcount == 1:
                inserted += 1
                st["inserted"] += 1
                continue

            skipped_dupe += 1
            st["skipped_dupe"] += 1

            # Existing row: only fill missing metadata; avoid a write if nothing to fill.
            cur2 = conn.execute(
                "UPDATE articles SET "
                " title=COALESCE(title, ?), "
                " published_at=COALESCE(published_at, ?), "
                " source=COALESCE(source, 'rss'), "
                " feed_url=COALESCE(feed_url, ?) "
                "WHERE url=? AND (title IS NULL OR published_at IS NULL OR feed_url IS NULL OR source IS NULL)",
                (it.get("title"), pub, f_url, url),
            )
            if cur2.rowcount == 1:
                meta_filled += 1
                st["meta_filled"] += 1

        # update feed bookkeeping
        conn.execute(
            "UPDATE feeds SET last_checked_at=?, last_seen_published_at=COALESCE(?, last_seen_published_at) WHERE feed_url=?",
            (now_iso(), st["max_pub"], f_url),
        )

        per_feed.append(st)

    conn.commit()

    # Meaningful summary: what actually changed.
    print(
        "RSS enqueue: "
        f"feeds_ok={feeds_ok}, feeds_err={feeds_err}, scanned={scanned}, "
        f"inserted={inserted}, meta_filled={meta_filled}, "
        f"skipped_dupe={skipped_dupe}, skipped_old_early={skipped_old}"
    )

    # Full per-feed breakdown (sorted by inserted desc, then scanned desc).
    def k(x: dict):
        return (-int(x.get("inserted") or 0), -int(x.get("scanned") or 0), x.get("feed_url") or "")

    for st in sorted(per_feed, key=k):
        # Shorten URL display a bit.
        f = st["feed_url"]
        if f.startswith("https://vietstock.vn/"):
            f_disp = f[len("https://vietstock.vn/"):]
        else:
            f_disp = f

        if st.get("error"):
            print(f"- FEED {f_disp}: ERROR={st['error']}")
            continue

        print(
            "- FEED "
            + f_disp
            + ": "
            + f"items={st['items_in_feed']}, scanned={st['scanned']}, inserted={st['inserted']}, "
            + f"meta_filled={st['meta_filled']}, skipped_dupe={st['skipped_dupe']}, "
            + f"stopped_old={st['skipped_old_early'] > 0}, last_seen={st['last_seen'] or '-'}, max_pub={st['max_pub'] or '-'}"
        )

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


def fetch_channel_page(channel_id: int, page: int, fromdate: str = "", todate: str = "") -> bytes:
    """Fetch Vietstock channel listing page HTML.

    Channel pages render content via JS that calls:
      /StartPage/ChannelContentPage?channelID=<id>&page=<n>[&fromdate=YYYY-MM-DD&todate=YYYY-MM-DD]

    This endpoint returns HTML containing the listing items with article links.
    """
    qs = {
        "channelID": str(channel_id),
        "page": str(page),
    }
    if fromdate:
        qs["fromdate"] = fromdate
    if todate:
        qs["todate"] = todate
    url = "https://vietstock.vn/StartPage/ChannelContentPage?" + urllib.parse.urlencode(qs)
    return http_get(url, timeout=25)


def cmd_backfill(args: argparse.Namespace) -> int:
    conn = connect()

    # Manual global stop switch.
    backfill_done = conn.execute("SELECT value FROM kv WHERE key='backfill.done'").fetchone()
    if backfill_done and str(backfill_done[0]).strip() == "1":
        print("Backfill disabled (kv.backfill.done=1).")
        return 0

    # Load enabled seeds with channel_id.
    seeds = conn.execute(
        "SELECT seed_url, COALESCE(channel_id, 0) AS channel_id FROM seeds WHERE enabled=1 ORDER BY seed_url"
    ).fetchall()

    budget_pages = args.budget_pages
    pages_done = 0
    seeds_done_this_run = 0

    for row in seeds:
        seed_url = row["seed_url"]
        channel_id = int(row["channel_id"] or 0)

        st = conn.execute(
            "SELECT next_page, done, no_new_pages FROM crawl_state WHERE seed_url=?",
            (seed_url,),
        ).fetchone()
        next_page = int(st[0]) if st else 1
        done = int(st[1]) if st else 0
        no_new_pages = int(st[2]) if st else 0

        if done:
            seeds_done_this_run += 1
            continue

        while pages_done < budget_pages:
            try:
                if channel_id:
                    body = fetch_channel_page(channel_id, next_page)
                else:
                    # Fallback: fetch the seed page directly.
                    body = http_get(build_page_url(seed_url, next_page), timeout=20)
            except Exception as e:
                conn.execute(
                    "UPDATE crawl_state SET last_crawled_at=?, last_error=? WHERE seed_url=?",
                    (now_iso(), str(e), seed_url),
                )
                conn.commit()
                break

            found = extract_links_from_listing(body)

            new_inserts = 0
            for a_url in found:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO articles(url, source, fetch_status) VALUES (?, 'backfill', 'pending')",
                    (a_url,),
                )
                if cur.rowcount:
                    new_inserts += 1
                conn.execute(
                    "UPDATE articles SET source=COALESCE(source, 'backfill') WHERE url=?",
                    (a_url,),
                )

            pages_done += 1

            if new_inserts == 0:
                no_new_pages += 1
            else:
                no_new_pages = 0

            # If we got 3 consecutive pages with no new links, assume we've bottomed out for this seed.
            seed_done = 1 if no_new_pages >= 3 else 0

            conn.execute(
                "UPDATE crawl_state SET last_crawled_at=?, next_page=?, no_new_pages=?, done=?, last_error=NULL WHERE seed_url=?",
                (now_iso(), next_page + 1, no_new_pages, seed_done, seed_url),
            )
            conn.commit()

            next_page += 1

            if seed_done:
                seeds_done_this_run += 1
                break

            time.sleep(max(0.0, 1.0 / max(0.1, args.rate)))

        if pages_done >= budget_pages:
            break

    # If all seeds are done, set global flag.
    total_enabled = conn.execute("SELECT COUNT(*) FROM seeds WHERE enabled=1").fetchone()[0]
    total_done = conn.execute("SELECT COUNT(*) FROM crawl_state WHERE done=1").fetchone()[0]
    if total_enabled and total_done >= total_enabled:
        conn.execute(
            "INSERT INTO kv(key,value) VALUES('backfill.done','1') ON CONFLICT(key) DO UPDATE SET value='1', updated_at=datetime('now')"
        )
        conn.commit()
        print(f"Backfill crawl done (pages={pages_done}). All seeds done; set kv.backfill.done=1")
        return 0

    print(f"Backfill crawl done (pages={pages_done})")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    """Fetch pending URLs.

    Supports parallel workers (thread pool) because urllib + Playwright calls are blocking.
    Global rate limit is enforced across workers (approximate, best-effort).
    """

    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    conn = connect()
    # Fetch ordering strategy:
    # For backfill progress (make `oldest_published_at` move earlier), prefer *older-looking URLs*
    # based on the /YYYY/MM/ segment in the article URL, rather than newest-first.
    #
    # Note: `published_at` is usually NULL for pending rows, so ordering purely by published_at
    # won't help us reach older history.
    rows = conn.execute(
        "SELECT url, discovered_at FROM articles WHERE fetch_status='pending' ORDER BY discovered_at ASC LIMIT ?",
        (max(100, args.limit * 10),),
    ).fetchall()

    def url_ym_key(u: str):
        # Typical Vietstock/Fili pattern: https://vietstock.vn/YYYY/MM/... .htm
        m = re.search(r"/(\d{4})/(\d{2})/", u)
        if m:
            return (int(m.group(1)), int(m.group(2)), u)
        # Unknown format: push to the end.
        return (9999, 99, u)

    # Prefer oldest year/month first; tie-break by URL for stability.
    urls = [r["url"] for r in sorted(rows, key=lambda r: url_ym_key(r["url"]))][: args.limit]

    fetched = 0
    failed = 0

    # Best-effort global rate limiting across workers.
    rate_lock = threading.Lock()
    next_ok = {"t": time.monotonic()}

    def rate_wait() -> None:
        # Ensure at most `args.rate` requests/sec across all workers.
        interval = 1.0 / max(0.1, args.rate)
        with rate_lock:
            now = time.monotonic()
            t = max(now, next_ok["t"])
            sleep_s = t - now
            next_ok["t"] = t + interval
        if sleep_s > 0:
            time.sleep(sleep_s)

    def fetch_one(url: str) -> dict:
        try:
            fetch_method = "http"

            # Primary HTTP attempt (rate-limited)
            try:
                rate_wait()
                raw = http_get(url, timeout=30)
            except Exception:
                # Hard failure -> Playwright fallback (not rate-limited; expensive but rare)
                raw = http_get_playwright(url)
                fetch_method = "playwright"

            title = extract_title(raw)
            pub = extract_published(raw)
            text = extract_main_text(raw)
            html_path, text_path, h, wc = store_content(pub, url, raw, text)

            # If the extracted body is suspiciously short, try Playwright once.
            if wc < 80 and fetch_method != "playwright":
                try:
                    raw2 = http_get_playwright(url)
                    title2 = extract_title(raw2) or title
                    pub2 = extract_published(raw2) or pub
                    text2 = extract_main_text(raw2)
                    html_path, text_path, h, wc = store_content(pub2, url, raw2, text2)
                    title, pub, wc = title2, pub2, wc
                    fetch_method = "playwright"
                except Exception:
                    pass

            return {
                "ok": True,
                "url": url,
                "title": title,
                "published_at": pub,
                "fetch_method": fetch_method,
                "html_path": html_path,
                "text_path": text_path,
                "content_sha256": h,
                "word_count": wc,
            }
        except Exception as e:
            return {"ok": False, "url": url, "error": str(e)}

    workers = max(1, int(getattr(args, "workers", 1) or 1))

    # workers=1 keeps behavior similar to the old sequential path (but still uses helper).
    if workers == 1:
        for url in urls:
            res = fetch_one(url)
            if res["ok"]:
                upsert_article(
                    conn,
                    res["url"],
                    title=res.get("title"),
                    published_at=res.get("published_at"),
                    fetched_at=now_iso(),
                    fetch_status="fetched",
                    fetch_method=res.get("fetch_method"),
                    fetch_error=None,
                    html_path=res.get("html_path"),
                    text_path=res.get("text_path"),
                    content_sha256=res.get("content_sha256"),
                    word_count=res.get("word_count"),
                )
                if res.get("fetch_method") == "playwright":
                    bump_kv(conn, "fetch.playwright_used", 1)
                else:
                    bump_kv(conn, "fetch.http_used", 1)
                fetched += 1
            else:
                upsert_article(
                    conn,
                    res["url"],
                    fetched_at=now_iso(),
                    fetch_status="failed",
                    fetch_error=res.get("error"),
                )
                bump_kv(conn, "fetch.failed", 1)
                failed += 1
            conn.commit()

        print(f"Fetch done (fetched={fetched}, failed={failed})")
        return 0

    # Parallel worker pool
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(fetch_one, url) for url in urls]
        for fut in as_completed(futs):
            res = fut.result()

            if res["ok"]:
                upsert_article(
                    conn,
                    res["url"],
                    title=res.get("title"),
                    published_at=res.get("published_at"),
                    fetched_at=now_iso(),
                    fetch_status="fetched",
                    fetch_method=res.get("fetch_method"),
                    fetch_error=None,
                    html_path=res.get("html_path"),
                    text_path=res.get("text_path"),
                    content_sha256=res.get("content_sha256"),
                    word_count=res.get("word_count"),
                )
                if res.get("fetch_method") == "playwright":
                    bump_kv(conn, "fetch.playwright_used", 1)
                else:
                    bump_kv(conn, "fetch.http_used", 1)
                fetched += 1
            else:
                upsert_article(
                    conn,
                    res["url"],
                    fetched_at=now_iso(),
                    fetch_status="failed",
                    fetch_error=res.get("error"),
                )
                bump_kv(conn, "fetch.failed", 1)
                failed += 1

            # keep commits frequent to avoid large transactions
            conn.commit()

    print(f"Fetch done (fetched={fetched}, failed={failed})")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    conn = connect()

    def q1(sql: str, params=()):
        row = conn.execute(sql, params).fetchone()
        return row[0] if row is not None else None

    # Consistency checks: detect rows where status doesn't match stored paths/errors.
    pending_with_files = q1(
        """
        SELECT COUNT(*)
        FROM articles
        WHERE fetch_status='pending'
          AND html_path IS NOT NULL
          AND text_path IS NOT NULL
        """
    )
    fetched_missing_files = q1(
        """
        SELECT COUNT(*)
        FROM articles
        WHERE fetch_status='fetched'
          AND (html_path IS NULL OR text_path IS NULL)
        """
    )
    failed_without_error = q1(
        """
        SELECT COUNT(*)
        FROM articles
        WHERE fetch_status='failed'
          AND (fetch_error IS NULL OR fetch_error='')
        """
    )

    stats = {
        "db": str(DB_PATH),
        "articles": {
            "total": q1("SELECT COUNT(*) FROM articles"),
            "pending": q1("SELECT COUNT(*) FROM articles WHERE fetch_status='pending'"),
            "fetched": q1("SELECT COUNT(*) FROM articles WHERE fetch_status='fetched'"),
            "failed": q1("SELECT COUNT(*) FROM articles WHERE fetch_status='failed'"),
            "oldest_published_at": q1("SELECT MIN(published_at) FROM articles WHERE published_at IS NOT NULL AND published_at NOT LIKE '2002-01-01%'"),
            "newest_published_at": q1("SELECT MAX(published_at) FROM articles WHERE published_at IS NOT NULL AND published_at NOT LIKE '2002-01-01%'"),
        },
        "consistency": {
            "pending_with_files": pending_with_files or 0,
            "fetched_missing_files": fetched_missing_files or 0,
            "failed_without_error": failed_without_error or 0,
        },
        "fetch": {
            "http_used": q1("SELECT CAST(value AS INTEGER) FROM kv WHERE key='fetch.http_used'") or 0,
            "playwright_used": q1("SELECT CAST(value AS INTEGER) FROM kv WHERE key='fetch.playwright_used'") or 0,
            "failed": q1("SELECT CAST(value AS INTEGER) FROM kv WHERE key='fetch.failed'") or 0,
        },
        "control": {
            "backfill_done": (q1("SELECT value FROM kv WHERE key='backfill.done'") or "0")
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
    p_f.add_argument("--rate", type=float, default=1.0, help="requests per second (global, across workers)")
    p_f.add_argument("--workers", type=int, default=1, help="parallel fetch workers (threads)")

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
