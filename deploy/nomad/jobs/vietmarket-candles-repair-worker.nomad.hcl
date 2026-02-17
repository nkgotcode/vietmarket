job "vietmarket-candles-repair-worker" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    crons            = ["*/5 * * * *"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "worker-optiplex" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "worker" {
      driver = "docker"

      config {
        image      = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull = true
        command    = "bash"
        args       = ["-lc", "python3 packages/ingest/vn/candles_repair_worker_pg.py --limit 20"]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
      }

      resources {
        cpu    = 500
        memory = 768
      }
    }
  }

  group "worker-epyc" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "epyc"
    }

    task "worker" {
      driver = "docker"

      config {
        image      = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull = true
        command    = "bash"
        args       = ["-lc", "python3 packages/ingest/vn/candles_repair_worker_pg.py --limit 20"]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
      }

      resources {
        cpu    = 500
        memory = 768
      }
    }
  }
}
