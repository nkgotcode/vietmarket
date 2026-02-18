job "vietmarket-corporate-actions-ingest" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    crons            = ["15 */6 * * *"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "ingest" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "events_to_timescale" {
      driver = "docker"

      config {
        image      = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull = true
        entrypoint = ["python3", "/app/packages/ingest/vietstock/vietstock_events_to_timescale.py"]
      }

      env {
        PG_URL       = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
        MAX_PAGES    = "10"
        START_PAGE   = "1"
        PAGE_RETRIES = "5"
      }

      resources {
        cpu    = 300
        memory = 512
      }
    }
  }
}
