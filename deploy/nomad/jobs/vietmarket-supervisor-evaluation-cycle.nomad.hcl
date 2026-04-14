job "vietmarket-supervisor-evaluation-cycle" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    crons            = ["50 15 * * 1-5"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "evaluation" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "evaluation_cycle" {
      driver = "docker"

      config {
        image      = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull = false
        command    = "bash"
        args       = ["-lc", "cd /src && python3 packages/supervisor/reports/run_evaluation_cycle.py"]
        volumes    = ["/home/itsnk/vietmarket:/src"]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
      }

      resources {
        cpu    = 700
        memory = 1024
      }

      restart {
        attempts = 0
        mode     = "fail"
      }
    }
  }
}
