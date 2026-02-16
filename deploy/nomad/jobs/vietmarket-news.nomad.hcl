job "vietmarket-news" {
  datacenters = ["dc1"]
  type = "service"

  group "macmini" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "macmini"
    }

    task "vietstock_to_convex" {
      driver = "exec"

      config {
        command = "bash"
        args = ["-lc", "cd /Users/lenamkhanh/vietmarket && source .venv/bin/activate && CONVEX_URL=https://opulent-hummingbird-838.convex.cloud python packages/ingest/vietstock/vietstock_to_convex.py"]
      }

      resources {
        cpu    = 500
        memory = 512
      }
    }
  }
}
