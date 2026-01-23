# Vietstock Archive (local-first)

This folder documents and implements a local-first pipeline to:

1. Track Vietstock RSS feeds (via a local relay to avoid UA blocks)
2. Ingest RSS items into a local queue
3. Backfill older history by crawling category listing pages
4. Fetch full article HTML and extract cleaned text
5. Store everything locally for later Q&A, sentiment, and embeddings

## Status
- RSS relay: **enabled** (served locally at `http://127.0.0.1:18999/`, refreshed every 15m)
- Archive DB + crawler: **in progress** (this folder)

## Components
- Database: `~/.clawdbot/vietstock-archive/archive.sqlite`
- Content store:
  - HTML: `~/.clawdbot/vietstock-archive/html/YYYY/MM/<sha256>.html`
  - Text: `~/.clawdbot/vietstock-archive/text/YYYY/MM/<sha256>.txt`
- Scripts (source): `clawd/vietstock-archive/scripts/`
- Installed runner (symlink/copy): `~/.clawdbot/bin/vietstock-archive`

## Quickstart
Run once manually:

```bash
/Users/lenamkhanh/.clawdbot/bin/vietstock-archive init
/Users/lenamkhanh/.clawdbot/bin/vietstock-archive rss --limit 500
/Users/lenamkhanh/.clawdbot/bin/vietstock-archive backfill --budget-pages 100
/Users/lenamkhanh/.clawdbot/bin/vietstock-archive fetch --limit 50 --rate 1
```

Check progress:

```bash
/Users/lenamkhanh/.clawdbot/bin/vietstock-archive status
```

## Progress tracking ("how far back")
We persist:
- oldest `published_at` seen per source
- most recent backfill page crawled per category seed

Use:

```bash
/Users/lenamkhanh/.clawdbot/bin/vietstock-archive status --json
```

## Notes
- Backfill is best-effort; Vietstock history is not exposed fully through RSS.
- Crawling is rate-limited (default 1 req/sec) to be gentle.
