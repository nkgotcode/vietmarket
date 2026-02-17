job "vietmarket-symbols-sync" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
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

    task "sync" {
      driver = "docker"

      config {
        image      = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull = true
        command    = "bash"
        args       = ["-lc", "python3 packages/ingest/vn/symbols_sync_pg.py"]
        volumes    = ["/home/itsnk/vietmarket/data/simplize:/app/data/simplize:ro"]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"

        # Use local Simplize universe file for now (VNDIRECT 443 is timing out from runners)
        SYMBOLS_SOURCE  = "file"
        SYMBOLS_FILE    = "/app/data/simplize/universe.latest.json"
        VN_STOCK_FLOORS = "HOSE,HNX,UPCOM"
        PAGE_SIZE       = "500"
        MAX_PAGES       = "200"
      }

      resources {
        cpu    = 300
        memory = 384
      }
    }
  }
}
