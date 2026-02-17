job "vietmarket-vietstock-migrate-sqlite-to-timescale" {
  datacenters = ["dc1"]
  type        = "batch"

  # One-shot migration job (dispatch manually).
  # Runs on the Mac mini (where the sqlite archive + text files live) and writes into Timescale.

  group "migrate" {
    count = 1

    # Target Mac mini witness node.
    constraint {
      attribute = "${meta.role}"
      value     = "witness"
    }

    task "migrate" {
      driver = "raw_exec"

      config {
        command = "bash"
        args = [
          "-lc",
          "set -euo pipefail; cd /Users/lenamkhanh/vietmarket; python3 -m pip -q install --user psycopg2-binary==2.9.9 >/dev/null 2>&1 || true; PG_URL=\"$PG_URL\" VIETSTOCK_ARCHIVE_DB=\"$VIETSTOCK_ARCHIVE_DB\" TEXT_MAX_CHARS=\"$TEXT_MAX_CHARS\" python3 packages/ingest/vietstock/migrate_vietstock_sqlite_to_timescale.py"
        ]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"

        # Archive sqlite lives on the Mac mini
        VIETSTOCK_ARCHIVE_DB = "/Users/lenamkhanh/vietstock-archive-data/archive.sqlite"

        # Limit text size per article (safety)
        TEXT_MAX_CHARS = "200000"
      }

      resources {
        cpu    = 500
        memory = 1024
      }
    }
  }
}
