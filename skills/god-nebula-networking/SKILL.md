---
name: god-nebula-networking
description: "God-level Nebula overlay networking mastery. Covers Nebula architecture (lighthouse nodes, relay nodes, certificate authority), certificate generation and management, firewall rules, network topology design, unsafe routes for subnet routing, DNS configuration, mobile device setup, performance tuning, and integration with existing infrastructure. Nebula is Slack's open-source overlay network — a simpler, faster alternative to traditional VPNs. Never fabricate Nebula config fields — verify against nebula.defined.net/docs."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Nebula Overlay Networking

## Anti-Hallucination Rules

- NEVER invent Nebula configuration fields — verify against the official Nebula docs and example config.
- NEVER confuse Nebula with WireGuard or Tailscale — they use different protocols and architectures.
- NEVER fabricate cipher suites — Nebula uses Noise protocol with Curve25519, ChaCha20-Poly1305, and BLAKE2s.
- ALWAYS specify Nebula version when discussing features — the config format has evolved across versions.

---

## 1. Architecture

```
Nebula Overlay Network:
  ┌─────────────────────────────────────────────┐
  │            Nebula Certificate Authority      │
  │  (offline CA — signs node certificates)      │
  └──────────────────┬──────────────────────────┘
                     │ signs certs
  ┌──────────────────▼──────────────────────────┐
  │              Lighthouse Node(s)              │
  │  (publicly reachable, helps nodes find       │
  │   each other — like a STUN server)           │
  └──────────┬──────────────┬───────────────────┘
             │              │
     ┌───────▼───┐   ┌─────▼─────┐
     │  Node A   │   │  Node B   │
     │ (behind   │◄──►│ (behind   │
     │  NAT)     │   │  NAT)     │
     └───────────┘   └───────────┘
  Direct peer-to-peer tunnel (UDP, encrypted)
  Punches through NAT when possible
  Falls back to relay via lighthouse when not
```

---

## 2. Certificate Authority Setup

```bash
# Generate CA certificate and key (DO THIS OFFLINE, KEEP ca.key SAFE)
nebula-cert ca -name "My Organization" -duration 8760h   # 1 year

# Output:
#   ca.crt  — distribute to all nodes
#   ca.key  — KEEP OFFLINE AND SECURE (never on a node)

# Sign a node certificate
nebula-cert sign \
  -name "lighthouse-1" \
  -ip "10.42.0.1/24" \
  -groups "lighthouse,infrastructure" \
  -duration 8760h

# Sign a server node
nebula-cert sign \
  -name "web-server-1" \
  -ip "10.42.0.10/24" \
  -groups "servers,web" \
  -duration 8760h

# Sign a developer laptop
nebula-cert sign \
  -name "alice-laptop" \
  -ip "10.42.1.100/24" \
  -groups "developers,ssh-allowed" \
  -duration 2160h   # 90 days — shorter for user devices

# Verify a certificate
nebula-cert print -path web-server-1.crt
```

**IP addressing strategy:**
```
10.42.0.0/24   — Infrastructure (lighthouses, DNS, monitoring)
10.42.1.0/24   — Developer devices
10.42.2.0/24   — Production servers
10.42.3.0/24   — Staging servers
10.42.4.0/24   — CI/CD runners
```

---

## 3. Configuration

### 3.1 Lighthouse Node Config

```yaml
# config-lighthouse.yaml
pki:
  ca: /etc/nebula/ca.crt
  cert: /etc/nebula/lighthouse-1.crt
  key: /etc/nebula/lighthouse-1.key

static_host_map:
  # Empty for lighthouse — it IS the map

lighthouse:
  am_lighthouse: true
  serve_dns: true           # Serve DNS for Nebula hostnames
  dns:
    host: 0.0.0.0
    port: 53

listen:
  host: 0.0.0.0
  port: 4242

punchy:
  punch: true
  respond: true
  delay: 1s

relay:
  am_relay: true            # Act as relay for nodes that can't punch NAT
  use_relays: false

tun:
  disabled: false
  dev: nebula1
  drop_local_broadcast: false
  drop_multicast: false
  tx_queue: 500
  mtu: 1300

logging:
  level: info
  format: json

firewall:
  conntrack:
    tcp_timeout: 12m
    udp_timeout: 3m
    default_timeout: 10m

  outbound:
    - port: any
      proto: any
      host: any

  inbound:
    - port: any
      proto: icmp
      host: any
    # Allow all Nebula nodes to reach lighthouse
    - port: any
      proto: any
      host: any
```

### 3.2 Regular Node Config

```yaml
# config-node.yaml
pki:
  ca: /etc/nebula/ca.crt
  cert: /etc/nebula/web-server-1.crt
  key: /etc/nebula/web-server-1.key

static_host_map:
  "10.42.0.1": ["lighthouse.example.com:4242"]   # Lighthouse public IP/DNS

lighthouse:
  am_lighthouse: false
  interval: 60
  hosts:
    - "10.42.0.1"           # Nebula IP of lighthouse

listen:
  host: 0.0.0.0
  port: 4242

punchy:
  punch: true
  respond: true

relay:
  am_relay: false
  use_relays: true
  relays:
    - 10.42.0.1             # Use lighthouse as relay fallback

tun:
  dev: nebula1
  mtu: 1300

logging:
  level: info
  format: json

firewall:
  outbound:
    - port: any
      proto: any
      host: any

  inbound:
    # ICMP from anyone in the network
    - port: any
      proto: icmp
      host: any

    # SSH only from developers group
    - port: 22
      proto: tcp
      groups:
        - ssh-allowed

    # HTTP/HTTPS from web group
    - port: 80
      proto: tcp
      host: any
    - port: 443
      proto: tcp
      host: any

    # Monitoring from infrastructure group
    - port: 9090
      proto: tcp
      groups:
        - infrastructure
```

---

## 4. Firewall Rules

```yaml
# Group-based access control (the power of Nebula's firewall)
firewall:
  inbound:
    # Only database group can access PostgreSQL
    - port: 5432
      proto: tcp
      groups:
        - database-clients

    # Only monitoring can scrape metrics
    - port: 9090
      proto: tcp
      groups:
        - monitoring

    # CI/CD can SSH for deployment
    - port: 22
      proto: tcp
      groups:
        - cicd

    # Specific host access (by Nebula hostname)
    - port: 8080
      proto: tcp
      host: admin-server
```

---

## 5. Unsafe Routes (Subnet Routing)

Route traffic to non-Nebula subnets through a Nebula node (like a VPN gateway).

```yaml
# On the gateway node (must have IP forwarding enabled):
tun:
  unsafe_routes:
    - route: 192.168.1.0/24        # Corporate LAN subnet
      via: 10.42.0.1               # Route through this Nebula node
      mtu: 1300

# On the gateway host, enable forwarding:
# sysctl -w net.ipv4.ip_forward=1
# iptables -t nat -A POSTROUTING -s 10.42.0.0/16 -o eth0 -j MASQUERADE
```

---

## 6. DNS Integration

```yaml
# Lighthouse serves DNS for Nebula hostnames
lighthouse:
  serve_dns: true
  dns:
    host: 0.0.0.0
    port: 53

# Nodes can resolve each other by certificate name:
# dig @10.42.0.1 web-server-1  →  10.42.0.10
# dig @10.42.0.1 alice-laptop  →  10.42.1.100
```

---

## Cross-Domain Connections

**Nebula ↔ Kubernetes:** Use Nebula to create a secure overlay connecting K8s nodes across cloud providers or on-prem. Pods can reach services on the Nebula network via unsafe routes.

**Nebula ↔ Zero Trust:** Nebula's certificate-based identity + group-based firewall rules implement zero-trust networking at Layer 3. No IP-based trust — identity is cryptographic.

**Nebula ↔ CI/CD:** CI runners join the Nebula network with `cicd` group certificates, getting SSH access to deployment targets without exposing SSH to the internet.

---

## Self-Review Checklist

- [ ] CA key stored offline and backed up securely (not on any Nebula node)
- [ ] Certificate durations appropriate (shorter for user devices, longer for infrastructure)
- [ ] Groups assigned based on role (developers, servers, monitoring, cicd)
- [ ] Firewall rules follow least privilege — only required ports open per group
- [ ] At least 2 lighthouse nodes for redundancy
- [ ] Relay enabled on lighthouses for NAT-unfriendly networks
- [ ] Punchy enabled on all nodes for NAT traversal
- [ ] MTU set appropriately (1300 for most networks, lower for double-encapsulation)
- [ ] DNS serving enabled on lighthouse for name resolution
- [ ] Certificate rotation plan documented (before expiry)
- [ ] Unsafe routes only used when necessary, with IP forwarding properly configured
- [ ] Logging set to JSON format for structured log aggregation
