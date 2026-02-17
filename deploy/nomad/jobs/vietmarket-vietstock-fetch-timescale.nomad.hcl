job "vietmarket-vietstock-fetch-timescale" {
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

  group "fetch" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "fetch" {
      driver = "docker"

      config {
        image   = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        command = "bash"
        args    = ["-lc", "python3 packages/ingest/vietstock/vietstock_fetch_timescale.py"]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"

        LIMIT = "200"
        RATE  = "3"
      }

      resources {
        cpu    = 500
        memory = 768
      }
    }
  }
}
