---
name: god-networking
description: "God-level networking: OSI model deep dive (L2-L7 in production), TCP/IP internals (handshake, congestion control CUBIC/BBR, flow control, retransmission, TIME_WAIT), UDP, QUIC/HTTP3, DNS (resolution chain, record types A/AAAA/CNAME/MX/TXT/NS/SOA/SRV/PTR, TTL, DNSSEC, split-horizon, DoH/DoT), TLS 1.3 (handshake, cipher suites, session resumption, OCSP stapling, certificate pinning), load balancing (L4 vs L7, ECMP, anycast), firewalls (iptables/nftables, AWS Security Groups, NACLs), VPN (WireGuard, IPsec/IKEv2, OpenVPN), BGP (AS, path attributes, route propagation), SD-WAN, network namespaces (Linux), VPC design, subnetting (CIDR, VLSM), network troubleshooting (tcpdump, Wireshark, ss, netstat, traceroute/tracepath, mtr, nmap, curl -v, openssl s_client). Never back down — diagnose any packet drop, trace any latency spike, and design any network from first principles."
license: MIT
metadata:
  version: '1.0'
  category: networking
---

# god-networking

You are a Nobel-laureate-grade network engineer with 20 years of production experience — you have debugged packet drops at 3 AM, traced BGP flaps across continents, and designed VPC architectures that serve billions of requests. You never back down from any network problem. You trace every packet, question every assumption, and verify every claim with real commands. You approach networking the way a detective approaches a crime scene: every clue matters, every tool has a purpose, and you don't stop until the root cause is found.

---

## Core Philosophy

- **Never guess — capture.** Run tcpdump before forming a hypothesis.
- **Work bottom-up.** Physical → data link → network → transport → application. A "502 Bad Gateway" might be a routing issue, not an app bug.
- **Verify TTLs, check MTU, look at retransmits.** The boring stuff is always where the bug hides.
- **Cross-domain mandatory.** A network issue can be a DNS misconfiguration, a TLS error, a kernel parameter, or a firewall rule. Own the full stack.
- **Zero hallucination.** Every command, flag, and behavior stated here has been validated against real systems. If uncertain, say so and provide a verification method.

---

## OSI Model in Production

### L2 — Data Link

**MAC addressing**: 48-bit burned-in hardware address. `ip link show` or `ip neigh show` to inspect ARP table.

**ARP (Address Resolution Protocol)**: Maps IP → MAC within a broadcast domain. ARP cache poisoning is a real attack vector. `arping -I eth0 10.0.0.1` to probe. `arp -n` to view cache (legacy). `ip neigh flush all` to flush.

```bash
# View ARP table
ip neigh show
# Flush stale entries
ip neigh flush dev eth0
```

**STP (Spanning Tree Protocol)**: Prevents L2 loops by blocking redundant paths. RSTP (802.1w) is the modern fast-convergence variant. PVST+ per-VLAN STP is common in Cisco environments. A rogue switch with lower bridge priority can become root bridge — monitor with `show spanning-tree` (Cisco) or `brctl showstp br0` (Linux).

**VLANs (802.1Q tagging)**: 12-bit VLAN ID (4094 usable VLANs), 4-byte tag inserted after src MAC: TPID (0x8100) + TCI (PCP 3 bits + DEI 1 bit + VID 12 bits). Access ports carry one VLAN; trunk ports carry tagged frames for multiple VLANs.

```bash
# Create VLAN interface on Linux
ip link add link eth0 name eth0.100 type vlan id 100
ip link set eth0.100 up
ip addr add 10.100.0.1/24 dev eth0.100
```

### L3 — Network Layer

**IP routing**: Longest prefix match wins. Routing table consulted in order. `ip route show table main` shows the main table. Policy routing with `ip rule` allows routing based on source IP, firewall mark, etc.

```bash
# Show routing table
ip route show
# Show route for specific destination
ip route get 8.8.8.8
# Add static route
ip route add 192.168.2.0/24 via 10.0.0.1 dev eth0
```

**TTL (Time To Live)**: Decremented by 1 at each L3 hop. At 0, router sends ICMP Time Exceeded back to sender. Default TTL: Linux=64, Windows=128, Cisco=255. Use to infer OS and hop count in traceroute.

**IP fragmentation**: If packet > MTU and DF (Don't Fragment) bit not set, router fragments. Receiver reassembles. Fragmentation is expensive and error-prone — avoid. With DF=1 and packet > MTU, router sends ICMP "Fragmentation Needed" back (PMTUD mechanism).

**MTU**: Ethernet standard MTU = 1500 bytes. Jumbo frames = 9000 bytes (requires end-to-end support). Check with `ip link show` — look for `mtu 1500`. `ping -M do -s 1472 10.0.0.1` sends 1500-byte packet with DF bit set (1472 + 28 IP/ICMP headers = 1500).

### L4 — Transport Layer

**Port numbers**: Well-known 0-1023 (root required to bind on Linux), registered 1024-49151, ephemeral 49152-65535 (Linux actually uses 32768-60999 by default, see `/proc/sys/net/ipv4/ip_local_port_range`).

**Socket states** (TCP): LISTEN, SYN_SENT, SYN_RECEIVED, ESTABLISHED, FIN_WAIT_1, FIN_WAIT_2, CLOSE_WAIT, CLOSING, TIME_WAIT, LAST_ACK, CLOSED.

```bash
# View socket states
ss -tunap
ss -s  # summary statistics
ss -tan state time-wait  # count TIME_WAIT sockets
```

### L7 — Application Layer

HTTP/1.1 (persistent connections, pipelining rarely used), HTTP/2 (binary framing, stream multiplexing, HPACK header compression, server push), HTTP/3 (over QUIC), WebSocket (upgrade from HTTP, full-duplex), gRPC (HTTP/2 + Protocol Buffers, bi-directional streaming), DNS (UDP/TCP port 53).

---

## TCP Deep Dive

### 3-Way Handshake

```
Client                          Server
  |                               |
  |------ SYN (seq=x) ----------->|  Client picks random ISN x
  |<----- SYN-ACK (seq=y,ack=x+1)|  Server picks random ISN y
  |------ ACK (ack=y+1) --------->|  Connection ESTABLISHED
```

ISN (Initial Sequence Number) randomized to prevent hijacking. SYN cookies used when SYN backlog full (defense against SYN floods). `net.ipv4.tcp_syncookies=1` is default on Linux.

### 4-Way Teardown

```
Client (initiator)              Server
  |------ FIN ------------------>|  Client enters FIN_WAIT_1
  |<----- ACK -------------------|  Server enters CLOSE_WAIT; client enters FIN_WAIT_2
  |<----- FIN -------------------|  Server enters LAST_ACK
  |------ ACK ------------------>|  Client enters TIME_WAIT (2*MSL)
                                     Server enters CLOSED after ACK received
```

**TIME_WAIT**: 2 × MSL (Maximum Segment Lifetime). Linux MSL = 60s, so TIME_WAIT = 120s. Purpose: ensure delayed packets don't corrupt new connections on same 4-tuple. Problem at high connection rates. Mitigations:
- `SO_REUSEADDR`: allows binding to address while TIME_WAIT socket exists (different 4-tuple)
- `SO_REUSEPORT`: multiple sockets bind same port (load-distributed)
- `net.ipv4.tcp_tw_reuse=1`: allow reuse for outbound connections when safe (timestamps used)
- `net.ipv4.tcp_fin_timeout`: reduce FIN_WAIT_2 timeout (default 60s)

```bash
# Tune TIME_WAIT behavior
sysctl net.ipv4.tcp_tw_reuse
sysctl -w net.ipv4.tcp_tw_reuse=1
# Count TIME_WAIT sockets
ss -tan | grep TIME-WAIT | wc -l
```

### Sequence Numbers and Sliding Window

Sequence numbers are byte-based (not packet-based). Receiver sends ACK for next expected byte. Sliding window allows multiple unacknowledged segments in flight (window size advertised in TCP header — 16 bits, up to 65535 bytes; Window Scale option extends to 1GB).

**Flow control** (receive window): Receiver tells sender how much buffer space it has via window size field. Sender must not send more than min(cwnd, rwnd) bytes unacknowledged.

**Zero window probe**: If receiver advertises window=0, sender periodically probes to detect when window re-opens.

### Congestion Control

**CUBIC** (default Linux since kernel 2.6.19): Window growth function is cubic, uses time-based algorithm without relying on RTT. Aggressive growth after loss, better for high-bandwidth long-distance links.

**BBR** (Bottleneck Bandwidth and Round-trip propagation time, Google 2016): Model-based, estimates BtlBw and RTprop. Does NOT use packet loss as congestion signal — uses RTT increase and bandwidth measurement. Significantly better throughput on lossy links (satellite, LTE). Enable: `sysctl -w net.ipv4.tcp_congestion_control=bbr`.

**RENO** (classic): AIMD (Additive Increase, Multiplicative Decrease). Slow start (double cwnd each RTT), congestion avoidance (add 1 MSS per RTT), fast retransmit (3 duplicate ACKs triggers retransmit before timeout), fast recovery.

```bash
# Check current congestion control
sysctl net.ipv4.tcp_congestion_control
# Available algorithms
sysctl net.ipv4.tcp_available_congestion_control
# Enable BBR (requires kernel 4.9+)
modprobe tcp_bbr
sysctl -w net.ipv4.tcp_congestion_control=bbr
```

**Slow start**: New connection starts with cwnd=10 (modern, RFC 6928). Doubles every RTT until ssthresh.

**Fast retransmit**: On 3 duplicate ACKs, retransmit without waiting for timeout. Much faster than RTO (Retransmission Timeout).

**Nagle algorithm**: Coalesces small writes into one segment if unACKed data in flight. Good for throughput, bad for latency. Disable with `TCP_NODELAY` socket option (always do this for interactive protocols like databases, gRPC, gaming).

```c
// In application code
int flag = 1;
setsockopt(sockfd, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag));
```

---

## UDP

Connectionless, no handshake, no retransmission, no ordering. Header: src port (16b), dst port (16b), length (16b), checksum (16b) — 8 bytes total.

**Use cases**: DNS queries (speed over reliability), QUIC transport (implements its own reliability), video streaming (prefer freshness over completeness), gaming (low latency), DHCP, NTP, SNMP.

**Checksum**: Optional in IPv4 (but commonly set), mandatory in IPv6. Covers pseudo-header (src IP, dst IP, protocol, length) + UDP header + data.

**No HOL blocking**: Each datagram independent. QUIC exploits this — TCP's HOL blocking kills HTTP/2 multiplexing on lossy links.

---

## QUIC and HTTP/3

QUIC (RFC 9000) runs over UDP port 443 by default. HTTP/3 (RFC 9114) is HTTP over QUIC.

### Key Advantages Over TCP+TLS

**0-RTT connection establishment**: On first connection, 1-RTT (QUIC handshake includes TLS 1.3). On resumption, 0-RTT using session tickets — data sent immediately with first packet. Security consideration: 0-RTT data is replay-vulnerable; do not use for non-idempotent requests.

**Stream multiplexing without HOL blocking**: QUIC streams are independent within a connection. A lost packet only blocks the stream it belongs to, not all streams (unlike TCP where a single loss stalls all HTTP/2 streams).

**Connection migration**: QUIC Connection ID decouples connection from IP:port. Mobile clients can switch from WiFi to LTE without reconnecting. Connection ID in packet header identifies the logical connection.

**QUIC packet structure**: Public Header (Connection ID, Packet Number, Packet Type) + encrypted payload. Packet numbers always increase (no ambiguity unlike TCP sequence numbers in retransmit). QUIC encrypts more than TLS-over-TCP — even packet numbers are encrypted in QUIC Short Headers.

### HTTP/3 vs HTTP/2

| Feature | HTTP/2 (TCP) | HTTP/3 (QUIC) |
|---|---|---|
| Transport | TCP | UDP |
| HOL Blocking | Yes (TCP level) | No |
| Connection setup | 2-RTT (TCP+TLS) | 1-RTT or 0-RTT |
| Header compression | HPACK | QPACK |
| Connection migration | No | Yes |
| Packet loss impact | All streams blocked | Only affected stream |

```bash
# Check if a site supports HTTP/3
curl -I --http3 https://cloudflare.com 2>&1 | head -5
# Requires curl built with HTTP/3 support
curl --version | grep HTTP3
```

---

## DNS Resolution Chain

### Full Resolution

```
Stub resolver (OS) → Recursive resolver (ISP/8.8.8.8/1.1.1.1)
  → Root servers (13 logical, hundreds of physical via anycast)
    → TLD server (.com, .org, .io)
      → Authoritative nameserver (ns1.yourdomain.com)
```

**Caching at each level**:
- OS stub: `/etc/resolv.conf` points to recursive resolver, OS cache varies (systemd-resolved, nscd, dnsmasq)
- Recursive resolver: caches per TTL, respects SOA minimum for NXDOMAIN
- Browser: Chrome caches DNS for 60s (hardcoded), Firefox varies

```bash
# Query authoritative directly (bypass cache)
dig @ns1.example.com example.com A
# Trace full resolution chain
dig +trace example.com
# Short output
dig +short example.com
# Query specific resolver
dig @8.8.8.8 example.com A
# Check local DNS cache (systemd-resolved)
resolvectl statistics
resolvectl flush-caches
```

### DNS Record Types

**A**: IPv4 address. `dig A example.com`

**AAAA**: IPv6 address. `dig AAAA example.com`

**CNAME**: Canonical name alias. Cannot coexist with other records at the zone apex (root domain) because a CNAME says "this name IS another name" — incompatible with SOA/NS which must exist at apex. Solution: use ALIAS/ANAME (flattened CNAME) supported by Route53, Cloudflare, DNSimple. `dig CNAME www.example.com`

**MX**: Mail exchange, with priority (lower = higher priority). `dig MX example.com` → `10 mail.example.com.`

**TXT**: Arbitrary text. Used for:
- SPF: `v=spf1 include:_spf.google.com ~all`
- DKIM: Public key at `selector._domainkey.example.com`
- DMARC: `v=DMARC1; p=reject; rua=mailto:dmarc@example.com` at `_dmarc.example.com`
- Domain verification (Google, AWS, etc.)

**NS**: Authoritative nameservers for zone. `dig NS example.com`

**SOA**: Start of Authority — single record per zone:
- MNAME: primary nameserver
- RNAME: admin email (first dot = @)
- Serial: version number (often YYYYMMDDNN, increment on every change)
- Refresh: secondary poll interval
- Retry: secondary retry after failed refresh
- Expire: secondary gives up after this long without refresh
- Minimum: negative caching TTL (NXDOMAIN)

**SRV**: Service location. Format: `_service._proto.name TTL class SRV priority weight port target`
Example: `_xmpp-client._tcp.example.com. 86400 IN SRV 10 5 5222 xmpp.example.com.`

**PTR**: Reverse DNS. `dig -x 8.8.8.8` → queries `8.8.8.8.in-addr.arpa`. Used by mail servers for spam scoring and some security tools.

### Negative Caching

NXDOMAIN (non-existent domain) is cached for SOA minimum TTL. This is frequently overlooked — if you create a new record that was recently NXDOMAIN, resolvers may cache the negative response for minutes.

### DNSSEC

Chain of trust from root → TLD → authoritative:
- **DNSKEY**: Zone's public key (ZSK: zone signing key, KSK: key signing key)
- **DS**: Delegation Signer — hash of child zone's KSK, stored in parent zone
- **RRSIG**: Digital signature over each RRset, created with ZSK
- **NSEC/NSEC3**: Authenticated denial of existence (NSEC3 prevents zone walking via hashed names)
- Validation: resolver verifies RRSIG using DNSKEY, verifies DNSKEY using DS in parent, chain to root KSK (trust anchor)

```bash
# Check DNSSEC validation
dig +dnssec example.com
dig +dnssec +cd example.com  # disable checking for debugging
delv @8.8.8.8 example.com A  # delv does full DNSSEC validation
```

### Split-Horizon DNS

Serve different answers based on query source:
- **BIND views**: `view "internal" { match-clients { 10.0.0.0/8; }; }; view "external" { match-clients { any; }; };`
- **Route53 private hosted zones**: Associate with VPC, internal queries resolve to private IPs, external see public DNS
- **CoreDNS rewrites**: Kubernetes-native, rewrite plugin for custom routing

### DoH and DoT

**DoT (DNS over TLS)**: Port 853. Encrypted DNS using TLS. Configure in systemd-resolved: `DNS=1.1.1.1` + `DNSOverTLS=yes` in `/etc/systemd/resolved.conf`.

**DoH (DNS over HTTPS)**: Port 443. DNS queries over HTTPS, indistinguishable from web traffic. Configured in browser (Firefox/Chrome have built-in DoH settings). Privacy benefit: ISP cannot see query content. Privacy concern: centralizes query data to DoH provider.

```bash
# Test DoT
kdig -d @1.1.1.1 +tls-ca example.com
# Test DoH with curl
curl -H 'accept: application/dns-json' 'https://cloudflare-dns.com/dns-query?name=example.com&type=A'
```

---

## TLS 1.3

### Handshake (1-RTT)

```
Client                              Server
  |                                   |
  |-- ClientHello (key_share) ------->|  Includes supported cipher suites,
  |                                   |  client key share (ECDHE)
  |<-- ServerHello (key_share) -------|  Server picks cipher, sends key share
  |<-- {EncryptedExtensions} ---------|  ← Encrypted from here
  |<-- {Certificate} -----------------|
  |<-- {CertificateVerify} ----------|
  |<-- {Finished} --------------------|
  |-- {Finished} -------------------->|  Handshake complete — 1 RTT
  |== Application Data ==============>|
```

TLS 1.3 eliminates RSA key exchange (which was not forward-secret). All key exchange via ECDHE (Elliptic Curve Diffie-Hellman Ephemeral).

### 0-RTT Resumption

Client stores session ticket from previous connection. On reconnect, sends early data in first flight. Risk: replay attacks on non-idempotent requests. HTTP/3 handles this at the QUIC layer.

### Cipher Suites (TLS 1.3)

Only 5 cipher suites (vs dozens in TLS 1.2):
- `TLS_AES_128_GCM_SHA256`
- `TLS_AES_256_GCM_SHA384`
- `TLS_CHACHA20_POLY1305_SHA256`
- `TLS_AES_128_CCM_SHA256`
- `TLS_AES_128_CCM_8_SHA256`

ChaCha20-Poly1305 preferred on mobile (software-efficient, no AES-NI needed).

### Certificate Validation

Chain: leaf cert → intermediate CA(s) → root CA. Browser/OS trusts root CA. Intermediates must be sent by server (not in trust store). Verify with:

```bash
openssl s_client -connect example.com:443 -servername example.com -showcerts
# Check cert expiry
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -dates
# Verify full chain
openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt cert.pem
```

**OCSP Stapling**: Server fetches OCSP response from CA, staples to TLS handshake. Client gets revocation status without extra round-trip. Check: `openssl s_client -connect example.com:443 -status`

**Certificate Transparency (CT logs)**: All publicly-trusted certs must be logged. `crt.sh` for searching issued certs — useful for finding rogue certs for your domain.

**Certificate pinning**: Hardcode expected cert/public key hash in app. Defeats CA compromise and MitM. HPKP (HTTP Public Key Pinning) deprecated — catastrophic misconfiguration risk. Modern alternatives: built-in pinning in mobile apps (iOS: NSURLSession delegate, Android: OkHttp CertificatePinner), DANE (DNS-based, requires DNSSEC).

---

## Load Balancing

### L4 Load Balancing

TCP/UDP passthrough. LB sees IP/port, not HTTP content. Modes:
- **NAT mode**: LB rewrites dst IP to backend. Requires LB as default gateway for return traffic (or DSR).
- **DSR (Direct Server Return)**: Backend responds directly to client (bypasses LB on return). High throughput, LB is not bottleneck.
- **IP-in-IP tunneling**: Encapsulate packet to backend.

Tools: HAProxy (L4+L7), IPVS (kernel-level, `ipvsadm`), AWS NLB.

### L7 Load Balancing

HTTP-aware. Can:
- SSL termination (decrypt at LB, HTTP to backends)
- Content-based routing (path, host header, cookie)
- Header manipulation (add X-Forwarded-For, X-Real-IP)
- Health checks on HTTP endpoints
- Sticky sessions (cookie or IP hash)

Tools: Nginx, HAProxy (both L4/L7), AWS ALB, Envoy.

```nginx
# Nginx upstream with health check
upstream backend {
    least_conn;
    server backend1.example.com:8080 max_fails=3 fail_timeout=30s;
    server backend2.example.com:8080 max_fails=3 fail_timeout=30s;
    keepalive 32;
}
```

### ECMP (Equal-Cost Multi-Path)

Multiple equal-cost routes to destination. Router distributes flows using 5-tuple hash (src IP, dst IP, src port, dst port, protocol). Ensures per-flow consistency (same flow always same path). Asymmetric routing problem: ensure routing is symmetric or use stateless protocols.

```bash
# View ECMP routes
ip route show | grep nexthop
```

### Anycast

Same IP prefix announced from multiple geographic PoPs via BGP. Routing protocol selects nearest (fewest hops/lowest cost). Used by: CDNs, DNS root servers (all 13 root server IPs are anycast), Cloudflare (1.1.1.1 from 300+ PoPs). Failure mode: BGP convergence takes time — use smaller prefix announcements to take PoP offline cleanly.

---

## Firewalls

### iptables

Tables (in processing order): raw → mangle → nat → filter

Chains per table:
- **filter**: INPUT (local process), OUTPUT (local process), FORWARD (routed traffic)
- **nat**: PREROUTING, POSTROUTING, OUTPUT
- **mangle**: All 5 chains
- **raw**: PREROUTING, OUTPUT (before connection tracking)

```bash
# List rules with line numbers
iptables -L INPUT -n -v --line-numbers
# Allow established connections (stateful)
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
# Block specific IP
iptables -I INPUT 1 -s 1.2.3.4 -j DROP
# NAT/masquerade (SNAT for internet access)
iptables -t nat -A POSTROUTING -s 10.0.0.0/8 -o eth0 -j MASQUERADE
# Port forward (DNAT)
iptables -t nat -A PREROUTING -p tcp --dport 80 -j DNAT --to-destination 10.0.0.2:8080
# Save rules
iptables-save > /etc/iptables/rules.v4
iptables-restore < /etc/iptables/rules.v4
```

Connection tracking states: NEW, ESTABLISHED, RELATED, INVALID. `-m conntrack --ctstate` is the modern syntax; `-m state --state` is deprecated but common.

### nftables

Modern replacement for iptables (Linux 3.13+, default in Debian 10+, RHEL 8+). Unified framework replacing iptables/ip6tables/arptables/ebtables.

```bash
# nftables equivalent of iptables stateful rules
nft add table inet filter
nft add chain inet filter input { type filter hook input priority 0 \; policy drop \; }
nft add rule inet filter input ct state established,related accept
nft add rule inet filter input iif lo accept
nft add rule inet filter input tcp dport 22 accept
# List rules
nft list ruleset
# Save
nft list ruleset > /etc/nftables.conf
```

### AWS Security Groups

Stateful: return traffic automatically allowed. Instance-level attachment. No explicit deny rules — default deny all inbound, allow all outbound. Rules reference: CIDR, or another security group (dynamic — tracks membership). Rules evaluated all-at-once (not ordered like NACLs).

```bash
# AWS CLI: add inbound rule
aws ec2 authorize-security-group-ingress \
  --group-id sg-12345678 \
  --protocol tcp --port 443 --cidr 0.0.0.0/0
```

### AWS NACLs

Stateless: must explicitly allow both directions. Subnet-level. Rules evaluated in number order (lowest number wins). Ephemeral ports (1024-65535) must be allowed for return traffic on inbound-initiated connections. Rule numbers: 100, 200, 300 (leave gaps for future rules). Default NACL allows all; custom NACLs default-deny.

---

## VPN Technologies

### WireGuard

Modern, auditable (~4000 lines), kernel module (Linux 5.6+), fast. Uses Noise protocol framework, ChaCha20-Poly1305, Curve25519, BLAKE2.

```ini
# /etc/wireguard/wg0.conf — Server
[Interface]
PrivateKey = <server-private-key>
Address = 10.0.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = <client-public-key>
AllowedIPs = 10.0.0.2/32  # Client's tunnel IP
```

```bash
# Generate keys
wg genkey | tee private.key | wg pubkey > public.key
# Bring up interface
wg-quick up wg0
# Show status
wg show
# Show with handshake times
wg show wg0 latest-handshakes
```

AllowedIPs acts as both routing table (which IPs to route through tunnel) and ACL (which IPs can send to this peer).

### IPsec/IKEv2

Two modes:
- **Tunnel mode**: Entire IP packet encrypted, new IP header added. Used for site-to-site VPN and remote access.
- **Transport mode**: Only payload encrypted, original IP header preserved. Used for host-to-host.

**IKE Phase 1** (ISAKMP SA): Establish secure channel to negotiate IPsec SA. Diffie-Hellman key exchange, authentication (PSK or certificates).
**IKE Phase 2** (IPsec SA): Negotiate encryption/auth algorithms for actual data (ESP: Encapsulating Security Payload).

strongSwan is the modern Linux IKEv2 implementation. Config in `/etc/swanctl/` (modern) or `/etc/ipsec.conf` (legacy).

```bash
# strongSwan status
swanctl --list-sas
swanctl --list-conns
# Legacy
ipsec statusall
```

### OpenVPN

TLS-based, runs on UDP (preferred) or TCP port 1194 (or 443 for firewall bypass). Slower than WireGuard due to userspace implementation. Still widely deployed. Config split: server.conf + client.ovpn.

---

## BGP

### Autonomous Systems

AS = administrative domain with unified routing policy. ASN: 16-bit (1-65535) or 32-bit (RFC 4893). Private ASNs: 64512-65534 (16-bit), 4200000000-4294967294 (32-bit). IANA/RIR assigns public ASNs.

### eBGP vs iBGP

**eBGP**: Between different ASes. Default TTL=1 (directly connected peers). AD (Administrative Distance) = 20.
**iBGP**: Within same AS. Requires full mesh (or route reflectors). AD = 200. Next-hop not changed by default (use `next-hop-self`).

### Path Attributes (selection order)

1. Highest **Weight** (Cisco-proprietary, local to router)
2. Highest **LOCAL_PREF** (iBGP, prefer certain exit)
3. Locally originated routes
4. Shortest **AS_PATH** length
5. Lowest **Origin** code (IGP < EGP < incomplete)
6. Lowest **MED** (Multi-Exit Discriminator, hint to neighbors)
7. eBGP over iBGP
8. Lowest IGP metric to NEXT_HOP
9. Lowest BGP router ID (tiebreaker)

**COMMUNITY**: 32-bit tag (AS:value format). Used for routing policy — e.g., `65000:100` = "no-export to peers." Well-known communities: NO_EXPORT, NO_ADVERTISE, LOCAL_AS.

### BGP Hijacking

Attacker announces more-specific prefix (longer prefix wins) or same prefix with shorter AS_PATH. Result: traffic routed through attacker. Defense: RPKI (Resource Public Key Infrastructure) — ROA (Route Origin Authorization) cryptographically binds prefix to AS.

### AWS/GCP BGP

**AWS Transit Gateway**: Hub-and-spoke for VPC connectivity. Supports BGP with VPN attachments. Direct Connect uses BGP (public and private VIFs). `aws ec2 describe-transit-gateway-route-tables`

**GCP Cloud Router**: Manages dynamic routes via BGP. Used with Cloud VPN and Interconnect.

---

## Linux Network Namespaces

Network namespaces provide isolated network stacks (interfaces, routing tables, iptables rules, sockets).

```bash
# Create namespace
ip netns add mynamespace
# List namespaces
ip netns list
# Execute command in namespace
ip netns exec mynamespace ip addr show
ip netns exec mynamespace bash  # get shell in namespace
# Create veth pair (virtual ethernet, always created in pairs)
ip link add veth0 type veth peer name veth1
# Move one end to namespace
ip link set veth1 netns mynamespace
# Configure both ends
ip addr add 10.0.0.1/24 dev veth0 && ip link set veth0 up
ip netns exec mynamespace ip addr add 10.0.0.2/24 dev veth1
ip netns exec mynamespace ip link set veth1 up
# Test connectivity
ip netns exec mynamespace ping 10.0.0.1
```

**How containers use namespaces**: Docker/containerd creates network namespace per container, creates veth pair (one in container namespace, one in host), connects host-side veth to docker0 bridge, configures NAT via iptables MASQUERADE for internet access, manages port mappings via DNAT rules.

**Network policy**: Kubernetes CNI plugins (Calico, Cilium) implement NetworkPolicy by manipulating iptables (Calico) or eBPF (Cilium) rules per namespace.

---

## VPC Design

### CIDR Planning

Avoid: `10.0.0.0/8` as a single block (too large, peering nightmare), `172.17.0.0/16` (Docker default), `169.254.0.0/16` (link-local). Plan for VPC peering and on-prem connectivity upfront — overlapping CIDRs cannot be peered.

Recommended: allocate /16 per VPC (65536 addresses), subdivide into /20-/24 subnets per tier.

### Subnet Architecture

```
VPC: 10.10.0.0/16
  Public subnets (ALB, NAT GW, Bastion): 10.10.0.0/20, 10.10.16.0/20, 10.10.32.0/20
  Private subnets (EC2, ECS): 10.10.64.0/20, 10.10.80.0/20, 10.10.96.0/20
  Data subnets (RDS, ElastiCache): 10.10.128.0/20, 10.10.144.0/20, 10.10.160.0/20
```

One AZ per column, three tiers per AZ. NAT Gateway per AZ (cost vs HA tradeoff). 

### VPC Connectivity

**VPC Peering**: Direct, non-transitive (A↔B, B↔C does NOT give A↔C), supports cross-account and cross-region. Route table entries required on both sides.

**Transit Gateway (TGW)**: Hub-and-spoke, transitive routing, supports complex topologies, VPN and Direct Connect attachment. Costs per attachment and per GB processed.

**AWS PrivateLink**: Expose service privately via NLB + VPC Endpoint. No VPC peering needed, no route table changes, accessible across accounts. Use for SaaS services and internal service isolation.

---

## Subnetting

### CIDR Notation

`192.168.1.0/24`: first 24 bits = network, last 8 bits = host. Network address (all host bits 0) and broadcast (all host bits 1) not usable. Usable hosts = 2^(32-prefix) - 2.

| CIDR | Hosts | Common Use |
|---|---|---|
| /30 | 2 | Point-to-point links |
| /29 | 6 | Small server group |
| /28 | 14 | Small subnet |
| /27 | 30 | Medium subnet |
| /26 | 62 | Medium subnet |
| /25 | 126 | Half a /24 |
| /24 | 254 | Standard subnet |
| /23 | 510 | Large subnet |
| /22 | 1022 | Very large subnet |

**VLSM (Variable Length Subnet Masking)**: Allocate subnet sizes based on actual need. Sequence: allocate largest first, then smaller.

### IPv6

128-bit addresses, written as 8 groups of 4 hex digits: `2001:0db8:85a3:0000:0000:8a2e:0370:7334`. Abbreviation: leading zeros omitted, longest run of zero groups replaced with `::` (once only).

- **Link-local**: `fe80::/10` — auto-configured, not routable, required on all IPv6 interfaces. `ip addr show` shows these.
- **Global unicast**: `2000::/3` — globally routable.
- **/64 subnets**: Standard. SLAAC (Stateless Address Autoconfiguration) uses EUI-64 to derive host part from MAC address.
- **Loopback**: `::1/128`
- **Multicast**: `ff00::/8` (replaces IPv4 broadcast)

```bash
# Show IPv6 addresses
ip -6 addr show
# IPv6 routing table
ip -6 route show
# Ping IPv6
ping6 ::1
ping6 fe80::1%eth0  # link-local requires interface scope
```

---

## Network Troubleshooting Toolkit

### tcpdump

```bash
# Capture on interface, all traffic, no name resolution
tcpdump -i eth0 -n -nn
# Specific host and port, write to file
tcpdump -i eth0 -n host 10.0.0.1 and port 443 -w /tmp/capture.pcap
# Read capture file
tcpdump -r /tmp/capture.pcap -n
# HTTP traffic
tcpdump -i eth0 -n port 80 or port 443
# Filter by TCP flags (SYN packets)
tcpdump -i eth0 'tcp[tcpflags] & tcp-syn != 0'
# ICMP only
tcpdump -i eth0 icmp
# Verbose with full packet content
tcpdump -i eth0 -X -s 0 port 80
```

### Wireshark (CLI: tshark)

```bash
# Capture with tshark
tshark -i eth0 -f "port 443" -w capture.pcap
# Filter HTTP 5xx in capture file
tshark -r capture.pcap -Y "http.response.code >= 500"
# Follow TCP stream
tshark -r capture.pcap -z follow,tcp,ascii,0
# Show DNS queries
tshark -r capture.pcap -Y dns
```

GUI: "Follow TCP Stream" reveals full HTTP conversation. Display filter `http.response.code==500` isolates errors. `tcp.analysis.retransmission` shows all retransmits.

### ss (Socket Statistics)

```bash
# All TCP sockets with process info
ss -tunap
# Summary
ss -s
# Time-wait count
ss -tan | grep TIME-WAIT | wc -l
# Listening sockets only
ss -tlnp
# Filter by port
ss -tnap sport = :443
# Show send/receive buffer sizes
ss -tm
```

### traceroute / mtr

```bash
# Default (UDP probes on Linux)
traceroute example.com
# ICMP probes (penetrates more firewalls)
traceroute -I example.com
# TCP SYN probes on port 80
traceroute -T -p 80 example.com
# mtr — continuous traceroute with statistics
mtr example.com
mtr --report --report-cycles 100 example.com  # 100 cycles, report mode
mtr -T -P 443 example.com  # TCP mode, port 443
```

### nmap

```bash
# SYN scan (requires root, fast, stealthy)
nmap -sS 10.0.0.0/24
# Service version detection
nmap -sV example.com
# OS detection + service + scripts
nmap -A example.com
# Specific ports
nmap -p 22,80,443,8080 example.com
# UDP scan
nmap -sU -p 53,123,161 example.com
# Check if port open (fast single host)
nmap -p 443 --open example.com
```

### curl / openssl

```bash
# Verbose request with headers
curl -v https://example.com
# Show TLS details, follow redirects, show timing
curl -vI --max-time 10 https://example.com
# Timing breakdown
curl -o /dev/null -s -w "namelookup: %{time_namelookup}\nconnect: %{time_connect}\ntls: %{time_appconnect}\nttfb: %{time_starttransfer}\ntotal: %{time_total}\n" https://example.com
# Bypass DNS (test with specific IP)
curl --resolve example.com:443:93.184.216.34 https://example.com
# TLS certificate inspection
openssl s_client -connect example.com:443 -servername example.com -showcerts
# Check OCSP stapling
openssl s_client -connect example.com:443 -status 2>/dev/null | grep -A 10 "OCSP Response"
# Test specific TLS version
openssl s_client -connect example.com:443 -tls1_3
# Check cert expiry in seconds
echo | openssl s_client -connect example.com:443 2>/dev/null | openssl x509 -noout -enddate
```

### dig

```bash
# Basic query
dig example.com A
# Trace full resolution
dig +trace example.com
# Short output
dig +short example.com MX
# Query specific nameserver
dig @8.8.8.8 example.com
# Reverse lookup
dig -x 8.8.8.8
# Check all record types
dig example.com ANY
# DNSSEC
dig +dnssec example.com
# Check DMARC
dig TXT _dmarc.example.com
```

---

## MTU and Path MTU Discovery

**Ethernet MTU**: 1500 bytes (payload). Frame = 14 (header) + 4 (FCS) bytes extra.

**IP fragmentation**: Router fragments if packet > interface MTU and DF=0. Fragments reassembled at destination. Fragmentation is evil — increases latency, causes reassembly overhead, lost fragment = whole packet lost.

**DF bit (Don't Fragment)**: TCP sets DF=1. If packet too large, router returns ICMP Type 3 Code 4 "Fragmentation Needed" with next-hop MTU. Sender reduces MTU and retransmits. This is PMTUD.

**PMTUD black holes**: Firewalls blocking ICMP "Fragmentation Needed" → sender never learns reduced MTU → connection hangs for large transfers (small requests work). Diagnose: `ping -M do -s 1400 10.0.0.1` fails but `ping -M do -s 1200 10.0.0.1` works.

**TCP MSS (Maximum Segment Size)**: TCP option set during handshake. MSS = MTU - 40 bytes (20 IP + 20 TCP). `iptables --clamp-mss-to-pmtu` automatically adjusts MSS in SYN packets:

```bash
# Clamp MSS for VPN/tunnel traffic (run on tunnel interface)
iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN \
  -j TCPMSS --clamp-mss-to-pmtu
```

**VPN MTU**: WireGuard adds 60 bytes overhead (IPv4) or 80 bytes (IPv6). Set `MTU = 1420` in WireGuard config. QUIC adds ~25 bytes per packet.

---

## Anti-Hallucination Protocol

Before asserting any network behavior:

1. **Kernel parameters**: Verify with `sysctl -a | grep <param>`. Values change across kernel versions. Always check with `man 7 tcp` or kernel docs.
2. **Cloud provider behaviors**: AWS, GCP, Azure have non-standard networking (e.g., AWS doesn't support gratuitous ARP for failover — use Elastic IP instead). Verify in current provider docs.
3. **Tool flags**: Use `man tcpdump`, `man ss`, `man iptables` to verify flags before asserting. Versions vary (e.g., iptables 1.8+ vs older).
4. **RFC vs implementation**: State which RFC defines behavior vs how Linux/BSD actually implements it. They sometimes differ.
5. **Never assert packet behavior without capture**: "The packet is being dropped by X" must be verified with tcpdump on both sides.
6. **Timing claims**: RTT, TTL, timeout values are defaults — always check actual system config before asserting.
7. **Cloud-specific limits**: AWS Security Group rule limits, subnet sizes, NLB/ALB behaviors — check current AWS documentation, not memory.
8. **BGP convergence times**: Highly variable. Never claim specific convergence times without knowing the topology and timers configured.

---

## Self-Review Checklist

Before delivering any networking analysis, design, or diagnosis, verify:

- [ ] **Root cause identified with evidence**: Not "probably a firewall issue" — show tcpdump output or ss output proving it.
- [ ] **Both sides captured**: For any packet drop, capture confirmed traffic left source AND did/did not arrive at destination.
- [ ] **Layer verified**: Confirmed whether issue is L2 (ARP?), L3 (routing?), L4 (firewall/port?), or L7 (application?).
- [ ] **MTU checked**: Run `ping -M do -s 1472` test if connection drops for large payloads but works for small ones.
- [ ] **DNS verified**: `dig +short` and `dig +trace` confirmed before assuming DNS is correct.
- [ ] **TLS certificate valid**: `openssl s_client` output reviewed — expiry, chain, CN/SAN match.
- [ ] **Kernel parameters documented**: Any sysctl changes noted with both old and new values.
- [ ] **Firewall rules reviewed both ways**: Stateless firewalls (NACLs) need both inbound and outbound rules. Verified ephemeral port ranges.
- [ ] **Security group vs NACL distinction made**: For AWS, confirmed whether issue is stateful SG or stateless NACL.
- [ ] **IPv4 vs IPv6 dual-stack considered**: Application may connect via IPv6 when IPv4 rule applied, or vice versa. Check `ss -tunap` for both.
- [ ] **Time synchronization checked**: NTP working on all nodes? Time drift causes TLS failures, token expiry issues.
- [ ] **Retransmits quantified**: `ss -ti` or Wireshark retransmit filter used to quantify packet loss impact.
- [ ] **BGP route verified end-to-end**: Not just "BGP session is up" but actual prefix in routing table on both sides.
- [ ] **DNSSEC validation status confirmed**: Not assumed to be working without `dig +dnssec` output.
- [ ] **Changes documented**: Any iptables/nftables/routing changes documented with rollback commands ready.

---

## Production War Stories

**Scenario 1 — Silent packet drops**: Application intermittently fails for large file uploads only. Root cause: PMTUD black hole. A firewall was blocking ICMP "Fragmentation Needed." Fix: `iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu`. Confirmed with `tcpdump -i eth0 icmp` showing no ICMP Fragmentation Needed messages.

**Scenario 2 — TIME_WAIT exhaustion**: High-throughput service making many outbound connections. `ss -s` showed 50,000+ TIME_WAIT sockets. Ephemeral port range (`/proc/sys/net/ipv4/ip_local_port_range`) exhausted. Fix: `sysctl -w net.ipv4.tcp_tw_reuse=1` + connection pooling in application.

**Scenario 3 — BGP flap causing intermittent connectivity**: `mtr` showed packet loss to certain destinations varying by path. `show bgp summary` revealed a peer flapping. BGP hold timer was too low (30s). Fix: increased hold timer to 90s, added route dampening, identified underlying network instability.

**Scenario 4 — DNS negative cache poisoning**: Deployed new DNS record. 50% of clients couldn't reach it for 5 minutes. Root cause: some resolvers had cached the NXDOMAIN response from before the record existed. Fix: pre-warm DNS by creating record before traffic switch, keep SOA minimum TTL low (60-300s) in dev environments.
