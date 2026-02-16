job "clickhouse" {
  datacenters = ["dc1"]
  type        = "service"

  constraint {
    attribute = "${node.unique.name}"
    value     = "epyc"
  }

  # Tailnet-only exposure.
  group "ch" {
    network {
      mode = "host"

      port "http" {
        static = 8123
      }
      port "native" {
        static = 9000
      }
    }

    task "clickhouse" {
      driver = "docker"

      config {
        image = "clickhouse/clickhouse-server:24.12"
        network_mode = "host"

        volumes = [
          "/opt/clickhouse:/var/lib/clickhouse",
          "/opt/clickhouse-logs:/var/log/clickhouse-server",
        ]

        # Bind to tailscale IP only.
        args = [
          "--http_port=8123",
          "--tcp_port=9000",
          "--listen_host=100.103.201.10",
        ]
      }

      env {
        CLICKHOUSE_DB = "vietmarket"
      }

      resources {
        cpu    = 1500
        memory = 2048
      }

      service {
        name = "clickhouse"
        port = "http"
      }
    }
  }
}
