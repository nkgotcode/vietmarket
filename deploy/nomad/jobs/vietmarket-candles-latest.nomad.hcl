job "vietmarket-candles-latest" {
  datacenters = ["dc1"]
  type        = "batch"

  # Every 5 minutes.
  periodic {
    cron             = "*/5 * * * *"
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  # Only run on Linux clients.
  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "primary_latest" {
    count = 10

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "latest" {
      driver = "docker"

      config {
        image   = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        command = "bash"
        args    = ["-lc", "packages/ingest/vn/candles_batch_run.sh"]
      }

      env {
        CONVEX_URL    = "https://opulent-hummingbird-838.convex.cloud"
        NODE_ID       = "optiplex"
        JOB_NAME      = "candles_latest"
        SHARD_COUNT   = "10"
        SHARD_INDEX   = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES = "10"
        LEASE_MS      = "300000"

        BATCH_SIZE      = "4"
        TFS             = "1d,1h,15m"
        INCLUDE_INDICES = "0"
        RUN_TIMEOUT_SEC = "300"

        START_1D  = "2026-01-01"
        START_1H  = "2026-02-01"
        START_15M = "2026-02-01"

        CURSOR_DIR = "/opt/nomad/data/vietmarket-cursors"
      }

      resources {
        cpu    = 250
        memory = 256
      }
    }
  }

  group "standby_latest" {
    count = 10

    constraint {
      attribute = "${node.unique.name}"
      value     = "epyc"
    }

    task "latest" {
      driver = "docker"

      config {
        image   = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        command = "bash"
        args    = ["-lc", "packages/ingest/vn/candles_batch_run.sh"]
      }

      env {
        CONVEX_URL    = "https://opulent-hummingbird-838.convex.cloud"
        NODE_ID       = "epyc"
        JOB_NAME      = "candles_latest"
        SHARD_COUNT   = "10"
        SHARD_INDEX   = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES = "10"
        LEASE_MS      = "300000"

        BATCH_SIZE      = "4"
        TFS             = "1d,1h,15m"
        INCLUDE_INDICES = "0"
        RUN_TIMEOUT_SEC = "300"

        START_1D  = "2026-01-01"
        START_1H  = "2026-02-01"
        START_15M = "2026-02-01"

        CURSOR_DIR = "/opt/nomad/data/vietmarket-cursors"
      }

      resources {
        cpu    = 250
        memory = 256
      }
    }
  }
}
