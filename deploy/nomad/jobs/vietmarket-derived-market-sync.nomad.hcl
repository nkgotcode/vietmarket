job "vietmarket-derived-market-sync" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    crons            = ["*/30 * * * *"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  group "sync" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "epyc"
    }

    task "derived_sync" {
      driver = "docker"

      config {
        image      = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull = false
        command    = "python3"
        args       = ["packages/ingest/vn/derived_market_sync_pg.py"]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
      }

      resources {
        cpu    = 500
        memory = 1024
      }

      restart {
        attempts = 0
        mode     = "fail"
      }
    }
  }
}
