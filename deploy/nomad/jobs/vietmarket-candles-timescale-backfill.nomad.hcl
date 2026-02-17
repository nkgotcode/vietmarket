job "vietmarket-candles-timescale-backfill" {
  datacenters = ["dc1"]
  type        = "batch"

  # Every 15 minutes (slow & steady).
  periodic {
    crons             = ["*/15 * * * *"]
    prohibit_overlap  = true
    time_zone         = "Asia/Ho_Chi_Minh"
  }

  # Only run on Linux clients.
  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  # ============================
  # 1D FULL-HISTORY BACKFILL ONLY
  # ============================

  group "primary_backfill_1d" {
    count = 12

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "backfill_1d" {
      driver = "docker"

      config {
        image = "ghcr.io/nkgotcode/vietmarket-ingest:main"
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
        CONVEX_URL = ""

        NODE_ID       = "optiplex"
        JOB_NAME      = "candles_backfill_1d"
        SHARD_COUNT   = "12"
        SHARD_INDEX   = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES = "30"
        LEASE_MS      = "300000"

        BATCH_SIZE = "1"
        TFS        = "1d"
        START_1D   = "2000-01-01"

        CURSOR_DIR = "/opt/nomad/data/vietmarket-cursors"
      }

      resources {
        cpu    = 250
        memory = 256
      }
    }
  }

  group "standby_backfill_1d" {
    count = 12

    constraint {
      attribute = "${node.unique.name}"
      value     = "epyc"
    }

    task "backfill_1d" {
      driver = "docker"

      config {
        image = "ghcr.io/nkgotcode/vietmarket-ingest:main"
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
        CONVEX_URL = ""

        NODE_ID       = "epyc"
        JOB_NAME      = "candles_backfill_1d"
        SHARD_COUNT   = "12"
        SHARD_INDEX   = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES = "30"
        LEASE_MS      = "300000"

        BATCH_SIZE = "1"
        TFS        = "1d"
        START_1D   = "2000-01-01"

        CURSOR_DIR = "/opt/nomad/data/vietmarket-cursors"
      }

      resources {
        cpu    = 250
        memory = 256
      }
    }
  }
}
