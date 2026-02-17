job "vietmarket-vietstock-timescale" {
  datacenters = ["dc1"]
  type        = "batch"

  # Hourly
  periodic {
    crons            = ["0 * * * *"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "primary" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "rss" {
      driver = "docker"

      config {
        image   = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        command = "bash"
        args    = ["-lc", "python3 packages/ingest/vietstock/vietstock_rss_to_timescale.py"]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
        CONVEX_URL = ""

        # TODO: set real Vietstock RSS feeds (space-separated)
        # Example:
        # VIETSTOCK_RSS_FEEDS = "https://vietstock.vn/rss/tin-moi-nhat.rss https://vietstock.vn/rss/chung-khoan.rss"
        VIETSTOCK_RSS_FEEDS = ""

        LIMIT = "30"
        SLEEP = "0.2"
      }

      resources {
        cpu    = 300
        memory = 256
      }
    }
  }
}
