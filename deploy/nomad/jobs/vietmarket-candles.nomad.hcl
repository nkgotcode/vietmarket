job "vietmarket-candles" {
  datacenters = ["dc1"]
  type = "service"

  # Disable deployments if nodes are down.
  constraint {
    attribute = "${node.class}"
    value     = "linux"
  }

  # Run primary on optiplex; standby on epyc.
  group "primary" {
    count = 12

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    restart {
      attempts = 10
      interval = "30m"
      delay    = "15s"
      mode     = "delay"
    }

    update {
      max_parallel     = 2
      min_healthy_time = "10s"
      healthy_deadline = "5m"
      auto_revert      = true
      canary           = 1
    }

    task "candles_latest" {
      driver = "docker"

      config {
        image = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        command = "bash"
        args = ["-lc", "packages/ingest/vn/candles_batch_run.sh"]
      }

      env {
        CONVEX_URL     = "https://opulent-hummingbird-838.convex.cloud"
        NODE_ID        = "optiplex"
        JOB_NAME       = "candles_latest"
        SHARD_COUNT    = "12"
        SHARD_INDEX    = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES  = "10"
        LEASE_MS       = "300000"

        # job params
        BATCH_SIZE = "8"
        TFS        = "1d,1h,15m"
        INCLUDE_INDICES = "0"
        RUN_TIMEOUT_SEC = "300"

        # rolling windows (start dates are fixed in UTC here; adjust later if you want dynamic)
        START_1D  = "2026-01-01"
        START_1H  = "2026-02-01"
        START_15M = "2026-02-01"

        CURSOR_DIR = "/opt/nomad/data/vietmarket-cursors"
      }

      resources {
        cpu    = 500
        memory = 512
      }
    }

    task "candles_backfill_1d" {
      driver = "docker"
      config {
        image = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        command = "bash"
        args = ["-lc", "packages/ingest/vn/candles_batch_run.sh"]
      }
      env {
        CONVEX_URL     = "https://opulent-hummingbird-838.convex.cloud"
        NODE_ID        = "optiplex"
        JOB_NAME       = "candles_backfill_1d"
        SHARD_COUNT    = "12"
        SHARD_INDEX    = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES  = "30"
        LEASE_MS       = "300000"

        BATCH_SIZE = "1"
        TFS        = "1d"
        START_1D   = "2000-01-01"
        CURSOR_DIR = "/opt/nomad/data/vietmarket-cursors"
      }
      resources {
        cpu    = 500
        memory = 512
      }
    }

    task "candles_backfill_1h" {
      driver = "docker"
      config {
        image = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        command = "bash"
        args = ["-lc", "packages/ingest/vn/candles_batch_run.sh"]
      }
      env {
        CONVEX_URL     = "https://opulent-hummingbird-838.convex.cloud"
        NODE_ID        = "optiplex"
        JOB_NAME       = "candles_backfill_1h"
        SHARD_COUNT    = "12"
        SHARD_INDEX    = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES  = "30"
        LEASE_MS       = "300000"

        BATCH_SIZE = "1"
        TFS        = "1h"
        INCLUDE_INDICES = "0"
        RUN_TIMEOUT_SEC = "300"
        START_1H   = "2000-01-01"
        CURSOR_DIR = "/opt/nomad/data/vietmarket-cursors"
      }
      resources {
        cpu    = 500
        memory = 512
      }
    }

    task "candles_backfill_15m" {
      driver = "docker"
      config {
        image = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        command = "bash"
        args = ["-lc", "packages/ingest/vn/candles_batch_run.sh"]
      }
      env {
        CONVEX_URL     = "https://opulent-hummingbird-838.convex.cloud"
        NODE_ID        = "optiplex"
        JOB_NAME       = "candles_backfill_15m"
        SHARD_COUNT    = "12"
        SHARD_INDEX    = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES  = "30"
        LEASE_MS       = "300000"

        BATCH_SIZE = "1"
        TFS        = "15m"
        INCLUDE_INDICES = "0"
        RUN_TIMEOUT_SEC = "300"
        START_15M  = "2000-01-01"
        CURSOR_DIR = "/opt/nomad/data/vietmarket-cursors"
      }
      resources {
        cpu    = 500
        memory = 512
      }
    }
  }

  group "standby" {
    count = 12
    constraint {
      attribute = "${node.unique.name}"
      value     = "epyc"
    }

    # Standby does the same work but will usually skip due to leases.
    # We keep update/restart settings simple.
    restart { attempts = 10 interval = "30m" delay = "15s" mode = "delay" }

    task "candles_bundle" {
      driver = "docker"
      config {
        image = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        command = "vietmarket-ingest"
        args = ["bundle", "candles"]
      }
      env {
        CONVEX_URL     = "https://opulent-hummingbird-838.convex.cloud"
        NODE_ID        = "epyc"
        SHARD_COUNT    = "12"
        SHARD_INDEX    = "${NOMAD_ALLOC_INDEX}"
        LEASE_MS       = "300000"
        STALE_MINUTES_LATEST = "10"
        STALE_MINUTES_DEEP   = "30"
      }
      resources {
        cpu    = 750
        memory = 768
      }
    }
  }
}
