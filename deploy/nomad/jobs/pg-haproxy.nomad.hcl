job "pg-haproxy" {
  datacenters = ["dc1"]
  type        = "service"

  # HAProxy that routes to the current Patroni leader.
  # Runs on optiplex + epyc, listens on 5433 (so it doesn't clash with local PG 5432).

  group "proxy" {
    count = 2

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
      port "pg" { static = 5433 }
    }

    task "haproxy" {
      driver = "docker"

      config {
        image        = "haproxy:2.9"
        network_mode = "host"
        args         = ["-f", "/local/haproxy.cfg", "-db"]
      }

      template {
        destination = "local/haproxy.cfg"
        data = <<CFG
global
  maxconn 4096

defaults
  log global
  mode tcp
  timeout connect 5s
  timeout client  60s
  timeout server  60s

frontend pg_rw
  bind 0.0.0.0:5433
  default_backend patroni_rw

backend patroni_rw
  mode tcp
  option tcp-check

  # Pure TCP checks on Postgres port.
  # (Avoid depending on Patroni REST API reachability on 8008.)
  default-server inter 2s fall 3 rise 2 on-marked-down shutdown-sessions

  server optiplex 100.83.150.39:5432 check
  server epyc     100.103.201.10:5432 check
CFG
      }

      resources {
        cpu    = 300
        memory = 128
      }
    }
  }
}
