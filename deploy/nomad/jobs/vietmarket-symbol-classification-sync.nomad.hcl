job "vietmarket-symbol-classification-sync" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    # Runs after vietmarket-symbols-sync (minute 15) so newly synced symbols
    # can receive canonical sector/industry classification automatically.
    crons            = ["25 */6 * * *"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "classification" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "symbol_classification_sync" {
      driver = "docker"

      config {
        image      = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull = false
        command    = "python3"
        args       = ["/src/packages/ingest/vn/symbol_classification_sync.py"]
        volumes    = ["/home/itsnk/vietmarket:/src"]
      }

      env {
        PG_URL                 = "postgres://vietmarket:***@100.83.150.39:5433/vietmarket?sslmode=disable"
        ONLY_MISSING           = "1"
        CLASSIFICATION_WORKERS = "6"
        CLASSIFICATION_SLEEP   = "0.05"
      }

      resources {
        cpu    = 700
        memory = 768
      }

      restart {
        attempts = 0
        mode     = "fail"
      }
    }
  }
}
