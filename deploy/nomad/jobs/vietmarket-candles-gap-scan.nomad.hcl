job "vietmarket-candles-gap-scan" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    crons            = ["*/30 * * * *"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "scan" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "scan" {
      driver = "docker"

      config {
        image   = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        command = "bash"
        args    = ["-lc", "python3 packages/ingest/vn/candles_gap_scan_pg.py --tf 1d --lookback-days 60 --limit-tickers 500"]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
      }

      resources {
        cpu    = 300
        memory = 256
      }
    }
  }
}
