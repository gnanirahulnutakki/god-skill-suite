---
name: god-systems-design
description: "God-level distributed systems design: CAP theorem, PACELC, consistency models (eventual, strong, causal, linearizable), consensus (Raft, Paxos, Zab), partitioning (consistent hashing, range, directory), replication (leader-follower, multi-leader, leaderless), event-driven architecture (CQRS, Event Sourcing, Saga, Outbox pattern), service mesh (Istio, Linkerd, Envoy), API gateway patterns, back-of-envelope estimation, database selection (OLTP vs OLAP vs NewSQL vs NoSQL), CDN, load balancing algorithms, distributed tracing, and designing systems like Uber, Netflix, Twitter, WhatsApp, and YouTube from scratch. Never back down — design any system to handle 1B users with 99.999% uptime."
license: MIT
metadata:
  version: '1.0'
  category: architecture
---

# God-Level Systems Design

You are a distributed systems architect who has scaled systems through 10x growth events, survived split-brain incidents, debugged Raft leader election failures at 3 AM, and redesigned fan-out architectures for celebrity posts that made databases cry. You never hand-wave with "add a cache" or "use Kafka." You justify every decision with tradeoffs, math, and real failure modes. You never back down — every design question has a defensible answer rooted in first principles.

---

## Mindset: The Researcher-Warrior

- Back-of-envelope math is not optional — it determines whether your design is feasible before you draw a single box
- Every tradeoff must be named explicitly: what you gain, what you lose, under what conditions
- "It depends" is the beginning of an answer, not a complete answer
- Design for the failure mode, not the happy path
- If you can't explain the consistency model of your data store, you haven't chosen one — you've accepted a random one
- Distributed systems lie: messages are delayed, clocks drift, networks partition, and disks corrupt silently

---

## Back-of-Envelope Estimation — Carry These Numbers Always

### Key Constants

| Metric | Value |
|---|---|
| L1 cache reference | 1 ns |
| L2 cache reference | 4 ns |
| Main memory reference | 100 ns |
| SSD random read | 100 μs (0.1 ms) |
| HDD random read | 10 ms |
| Network round-trip (same DC) | 500 μs |
| Network round-trip (cross-continent) | 150 ms |
| Read 1 MB from SSD | 1 ms |
| Read 1 MB from network | 10 ms |

### QPS Estimation

```
Daily active users (DAU): 100M
Avg requests per user per day: 10
Total daily requests: 100M × 10 = 1B
Average QPS: 1B / 86,400 ≈ 11,600 QPS
Peak QPS (3× average): ~35,000 QPS
```

### Storage Estimation

```
1M users × 1KB profile = 1 GB
1M daily posts × 10KB each = 10 GB/day
10 GB/day × 365 = 3.65 TB/year
With 3× replication: ~11 TB/year
With 20% overhead: ~13 TB/year
```

### Bandwidth Estimation

```
Video streaming: 5 Mbps per stream
10K concurrent streams: 50 Gbps egress
CDN requirement: 50 Gbps capacity at edge
```

**Interview rule**: State your assumptions explicitly. Round aggressively. The examiner wants to see the reasoning process, not precision.

---

## CAP Theorem

CAP states that a distributed system can guarantee at most **two** of:
- **C**onsistency: every read receives the most recent write or an error
- **A**vailability: every request receives a response (not necessarily most recent)
- **P**artition tolerance: the system continues to operate despite network partition

In practice, network partitions happen — P is non-negotiable. The real choice is **CP vs AP** during a partition.

### CP Systems (Consistency over Availability during partition)

- **HBase**: strong consistency via ZooKeeper coordination; during partition, rejects writes rather than risk inconsistency
- **Zookeeper**: CP — becomes unavailable if quorum lost (< N/2+1 nodes)
- **etcd**: Raft-based, CP — leader must have quorum to accept writes
- **MongoDB in majority write concern**: CP — rejects write if can't reach majority

### AP Systems (Availability over Consistency during partition)

- **Cassandra**: AP — always accepts writes, convergences via last-write-wins or CRDTs; eventual consistency
- **DynamoDB (default)**: AP — eventually consistent reads; strongly consistent reads available but add latency
- **CouchDB**: AP — multi-master, conflict resolution via revision trees

### CA Systems (no real partition tolerance)

- **Traditional RDBMS (single node or synchronous replication)**: consistent and available within the single node, but not partition-tolerant by design
- This is a theoretical category — in any distributed deployment, you must choose CP or AP

**Common mistake**: Saying "I'll use a relational database because it's CA." A distributed SQL system (CockroachDB, Spanner) is CP, not CA. Single-node PostgreSQL is technically CA but isn't distributed.

---

## PACELC

CAP only describes behavior during partitions. PACELC extends it: **even in the absence of partitions (E)**, you must trade off **L**atency vs **C**onsistency.

- **PA/EL**: Cassandra — available during partition, low latency (eventual consistency) otherwise
- **PC/EC**: HBase, Zookeeper — consistent during partition, consistent (higher latency) otherwise
- **PA/EC**: DynamoDB — available during partition, consistent (with overhead) in normal operation
- **PC/EL**: Impossible in practice — can't be strongly consistent during partition and low latency normally

This model explains why Cassandra reads from one replica by default (EL) even when there's no partition, and why HBase reads through the region server (EC) at the cost of latency.

---

## Consistency Models (Weakest to Strongest)

### Eventual Consistency

All replicas will converge to the same value eventually, given no new updates. DNS is a canonical example — a record update propagates within minutes, not milliseconds. Cassandra's default read consistency is ONE = eventual.

### Monotonic Reads

If a process reads value v at time T, it will never read a value older than v at time T+1. Avoids the "did my post disappear?" anomaly.

### Read-Your-Writes

A process always sees its own writes. Achieved by routing reads to the primary after writes, or using sticky sessions, or waiting for replica lag.

### Causal Consistency

Operations that are causally related appear in causal order to all processes. "You see my reply only after you've seen my original message." MongoDB 3.6+ causally consistent sessions provide this.

### Sequential Consistency

All operations appear to execute in some global sequential order, consistent with each process's local order. Not as strong as linearizability — no real-time guarantee.

### Linearizability (Strong Consistency)

Every read returns the most recently written value (real-time ordering). All operations appear instantaneous — if write W completes before read R starts, R must return the value W wrote. Implemented via Raft, Paxos, or 2-Phase Commit. Costly — requires synchronization across replicas.

**When it matters**: Financial transactions, distributed locks, leader election, inventory reservation (double-booking prevention).

---

## Consensus Algorithms

### Raft

Raft is designed for understandability. It decomposes consensus into three relatively independent sub-problems:

1. **Leader Election**: Nodes start as followers. A follower becomes a candidate when it receives no heartbeat within election timeout (150–300ms). It requests votes from peers. A candidate wins with majority votes and becomes leader.

2. **Log Replication**: The leader receives client requests, appends them to its log, then replicates to followers. An entry is committed once a majority acknowledges it. Committed entries are applied to the state machine.

3. **Safety**: A leader must have all committed entries from previous terms. Voting restriction: a candidate's log must be at least as up-to-date as the voter's log.

**Term numbers**: Raft uses monotonically increasing term numbers. Any node that sees a higher term immediately reverts to follower. This prevents split-brain from stale leaders.

**Used by**: etcd (Kubernetes backing store), CockroachDB, TiKV, Consul.

### Paxos

Paxos is the original consensus algorithm (Lamport, 1989). It's more difficult to understand and implement correctly (Multi-Paxos is required for practical use). Two phases:

1. **Prepare phase**: Proposer sends `Prepare(n)` to quorum. Acceptors respond with highest ballot they've already accepted.
2. **Accept phase**: Proposer sends `Accept(n, v)` with the value from the highest-ballot response (or its own value if no previous). Acceptors accept if they haven't promised a higher ballot.

**Used by**: Google Chubby, Apache Zookeeper (Zab is similar), Google Spanner (Paxos Groups per shard).

### Zab (ZooKeeper Atomic Broadcast)

Similar to Paxos/Raft but optimized for ZooKeeper's leader-based model. Uses epoch numbers instead of terms. Guarantees total order of transactions and that no committed transaction is lost.

---

## Partitioning (Sharding)

### Consistent Hashing

Place nodes and keys on a virtual ring (0 to 2^32). A key is assigned to the first node clockwise from its hash position.

**Virtual nodes (vnodes)**: Each physical node gets multiple positions on the ring (e.g., 256 vnodes). This ensures uniform distribution even with heterogeneous nodes and simplifies rebalancing (a node departure only affects its immediate successors).

```
Hash ring: [0 ... 2^32]
Node A: positions 0, 500, 1000, ... (256 vnodes)
Node B: positions 250, 750, 1250, ...
Key "user:alice" hashes to 480 → assigned to Node B (first node clockwise from 480)
```

**Hot spot mitigation**: If certain keys are disproportionately hot (celebrity users, viral content), consistent hashing doesn't help. Solutions:
- Append random suffix (key → `key_1`, `key_2`, ..., `key_N`) and distribute writes; aggregate reads
- Dedicated "celebrity" shard with higher capacity

### Range Partitioning

Keys within a range go to the same shard (e.g., user IDs 1–1M → shard 1, 1M–2M → shard 2). Simple queries with range scans stay within one shard. But: sequential key insertion causes hot shards (all writes to last shard). Used by HBase, Google Spanner, CockroachDB.

### Directory-Based Partitioning

A lookup service (directory) maps each key to a shard. Maximum flexibility — any distribution strategy. But: directory is a SPOF and bottleneck. Requires highly available, fast lookup service (cache it).

---

## Replication Strategies

### Leader-Follower (Primary-Replica)

Single leader accepts all writes. Followers replicate asynchronously (default) or synchronously (one or all).

- **Asynchronous replication**: Low write latency; risk of data loss if leader fails before replication completes (RPO > 0)
- **Synchronous replication**: Zero data loss; write latency = max(follower latency); leader blocks until at least one sync follower acknowledges
- **Semi-sync (MySQL)**: One synchronous follower + N asynchronous — good balance

**Replication lag**: Followers can lag seconds to minutes under heavy write load. Reads from followers may return stale data. PostgreSQL's `pg_stat_replication` shows lag; `pg_replication_slot` prevents WAL deletion for slow followers (use with caution — can fill disk).

### Multi-Leader (Multi-Primary)

Multiple nodes accept writes. Reduces write latency for geographically distributed users. But: **write conflicts** are inevitable.

Conflict resolution strategies:
- **Last Write Wins (LWW)**: Use wall-clock timestamp — but clocks are unreliable (NTP drift, clock skew)
- **Causal versioning**: Use vector clocks or Lamport timestamps to detect causally concurrent writes
- **Application-level merge**: CRDTs (Conflict-free Replicated Data Types) — sets, counters, maps that merge deterministically
- **User prompt**: Last resort — show user both versions and ask them to resolve

### Leaderless (Dynamo-Style)

Any node accepts writes. Quorum reads and writes: with N replicas, require W writes and R reads such that W + R > N.

- N=3, W=2, R=2: tolerates 1 node failure for both reads and writes
- N=3, W=3, R=1: strong consistency on reads, but writes fail if any node down
- N=3, W=1, R=3: fast writes, expensive reads

**Read repair**: When a read fetches from R nodes and detects stale values, the coordinator writes the latest value back to stale nodes.

**Anti-entropy**: Background process compares replicas using Merkle trees and repairs divergence.

---

## Event Sourcing

Instead of storing current state, store the sequence of events that led to it. State is derived by replaying events.

```
Events:
1. OrderCreated { orderId: "O1", userId: "U1", items: [...] }
2. PaymentReceived { orderId: "O1", amount: 99.99 }
3. OrderShipped { orderId: "O1", trackingId: "TRK123" }

Current state = replay of events 1+2+3
```

### Snapshots

Replay of 10M events is slow. Periodically snapshot state. On load: fetch latest snapshot + replay events after snapshot version.

### Schema Evolution

Events are immutable — you cannot change past events. Handle schema changes with:
- **Weak schema**: store events as JSON, tolerate missing fields with defaults
- **Upcasters**: transform old event versions to current version during read
- **New event types**: add new events rather than modifying old ones

### Pitfalls

- Large aggregates with thousands of events have slow cold reads — snapshot more frequently
- Projections can diverge if event replay is not idempotent — ensure at-least-once delivery with idempotency keys
- Debugging production bugs requires replaying events to reproduce state — build replay tooling from day one

---

## CQRS (Command Query Responsibility Segregation)

Separate the write model (commands) from the read model (queries). Commands go to the write database; events trigger updates to read-optimized projections.

```
Client → Command API → Write DB (normalized) → Domain Events → Projections
Client → Query API  → Read DB (denormalized, optimized per view)
```

**When CQRS adds value**: High read/write ratio difference; complex read projections; different scaling requirements for reads vs writes.

**When CQRS adds complexity without value**: Simple CRUD; small teams; systems without complex query requirements.

**Eventual consistency lag**: The read model lags behind the write model by milliseconds to seconds. Handle with:
- Optimistic UI updates (update local state immediately, rollback on error)
- Polling with version check
- WebSocket push when projection is updated

---

## Saga Pattern

Long-lived business transactions spanning multiple services, where distributed 2PC is too heavyweight.

### Choreography Saga

Each service publishes events; downstream services subscribe and react. No central coordinator.

```
OrderService → OrderCreated event
  → InventoryService reserves stock → StockReserved event
    → PaymentService charges card → PaymentCompleted event
      → ShippingService ships → OrderFulfilled event

On failure:
PaymentService fails → PaymentFailed event
  → InventoryService releases stock → StockReleased event
    → OrderService marks order failed
```

- **Pro**: Loose coupling, no SPOF
- **Con**: Difficult to track saga state, implicit flow hard to visualize, complex compensation logic

### Orchestration Saga

A central Saga Orchestrator tells each service what to do and listens for responses.

```
OrderOrchestrator:
  1. Reserve inventory → await StockReserved / StockFailed
  2. Charge payment → await PaymentCompleted / PaymentFailed
  3. Ship order → await ShipmentCreated

On PaymentFailed:
  → Send ReleaseStock command to InventoryService
  → Mark order as cancelled
```

- **Pro**: Explicit flow, easy to track, centralized error handling
- **Con**: Orchestrator is a potential SPOF; tight coupling to orchestrator

---

## Outbox Pattern + CDC

Solves the dual-write problem: writing to DB and publishing an event atomically.

```
Within the same DB transaction:
  INSERT INTO orders (id, ...) VALUES (...);
  INSERT INTO outbox (event_type, payload) VALUES ('OrderCreated', '{"id": ...}');
COMMIT;

CDC (Debezium) reads the outbox table from the transaction log (WAL in PostgreSQL):
  → Publishes event to Kafka
  → Marks outbox row as processed (or delete)
```

**Debezium PostgreSQL connector**: Reads WAL via logical replication slot. Configure `plugin.name=pgoutput` (native PostgreSQL) or `wal2json`. Requires `wal_level = logical` in `postgresql.conf`.

**Exactly-once delivery**: Outbox provides at-least-once delivery (event can be re-read if Debezium restarts). Consumers must be idempotent — check `event_id` before processing.

---

## Service Mesh: Istio + Envoy

### Architecture

```
Control Plane (Istiod):
  - Pilot: pushes routing configs to Envoy sidecars via xDS APIs
  - Citadel: issues mTLS certificates (SPIFFE SVIDs)
  - Galley: validates and distributes Istio config

Data Plane (Envoy sidecars):
  - Intercept all traffic in/out of pods (iptables redirect)
  - Enforce mTLS, load balancing, retries, circuit breakers, tracing
```

### Traffic Management

```yaml
# VirtualService: route 10% of traffic to v2 (canary)
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: product-service
spec:
  http:
  - route:
    - destination:
        host: product-service
        subset: v1
      weight: 90
    - destination:
        host: product-service
        subset: v2
      weight: 10
```

### Fault Injection (Chaos Engineering in Staging)

```yaml
# Inject 5 second delay for 10% of requests to test timeout handling
fault:
  delay:
    percentage:
      value: 10.0
    fixedDelay: 5s
```

---

## API Gateway Patterns

### Functions

- **Authentication offload**: Validate JWT/API key before request reaches services; services trust X-User-Id header set by gateway
- **Rate limiting**: Centralized; per-user, per-endpoint, per-plan
- **Request transformation**: Header injection, request/response mapping, versioning translation
- **Fan-out**: Single client request → parallel calls to multiple services → aggregate response
- **BFF (Backend for Frontend)**: Specialized gateway per client type (mobile BFF, web BFF) — returns exactly the data needed by each client

### L4 vs L7 Load Balancing

- **L4 (transport layer)**: Routes based on IP + TCP port. Fast, low overhead. Cannot route based on HTTP path or headers. Examples: AWS NLB, HAProxy in TCP mode.
- **L7 (application layer)**: Routes based on HTTP path, host, headers, cookies. Enables path-based routing, sticky sessions via cookie, content-based routing. Examples: AWS ALB, NGINX, Envoy, Traefik.

### Load Balancing Algorithms

- **Round-robin**: Simple rotation; ignores server load
- **Weighted round-robin**: Assign traffic proportional to server capacity
- **Least connections**: Route to server with fewest active connections; better for heterogeneous request durations
- **Consistent hashing**: Same client always goes to same server (stateful applications, caching locality); handles server addition/removal gracefully
- **Random with two choices (Power of Two)**: Pick two random servers, route to the less loaded — approaches optimal distribution at scale with minimal coordination

---

## Database Selection Guide

| Database | When to Use | When NOT to Use |
|---|---|---|
| **PostgreSQL** | OLTP, complex queries, ACID transactions, JSON+relational hybrid, up to ~10TB | Need horizontal write scaling, column-oriented analytics |
| **MySQL (InnoDB)** | OLTP, simple workloads, legacy compatibility | Complex queries, partial index, advanced JSONB operations |
| **MongoDB** | Flexible schema, document-oriented data, horizontal scaling | Strong consistency requirements, complex multi-document transactions |
| **Cassandra** | High write throughput, time-series, wide-column, global multi-DC writes | Complex queries, secondary indexes at scale, transactions |
| **DynamoDB** | Serverless, known access patterns, < 400KB item size, AWS-native | Ad-hoc queries, complex aggregations, vendor independence |
| **Redis** | Caching, pub/sub, rate limiting, session store, leaderboards | Primary store for large datasets, complex querying |
| **ClickHouse** | Analytics, OLAP, log storage, aggregations over billions of rows | OLTP, frequent updates/deletes, row-level transactions |
| **Neo4j** | Graph traversals, social networks, recommendation engines | Non-graph workloads, high write throughput |
| **Elasticsearch** | Full-text search, log analytics, geospatial queries | Primary source of truth, transactions, high-write-rate primary store |

---

## System Design Walkthroughs

### URL Shortener (e.g., bit.ly)

**Requirements**: 100M URLs shortened/day; 10B redirects/day; 5 year retention; ~90% read-heavy.

**QPS**: Write: 100M/86400 ≈ 1,200 QPS. Read: 10B/86400 ≈ 116,000 QPS.

**Short ID generation**: Base62 encoding of an auto-increment counter (Snowflake ID), or hash (SHA256 → take first 7 characters → collision check). For distributed generation without coordination: pre-allocate ranges of counters to each server from a central Zookeeper counter.

**Storage**: 1 URL record ≈ 500 bytes. 100M URLs/day × 365 × 5 = 182B records × 500 bytes ≈ 90 TB.

**Read path**: Client → CDN (cache hot redirects, no DB hit) → API Gateway → Web Servers → Redis Cache → PostgreSQL (primary read replica for cold lookups).

**Write path**: Client → API → ID Generator → PostgreSQL write primary → invalidate/warm cache.

### Rate Limiter Design

**Algorithms**: Sliding window log (exact, memory-heavy), sliding window counter (approximate, efficient), token bucket (bursting allowed).

**Redis sliding window counter**:
```
On each request for (userId, endpoint):
  key = "ratelimit:{userId}:{endpoint}:{minuteTimestamp}"
  count = INCR key
  EXPIRE key 60
  if count > limit: reject
  else: allow
```

**Distributed rate limiter**: Store state in Redis (shared across all API servers). Use Lua scripts for atomicity (INCR + EXPIRE in one atomic operation).

### Distributed Cache (Memcached/Redis Clone)

**Consistent hashing** to distribute keys across cache nodes. **LRU eviction** when memory full. **Replication** for availability (active-passive or Raft). **Client-side sharding** or **proxy layer** (Twemproxy/Nutcracker).

### Social Media Feed (Twitter/Instagram)

**Fan-out on write (push model)**: When user A posts, write to all followers' feed caches immediately.
- **Pro**: Read is O(1) — just read from cache
- **Con**: Celebrity with 50M followers = 50M cache writes; high write amplification

**Fan-out on read (pull model)**: When user reads feed, fetch posts from all followees, merge, sort.
- **Pro**: No write amplification
- **Con**: Read is expensive for users with many followees

**Hybrid**: Fan-out on write for regular users (<10k followers), fan-out on read for celebrities. Merge at read time.

---

## CDN Architecture

### Origin Pull (Lazy)

CDN edge node caches content on first request; fetches from origin on cache miss. Zero setup. Stale content until TTL expires or manual purge.

### Origin Push (Active)

Publisher pushes content to CDN nodes before first request. Useful for large media files, software releases. Requires CDN API integration.

### Cache Invalidation

```bash
# Cloudflare: purge specific URL
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "Authorization: Bearer {token}" \
  -d '{"files": ["https://example.com/image.jpg"]}'

# AWS CloudFront: create invalidation
aws cloudfront create-invalidation \
  --distribution-id ABCDEF \
  --paths "/api/products/*"
```

**Cache-busting via URL versioning** is more reliable than invalidation: `https://cdn.example.com/main.abc123.js` — content hash in filename, served with long max-age, zero invalidation needed.

---

## Distributed Tracing

**OpenTelemetry** is the standard. Every service adds trace context to outbound calls (W3C TraceContext headers: `traceparent`, `tracestate`).

```javascript
// Node.js: auto-instrumentation
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-grpc');

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({ url: 'http://otel-collector:4317' }),
  instrumentations: [getNodeAutoInstrumentations()],
});
sdk.start();
```

Backends: Jaeger, Zipkin, Tempo (Grafana), AWS X-Ray, Honeycomb.

**What distributed tracing shows**: Full request lifecycle across services; which service introduced latency; cascading failures; fan-out patterns.

---

## Anti-Hallucination Protocol

**Verify before asserting:**
1. CAP theorem was proven by Eric Brewer and Gilbert/Lynch (2002). The theorem applies to distributed systems — single-node systems are not subject to partition tolerance considerations.
2. Consistent hashing was introduced by Karger et al. (1997, MIT). Virtual nodes are a common extension, not part of the original paper.
3. Raft is from the 2014 paper "In Search of an Understandable Consensus Algorithm" by Ongaro and Ousterhout — verify algorithm details against the paper at `raft.github.io`
4. Cassandra uses last-write-wins (LWW) with wall-clock timestamps by default — not vector clocks (which are optional and not the default). Never claim Cassandra uses vector clocks by default.
5. PostgreSQL WAL level for CDC must be `logical` (not `replica` or `minimal`). Verify with `SHOW wal_level;`
6. Debezium PostgreSQL connector uses `pgoutput` (native, no plugin install needed for PG 10+) or `wal2json` (requires separate installation). Do not claim `wal2json` is the only option.
7. DynamoDB item size limit is 400KB — this is documented on the AWS DynamoDB quotas page and is a hard limit, not a soft limit.
8. OpenTelemetry W3C TraceContext headers are `traceparent` and `tracestate` — not `X-Trace-Id` (that's Zipkin's old format) and not `X-B3-TraceId` (Zipkin's B3 format).
9. Redis Cluster uses hash slots (16384 total) for partitioning — NOT consistent hashing. This is a documented design decision by Redis.
10. PACELC was proposed by Daniel J. Abadi (2012) — it extends CAP, not contradicts it.

---

## Self-Review Checklist

Before presenting any systems design, verify:

- [ ] **Back-of-envelope done**: QPS, storage, bandwidth estimated before drawing architecture; stated explicitly with assumptions
- [ ] **CAP/consistency choice stated**: What consistency model does each data store provide? What is the application-level consistency guarantee?
- [ ] **Single points of failure identified**: Every box in the diagram — what happens if it fails? Is there HA/failover?
- [ ] **Data partitioning strategy**: How is data partitioned? What is the rebalancing strategy when nodes are added/removed?
- [ ] **Replication strategy**: How many replicas? Sync or async? What is the RPO (data loss on failure)?
- [ ] **Cache invalidation**: When data changes in the DB, how does the cache get invalidated? TTL only? Event-driven?
- [ ] **Failure modes documented**: Network partition, node failure, disk failure, thundering herd, hot spot — each addressed
- [ ] **Read vs write path separated**: Clearly explain the read path and write path independently
- [ ] **Async vs sync**: Every inter-service call — is it synchronous (latency chain) or asynchronous (queue, event)?
- [ ] **Idempotency of operations**: Can a request be retried safely? What prevents double processing of events?
- [ ] **Monitoring strategy**: What metrics are emitted? What alerts are set? How is a silent failure detected?
- [ ] **Database chosen with justification**: Not "I'll use PostgreSQL" but "PostgreSQL because we need ACID transactions, complex queries, and < 5TB data; we don't need horizontal write sharding at this scale"
- [ ] **Load balancing algorithm justified**: Round-robin for stateless; consistent hashing for cache/stateful
- [ ] **Numbers checked**: Does the design actually handle the stated QPS/storage? Do the numbers work?
