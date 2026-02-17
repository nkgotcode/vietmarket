job "vietmarket-candles-timescale-backfill-1h" {
  datacenters = ["dc1"]
  type        = "batch"

  periodic {
    crons            = ["*/10 * * * *"]
    prohibit_overlap = true
    time_zone        = "Asia/Ho_Chi_Minh"
  }

  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "primary_backfill_1h" {
    count = 6

    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "backfill_1h" {
      driver = "docker"

      config {
        image      = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull = true

        volumes = [
          "/opt/nomad/data/vietmarket-cursors:/opt/nomad/data/vietmarket-cursors",
        ]
      }

      env {
        PG_URL     = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
        CONVEX_URL = ""

        NODE_ID       = "optiplex"
        JOB_NAME      = "candles_backfill_1h"
        SHARD_COUNT   = "12"
        SHARD_INDEX   = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES = "30"
        LEASE_MS      = "300000"

        INCLUDE_INDICES = "0"

        BATCH_SIZE = "1"
        TFS        = "1h"
        START_1H   = "2000-01-01"

        RUN_TIMEOUT_SEC = "1800"

        CURSOR_DIR = "/opt/nomad/data/vietmarket-cursors"
      }

      resources {
        cpu    = 300
        memory = 512
      }
    }
  }

  group "standby_backfill_1h" {
    count = 6

    constraint {
      attribute = "${node.unique.name}"
      value     = "epyc"
    }

    task "backfill_1h" {
      driver = "docker"

      config {
        image      = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull = true

        volumes = [
          "/opt/nomad/data/vietmarket-cursors:/opt/nomad/data/vietmarket-cursors",
        ]
      }

      env {
        PG_URL     = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
        CONVEX_URL = ""

        NODE_ID       = "epyc"
        JOB_NAME      = "candles_backfill_1h"
        SHARD_COUNT   = "12"
        SHARD_INDEX   = "${NOMAD_ALLOC_INDEX}"
        STALE_MINUTES = "30"
        LEASE_MS      = "300000"

        INCLUDE_INDICES = "0"

        BATCH_SIZE = "1"
        TFS        = "1h"
        START_1H   = "2000-01-01"

        RUN_TIMEOUT_SEC = "1800"

        CURSOR_DIR = "/opt/nomad/data/vietmarket-cursors"
      }

      resources {
        cpu    = 300
        memory = 512
      }
    }
  }
}
