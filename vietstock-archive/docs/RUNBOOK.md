# Runbook — Vietstock Archive

## Goals
- Keep a local, durable archive of Vietstock articles (HTML + cleaned text) and metadata.
- Provide measurable progress for backfill ("how far back did we go?").

## Commands

All commands run via:

```bash
/Users/lenamkhanh/.clawdbot/bin/vietstock-archive <command> [args]
```

### init
Creates/updates DB schema and seeds category listing URLs derived from the RSS list.

```bash
vietstock-archive init
```

### rss
Parses cached RSS feed XML from the local relay and enqueues article links.

```bash
vietstock-archive rss --limit 500
```

### backfill
Crawls category listing pages using pagination and enqueues discovered article links.

```bash
vietstock-archive backfill --budget-pages 200 --rate 1
```

- `--budget-pages`: max listing pages to fetch per run (controls speed and site load).
- `--rate`: requests/second (default 1).

#### Automatic stop
Backfill runs until it appears to have exhausted historical pages.

Implementation details:
- Vietstock category pages render listings via JS; we use the server endpoint:
  - `/StartPage/ChannelContentPage?channelID=<id>&page=<n>`
- For each seed/channel, if we see **3 consecutive pages with 0 new article URLs**, we mark that seed `done=1`.
- Once **all** enabled seeds are done, we set:
  - `kv.backfill.done = 1`

You can force backfill to resume by setting `kv.backfill.done=0`.

### fetch
Fetches pending article URLs, stores HTML + cleaned text.

```bash
vietstock-archive fetch --limit 50 --rate 1
```

### status
Shows progress and the oldest/newest `published_at` currently present.

```bash
vietstock-archive status
vietstock-archive status --json
```

## Storage
- SQLite DB: `/Users/lenamkhanh/vietstock-archive-data/archive.sqlite` (configurable via `VIETSTOCK_ARCHIVE_ROOT`)
- HTML store: `/Users/lenamkhanh/vietstock-archive-data/html/YYYY/MM/<sha256>.html`
- Text store: `/Users/lenamkhanh/vietstock-archive-data/text/YYYY/MM/<sha256>.txt`

## Progress definition
- Oldest "seen" date is tracked as `MIN(articles.published_at)`.
- Backfill progress per category is tracked in `crawl_state.next_page`.

## Extraction + Playwright fallback
- We use a Vietstock-specific extractor that prefers paragraphs with classes:
  - `pTitle`, `pHead`, `pBody`
  - then falls back to generic tag-stripping.
- If fetch fails (403/blocked/etc) **or** extracted text is too short (< ~80 words), we attempt a **Playwright (Node) fallback** to fetch rendered HTML.

### Playwright requirement
The fallback requires the Node package `playwright` to be installed and resolvable by `node`:

```bash
npm i playwright
```

(If Playwright is not installed, the fetcher will still work for most pages using the browser-like User-Agent.)

## Known limitations
- Pagination detection is heuristic (searches `page=` links). Some categories may use different paging.
- `published_at` can be inconsistent in site metadata; we prioritize `article:published_time` and visible timestamps and only use `dc.created` when it's not the site default.
