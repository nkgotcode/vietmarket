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

    # Ensure one proxy allocation per host so both stable DB endpoints are reachable.
    constraint {
      operator = "distinct_hosts"
      value    = "true"
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

  # Route only to the Patroni leader.
  # /leader returns HTTP 200 on the leader and 503 on replicas.
  option httpchk
  http-check connect port 8008
  http-check send meth GET uri /leader ver HTTP/1.1 hdr Host localhost
  http-check expect status 200

  default-server inter 2s fall 3 rise 2 on-marked-down shutdown-sessions

  server optiplex 100.83.150.39:5432 check port 8008
  server epyc     100.103.201.10:5432 check port 8008
CFG
      }

      resources {
        cpu    = 300
        memory = 128
      }
    }
  }
}
