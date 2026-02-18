job "vietmarket-fi-latest-sync-timescale" {
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

  group "sync" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "fi_latest_sync" {
      driver = "docker"

      config {
        image      = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull = true

        entrypoint = ["python3", "/app/packages/ingest/simplize/fi_latest_sync_pg.py"]

        # Mount local Simplize SQLite DB into container
        volumes = [
          "/home/itsnk/vietmarket/data/simplize:/app/data/simplize:ro",
        ]
      }

      env {
        PG_URL      = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
        SIMPLIZE_DB = "/app/data/simplize/simplize.db"
        PERIOD      = "Q"
      }

      resources {
        cpu    = 200
        memory = 256
      }
    }
  }
}
