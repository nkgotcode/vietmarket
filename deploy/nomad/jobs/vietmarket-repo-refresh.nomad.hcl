job "vietmarket-repo-refresh" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    # Run 5 minutes before symbols-sync (which runs at minute 15)
    crons            = ["10 */6 * * *"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "refresh" {
    count = 1

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "refresh" {
      driver = "raw_exec"

      config {
        command = "bash"
        args = [
          "-lc",
          "set -euo pipefail; cd /home/itsnk/vietmarket; git pull --ff-only; node scripts/simplize_universe_refresh.mjs --out-file data/simplize/universe.latest.json"
        ]
      }

      resources {
        cpu    = 200
        memory = 256
      }
    }
  }
}
