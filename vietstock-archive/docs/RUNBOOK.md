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
- SQLite DB: `~/.clawdbot/vietstock-archive/archive.sqlite`
- HTML store: `~/.clawdbot/vietstock-archive/html/YYYY/MM/<sha256>.html`
- Text store: `~/.clawdbot/vietstock-archive/text/YYYY/MM/<sha256>.txt`

## Progress definition
- Oldest "seen" date is tracked as `MIN(articles.published_at)`.
- Backfill progress per category is tracked in `crawl_state.next_page`.

## Known limitations
- Pagination detection is heuristic (searches `page=` links). Some categories may use different paging.
- Extraction is currently basic (tag stripping); can be upgraded later (Playwright + better DOM extraction).
- `published_at` may be missing for some pages; we fall back to metadata when present.
