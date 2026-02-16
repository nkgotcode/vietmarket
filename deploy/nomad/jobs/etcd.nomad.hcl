job "etcd" {
  datacenters = ["dc1"]
  type        = "service"

  # 3-node etcd for Patroni DCS (Optiplex + EPYC + Mac mini witness)
  # Client: 2379, Peer: 2380

  group "optiplex" {
    constraint {
      attribute = "${node.unique.name}"
      value     = "optiplex"
    }

    network {
      mode = "host"
      port "client" { static = 2379 }
      port "peer"   { static = 2380 }
    }

    task "etcd" {
      driver = "docker"

      config {
        image        = "quay.io/coreos/etcd:v3.5.16"
        network_mode = "host"

        volumes = [
          "/opt/etcd:/etcd-data",
        ]

        args = [
          "etcd",
          "--name=etcd-optiplex",
          "--data-dir=/etcd-data",
          "--listen-client-urls=http://0.0.0.0:2379",
          "--advertise-client-urls=http://100.83.150.39:2379",
          "--listen-peer-urls=http://0.0.0.0:2380",
          "--initial-advertise-peer-urls=http://100.83.150.39:2380",
          "--initial-cluster=etcd-optiplex=http://100.83.150.39:2380,etcd-epyc=http://100.103.201.10:2380,etcd-macmini=http://100.100.5.40:2380",
          "--initial-cluster-state=new",
          "--initial-cluster-token=vietmarket-etcd",
          "--auto-compaction-retention=1",
          "--quota-backend-bytes=536870912"
        ]
      }

      resources {
        cpu    = 300
        memory = 256
      }
    }
  }

  group "epyc" {
    constraint {
      attribute = "${node.unique.name}"
      value     = "epyc"
    }

    network {
      mode = "host"
      port "client" { static = 2379 }
      port "peer"   { static = 2380 }
    }

    task "etcd" {
      driver = "docker"

      config {
        image        = "quay.io/coreos/etcd:v3.5.16"
        network_mode = "host"

        volumes = [
          "/opt/etcd:/etcd-data",
        ]

        args = [
          "etcd",
          "--name=etcd-epyc",
          "--data-dir=/etcd-data",
          "--listen-client-urls=http://0.0.0.0:2379",
          "--advertise-client-urls=http://100.103.201.10:2379",
          "--listen-peer-urls=http://0.0.0.0:2380",
          "--initial-advertise-peer-urls=http://100.103.201.10:2380",
          "--initial-cluster=etcd-optiplex=http://100.83.150.39:2380,etcd-epyc=http://100.103.201.10:2380,etcd-macmini=http://100.100.5.40:2380",
          "--initial-cluster-state=new",
          "--initial-cluster-token=vietmarket-etcd",
          "--auto-compaction-retention=1",
          "--quota-backend-bytes=536870912"
        ]
      }

      resources {
        cpu    = 300
        memory = 256
      }
    }
  }

  group "macmini" {
    # Prefer meta-role constraint if present; fall back to node name constraint.
    constraint {
      attribute = "${meta.role}"
      value     = "witness"
    }

    network {
      mode = "host"
      port "client" { static = 2379 }
      port "peer"   { static = 2380 }
    }

    task "etcd" {
      driver = "raw_exec"

      env {
        ETCD_UNSUPPORTED_ARCH = "arm64"
      }

      config {
        command = "/opt/homebrew/opt/etcd/bin/etcd"
        args = [
          "--name=etcd-macmini",
          "--data-dir=/Users/lenamkhanh/Library/Application Support/etcd",
          "--listen-client-urls=http://0.0.0.0:2379",
          "--advertise-client-urls=http://100.100.5.40:2379",
          "--listen-peer-urls=http://0.0.0.0:2380",
          "--initial-advertise-peer-urls=http://100.100.5.40:2380",
          "--initial-cluster=etcd-optiplex=http://100.83.150.39:2380,etcd-epyc=http://100.103.201.10:2380,etcd-macmini=http://100.100.5.40:2380",
          "--initial-cluster-state=new",
          "--initial-cluster-token=vietmarket-etcd",
          "--auto-compaction-retention=1",
          "--quota-backend-bytes=536870912"
        ]
      }

      resources {
        cpu    = 200
        memory = 256
      }
    }
  }
}
