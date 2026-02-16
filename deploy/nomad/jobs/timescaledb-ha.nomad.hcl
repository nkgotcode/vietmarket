job "timescaledb-ha" {
  datacenters = ["dc1"]
  type        = "service"

  # 2-node TimescaleDB HA managed by Patroni, using etcd as DCS.
  # Nodes: optiplex + epyc
  # Patroni REST API: 8008
  # Postgres: 5432

  group "db" {
    count = 2

    # Place exactly one allocation per eligible node.
    constraint {
      attribute = "${node.unique.name}"
      operator  = "regexp"
      value     = "^(optiplex|epyc)$"
    }

    spread {
      attribute = "${node.unique.name}"
    }

    network {
      mode = "host"
      port "pg"      { static = 5432 }
      port "patroni" { static = 8008 }
    }

    task "db" {
      driver = "docker"

      config {
        image        = "timescale/timescaledb-ha:pg16"
        network_mode = "host"

        # NOTE: these host paths must exist on each node.
        # optiplex: /opt/timescaledb-ha
        # epyc:     /opt/timescaledb-ha
        volumes = [
          "/opt/timescaledb-ha:/home/postgres/pgdata",
        ]
      }

      env {
        # Patroni
        PATRONI_SCOPE = "vietmarket"

        # etcd DCS
        PATRONI_ETCD_HOSTS = "100.83.150.39:2379,100.103.201.10:2379,100.100.5.40:2379"

        # Patroni REST API
        PATRONI_RESTAPI_LISTEN          = "0.0.0.0:8008"
        # connect address must be unique per node, so we set it via template below.

        # Postgres
        PATRONI_POSTGRESQL_LISTEN = "0.0.0.0:5432"
        # connect address set via template below.

        # Credentials
        PATRONI_SUPERUSER_USERNAME   = "postgres"
        PATRONI_SUPERUSER_PASSWORD   = "postgres"
        PATRONI_REPLICATION_USERNAME = "replicator"
        PATRONI_REPLICATION_PASSWORD = "replicator"

        # App DB/user
        POSTGRES_DB       = "vietmarket"
        POSTGRES_USER     = "vietmarket"
        POSTGRES_PASSWORD = "vietmarket"

        # Help timescaledb-tune pick sane defaults
        TS_TUNE_MEMORY   = "2GB"
        TS_TUNE_NUM_CPUS = "2"
      }

      # Inject per-node addresses.
      template {
        destination = "local/patroni-env"
        env         = true
        data        = <<EOH
PATRONI_NAME={{ env "node.unique.name" }}
PATRONI_RESTAPI_CONNECT_ADDRESS={{ if eq (env "node.unique.name") "optiplex" }}100.83.150.39{{ else }}100.103.201.10{{ end }}:8008
PATRONI_POSTGRESQL_CONNECT_ADDRESS={{ if eq (env "node.unique.name") "optiplex" }}100.83.150.39{{ else }}100.103.201.10{{ end }}:5432
EOH
      }

      resources {
        cpu    = 1500
        memory = 3072
      }
    }
  }
}
