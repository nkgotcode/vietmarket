job "vietmarket-fi-latest-sync-timescale" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    crons            = ["*/30 * * * *"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  group "sync" {
    count = 1

    # Run on Mac mini witness where simplize.db lives.
    constraint {
      attribute = "${meta.role}"
      value     = "witness"
    }

    task "fi_latest_sync" {
      driver = "raw_exec"

      config {
        command = "bash"
        args = [
          "-lc",
          "set -euo pipefail; cd /Users/lenamkhanh/vietmarket; python3 -m pip -q install --user psycopg2-binary==2.9.9 >/dev/null 2>&1 || true; PG_URL=\"$PG_URL\" SIMPLIZE_DB=\"$SIMPLIZE_DB\" PERIOD=\"$PERIOD\" python3 packages/ingest/simplize/fi_latest_sync_pg.py",
        ]
      }

      env {
        PG_URL      = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
        SIMPLIZE_DB = "/Users/lenamkhanh/vietmarket/data/simplize/simplize.db"
        PERIOD      = "Q"
      }

      resources {
        cpu    = 300
        memory = 512
      }
    }
  }
}
