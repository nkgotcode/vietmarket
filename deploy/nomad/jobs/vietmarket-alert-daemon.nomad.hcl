job "vietmarket-alert-daemon" {
  datacenters = ["dc1"]
  type        = "service"

  group "alert-daemon" {
    count = 1

    task "daemon" {
      driver = "docker"

      config {
        image      = "ghcr.io/nkgotcode/vietmarket-ingest:main"
        force_pull = false
        command    = "python3"
        args       = [
          "tools/alerts/run_alert_daemon.py",
          "--pg-url", "${PG_URL}",
          "--rules", "config/alerts/rules.v1.yaml",
          "--watchlists", "config/alerts/watchlists.json",
          "--portfolio", "config/alerts/portfolio_symbols_current.json",
          "--channels", "config/alerts/channels.json",
          "--state", "runtime/alerts/state.json",
          "--firelog", "runtime/alerts/fires.jsonl"
        ]
      }

      env {
        PG_URL = "postgres://vietmarket:vietmarket@100.83.150.39:5433/vietmarket?sslmode=disable"
      }

      resources {
        cpu    = 300
        memory = 512
      }

      restart {
        attempts = 0
        mode     = "delay"
        delay    = "5s"
      }
    }
  }
}
