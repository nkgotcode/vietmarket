job "vietmarket-supervisor-daily-cycle" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    crons            = ["35 15 * * 1-5"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "supervisor" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "daily_cycle" {
      driver = "docker"

      config {
        image      = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull = false
        command    = "bash"
        args       = ["-lc", "cd /src && python3 packages/supervisor/orchestration/run_supervisor_cycle.py --mode daily --strict-health-gate"]
        volumes    = ["/home/itsnk/vietmarket:/src"]
      }

      env {
        PG_URL             = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
        TELEGRAM_BOT_TOKEN = "8762113348:AAGbuyAtjKFGG9QI346ZEkK5Z2YYYrAFod0"
        TELEGRAM_CHAT_ID   = "1134732327"
      }

      resources {
        cpu    = 1000
        memory = 1536
      }

      restart {
        attempts = 0
        mode     = "fail"
      }
    }
  }
}
