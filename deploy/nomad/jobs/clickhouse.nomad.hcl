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
        user = "0:0"

        volumes = [
          "/opt/clickhouse:/var/lib/clickhouse",
          "/opt/clickhouse-logs:/var/log/clickhouse-server",
        ]

        # Listen on host; restrict access at network level (Tailscale + firewall).
        args = [
          "--http_port=8123",
          "--tcp_port=9000"
        ]
      }

      env {
        CLICKHOUSE_DB       = "vietmarket"
        CLICKHOUSE_USER     = "vietmarket"
        CLICKHOUSE_PASSWORD = "vietmarket"
      }

      resources {
        cpu    = 1500
        memory = 2048
      }

      # service registration disabled (avoids Consul requirement)
    }
  }
}
