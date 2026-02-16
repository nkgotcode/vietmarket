job "vietmarket-candles-backfill" {
  datacenters = ["dc1"]
  type        = "batch"

  # Every 15 minutes.
  periodic {
    cron             = "*/15 * * * *"
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "primary_backfill_1d" {
    count = 12
    constraint { attribute = "${node.unique.name}" value = "optiplex" }

    task "backfill_1d" {
      driver = "docker"
      config { image = "ghcr.io/nkgotcode/vietmarket-ingest:main" command = "bash" args = ["-lc", "packages/ingest/vn/candles_batch_run.sh"] }
      env {
        CONVEX_URL    = "https://opulent-hummingbird-838.convex.cloud"
        NODE_ID       = "optiplex"
        JOB_NAME      = "candles_backfill_1d"
        SHARD_COUNT   = "12"
        SHARD_INDEX   = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES = "30"
        LEASE_MS      = "300000"
        BATCH_SIZE    = "1"
        TFS           = "1d"
        START_1D      = "2000-01-01"
        CURSOR_DIR    = "/opt/nomad/data/vietmarket-cursors"
      }
      resources { cpu = 250 memory = 256 }
    }
  }

  group "primary_backfill_1h" {
    count = 4
    constraint { attribute = "${node.unique.name}" value = "optiplex" }

    task "backfill_1h" {
      driver = "docker"
      config { image = "ghcr.io/nkgotcode/vietmarket-ingest:main" command = "bash" args = ["-lc", "packages/ingest/vn/candles_batch_run.sh"] }
      env {
        CONVEX_URL    = "https://opulent-hummingbird-838.convex.cloud"
        NODE_ID       = "optiplex"
        JOB_NAME      = "candles_backfill_1h"
        SHARD_COUNT   = "12"
        SHARD_INDEX   = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES = "30"
        LEASE_MS      = "300000"
        BATCH_SIZE    = "1"
        TFS           = "1h"
        INCLUDE_INDICES = "0"
        RUN_TIMEOUT_SEC = "300"
        START_1H      = "2000-01-01"
        CURSOR_DIR    = "/opt/nomad/data/vietmarket-cursors"
      }
      resources { cpu = 250 memory = 256 }
    }
  }

  group "primary_backfill_15m" {
    count = 3
    constraint { attribute = "${node.unique.name}" value = "optiplex" }

    task "backfill_15m" {
      driver = "docker"
      config { image = "ghcr.io/nkgotcode/vietmarket-ingest:main" command = "bash" args = ["-lc", "packages/ingest/vn/candles_batch_run.sh"] }
      env {
        CONVEX_URL    = "https://opulent-hummingbird-838.convex.cloud"
        NODE_ID       = "optiplex"
        JOB_NAME      = "candles_backfill_15m"
        SHARD_COUNT   = "12"
        SHARD_INDEX   = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES = "30"
        LEASE_MS      = "300000"
        BATCH_SIZE    = "1"
        TFS           = "15m"
        INCLUDE_INDICES = "0"
        RUN_TIMEOUT_SEC = "300"
        START_15M     = "2000-01-01"
        CURSOR_DIR    = "/opt/nomad/data/vietmarket-cursors"
      }
      resources { cpu = 250 memory = 256 }
    }
  }

  group "standby_backfill_1d" {
    count = 12
    constraint { attribute = "${node.unique.name}" value = "epyc" }
    task "backfill_1d" {
      driver = "docker"
      config { image = "ghcr.io/nkgotcode/vietmarket-ingest:main" command = "bash" args = ["-lc", "packages/ingest/vn/candles_batch_run.sh"] }
      env {
        CONVEX_URL    = "https://opulent-hummingbird-838.convex.cloud"
        NODE_ID       = "epyc"
        JOB_NAME      = "candles_backfill_1d"
        SHARD_COUNT   = "12"
        SHARD_INDEX   = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES = "30"
        LEASE_MS      = "300000"
        BATCH_SIZE    = "1"
        TFS           = "1d"
        START_1D      = "2000-01-01"
        CURSOR_DIR    = "/opt/nomad/data/vietmarket-cursors"
      }
      resources { cpu = 250 memory = 256 }
    }
  }

  group "standby_backfill_1h" {
    count = 4
    constraint { attribute = "${node.unique.name}" value = "epyc" }
    task "backfill_1h" {
      driver = "docker"
      config { image = "ghcr.io/nkgotcode/vietmarket-ingest:main" command = "bash" args = ["-lc", "packages/ingest/vn/candles_batch_run.sh"] }
      env {
        CONVEX_URL    = "https://opulent-hummingbird-838.convex.cloud"
        NODE_ID       = "epyc"
        JOB_NAME      = "candles_backfill_1h"
        SHARD_COUNT   = "12"
        SHARD_INDEX   = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES = "30"
        LEASE_MS      = "300000"
        BATCH_SIZE    = "1"
        TFS           = "1h"
        INCLUDE_INDICES = "0"
        RUN_TIMEOUT_SEC = "300"
        START_1H      = "2000-01-01"
        CURSOR_DIR    = "/opt/nomad/data/vietmarket-cursors"
      }
      resources { cpu = 250 memory = 256 }
    }
  }

  group "standby_backfill_15m" {
    count = 3
    constraint { attribute = "${node.unique.name}" value = "epyc" }
    task "backfill_15m" {
      driver = "docker"
      config { image = "ghcr.io/nkgotcode/vietmarket-ingest:main" command = "bash" args = ["-lc", "packages/ingest/vn/candles_batch_run.sh"] }
      env {
        CONVEX_URL    = "https://opulent-hummingbird-838.convex.cloud"
        NODE_ID       = "epyc"
        JOB_NAME      = "candles_backfill_15m"
        SHARD_COUNT   = "12"
        SHARD_INDEX   = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES = "30"
        LEASE_MS      = "300000"
        BATCH_SIZE    = "1"
        TFS           = "15m"
        INCLUDE_INDICES = "0"
        RUN_TIMEOUT_SEC = "300"
        START_15M     = "2000-01-01"
        CURSOR_DIR    = "/opt/nomad/data/vietmarket-cursors"
      }
      resources { cpu = 250 memory = 256 }
    }
  }
}
