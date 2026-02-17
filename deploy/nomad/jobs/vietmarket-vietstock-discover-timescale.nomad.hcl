job "vietmarket-vietstock-discover-timescale" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    crons            = ["0 * * * *"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "discover" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "discover" {
      driver = "docker"

      config {
        image       = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull  = true
        command     = "bash"
        args        = ["-lc", "python3 packages/ingest/vietstock/vietstock_discover_timescale.py"]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"

        RSS_LIMIT = "500"
        BACKFILL_BUDGET_PAGES = "200"
        RATE = "1"
        NO_NEW_PAGES_STOP = "3"
      }

      resources {
        cpu    = 400
        memory = 512
      }
    }
  }
}
