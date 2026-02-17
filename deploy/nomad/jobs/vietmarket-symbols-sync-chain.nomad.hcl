job "vietmarket-symbols-sync-chain" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    # Hard chain: refresh repo + regenerate universe, then sync symbols.
    crons            = ["15 */6 * * *"]
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

    task "repo_refresh" {
      driver = "raw_exec"

      lifecycle {
        hook    = "prestart"
        sidecar = false
      }

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

    task "symbols_sync" {
      driver = "docker"

      config {
        image      = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull = true
        command    = "bash"
        args       = ["-lc", "python3 packages/ingest/vn/symbols_sync_pg.py"]

        volumes = [
          "/home/itsnk/vietmarket/data/simplize:/app/data/simplize:ro"
        ]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"

        # Use local Simplize universe file (network to VNDIRECT is unreliable)
        SYMBOLS_SOURCE = "file"
        SYMBOLS_FILE   = "/app/data/simplize/universe.latest.json"
      }

      resources {
        cpu    = 300
        memory = 384
      }
    }
  }
}
