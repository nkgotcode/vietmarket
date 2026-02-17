job "vietmarket-vietstock-migrate-sqlite-to-timescale" {
  datacenters = ["dc1"]
  type        = "batch"

  # One-shot migration job (dispatch manually).
  # Copies Vietstock archive sqlite metadata + text files into Timescale.

  constraint {
    attribute = "${attr.kernel.name}"
    value     = "linux"
  }

  group "migrate" {
    count = 1

    # Run on Optiplex (has access to the archive path via tailnet/host filesystem assumptions).
    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    task "migrate" {
      driver = "docker"

      config {
        image   = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        command = "bash"
        args    = ["-lc", "python3 packages/ingest/vietstock/migrate_vietstock_sqlite_to_timescale.py"]

        volumes = [
          "/Users/lenamkhanh/vietstock-archive-data:/vietstock-archive-data:ro",
        ]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"

        # Path inside the container (mounted read-only)
        VIETSTOCK_ARCHIVE_DB = "/vietstock-archive-data/archive.sqlite"

        # Limit text size per article (safety)
        TEXT_MAX_CHARS = "200000"
      }

      resources {
        cpu    = 500
        memory = 1024
      }
    }
  }
}
