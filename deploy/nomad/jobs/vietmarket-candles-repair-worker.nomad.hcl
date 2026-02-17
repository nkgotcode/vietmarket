job "vietmarket-candles-repair-worker" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    crons            = ["*/10 * * * *"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "worker" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "worker" {
      driver = "docker"

      config {
        image   = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        command = "bash"
        args    = ["-lc", "python3 packages/ingest/vn/candles_repair_worker_pg.py --limit 5"]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
      }

      resources {
        cpu    = 400
        memory = 512
      }
    }
  }
}
