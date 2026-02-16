job "timescaledb" {
  datacenters = ["dc1"]
  type        = "service"

  # Pin to EPYC
  constraint {
    attribute = "${node.unique.name}"
    value     = "epyc"
  }

  group "db" {
    network {
      mode = "host"

      port "pg" {
        static = 5432
      }
    }

    task "timescaledb" {
      driver = "docker"

      config {
        image        = "timescale/timescaledb:2.14.2-pg16"
        network_mode = "host"

        volumes = [
          "/opt/timescaledb:/var/lib/postgresql/data",
        ]
      }

      env {
        POSTGRES_DB       = "vietmarket"
        POSTGRES_USER     = "vietmarket"
        POSTGRES_PASSWORD = "vietmarket"
        # Recommended for reliability on small VPS-class machines
        # (we can tune later)
        TS_TUNE_MEMORY    = "2GB"
        TS_TUNE_NUM_CPUS  = "2"
      }

      resources {
        cpu    = 1200
        memory = 2048
      }
    }
  }
}
