job "vietmarket-news" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    crons            = ["*/5 * * * *"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  group "macmini" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "macmini"
    }

    task "vietstock_to_convex" {
      driver = "raw_exec"

      config {
        command = "bash"
        args    = ["-lc", "cd /Users/lenamkhanh/vietmarket && source .venv/bin/activate && CONVEX_URL=https://opulent-hummingbird-838.convex.cloud python3 packages/ingest/vietstock/vietstock_to_convex.py --db /Users/lenamkhanh/vietstock-archive-data/archive.sqlite --limit 100"]
      }

      resources {
        cpu    = 500
        memory = 512
      }
    }
  }
}
