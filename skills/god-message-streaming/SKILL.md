---
name: god-message-streaming
description: "God-level messaging and event streaming skill covering Apache Kafka (producer/consumer internals, partitioning, replication, exactly-once semantics, Kafka Streams, ksqlDB, schema registry with Avro/Protobuf), RabbitMQ (exchanges, queues, bindings, dead letter exchanges, quorum queues), AWS SQS/SNS (standard vs FIFO, visibility timeout, DLQ, fan-out pattern), NATS (JetStream, pub/sub, request/reply, key-value), Apache Pulsar (multi-tenancy, geo-replication, tiered storage), and the engineering truth that choosing the wrong messaging system is a decision you will regret at 2am under production load."
metadata:
  version: "1.0.0"
---

# God-Level Message Streaming Skill

## Researcher-Warrior Mandate

You are an expert practitioner who has debugged consumer group rebalancing storms at 2am, wrestled with exactly-once semantics across distributed brokers, and designed fan-out architectures that survived traffic spikes. You never hallucinate configuration values. You never present theoretical knowledge as equivalent to production-verified knowledge. Every recommendation you make is grounded in documented system behavior and known operational tradeoffs.

**Anti-Hallucination Rules:**
- Every specific configuration value must be traceable to official documentation (Apache Kafka docs, AWS docs, NATS docs, RabbitMQ docs)
- When quoting defaults, say so explicitly: "default is X, tune based on Y"
- Never invent behavior — if unsure about an edge case, say "verify this in the specific version you deploy"
- If a feature is version-gated, state the minimum version
- Distinguish between Kafka (Apache open source), Confluent Platform, and AWS MSK — they are not identical

---

## Mental Model: What Is a Message Broker?

A message broker is a **decoupling mechanism** between producers and consumers. Producers do not need to know who consumes their messages, how many consumers exist, or whether consumers are currently running. The broker provides **temporal decoupling** (producer and consumer need not be simultaneously available), **spatial decoupling** (they need not know each other's location), and **semantic decoupling** (they communicate via contracts, not direct calls).

The three primitives of messaging:
1. **Point-to-point** (queue): one message → one consumer. Used for task distribution, work queues.
2. **Publish-subscribe** (topic/fanout): one message → many consumers. Used for event broadcast, notifications.
3. **Request-reply**: producer sends message, waits for correlated response. Implemented over async infrastructure for temporal decoupling.

Choosing the wrong primitive destroys correctness: a fanout system accidentally used point-to-point loses messages; a point-to-point system used where fanout was needed silently drops events from downstream systems.

---

## Apache Kafka: The Definitive Guide

### Fundamental Data Model

A **topic** is an ordered, partitioned, replicated log. This is not a metaphor — it is exactly what it is. Messages are appended to the end of the log, never removed by consumption. Consumers track their position via an **offset** — an integer representing position in the partition log. Offsets are stored in a Kafka topic called `__consumer_offsets`.

```
Topic: "orders"
Partition 0: [msg@0] [msg@1] [msg@2] [msg@3] ...
Partition 1: [msg@0] [msg@1] [msg@2] ...
Partition 2: [msg@0] [msg@1] ...
```

Key properties:
- Messages within a partition are **strictly ordered**
- Messages across partitions are **not ordered** — this is a design constraint you must internalize
- Messages are **immutable** — never edited after written
- Retention is **time-based or size-based**, not consumption-based (consumers can re-read)
- Offset is a **durable position marker** — it is per-partition, per-consumer-group

### Partitioning Strategy

Partition selection happens at the producer. The partition determines which broker's leader receives the write, which consumer in a group processes the message, and whether ordering is preserved.

**Key-based partitioning** (default when key is provided):
```java
// Key → hash → partition number (modulo numPartitions)
partition = Math.abs(murmur2(key)) % numPartitions
```
- Same key → same partition → ordering guarantee for that key
- Use case: user events partitioned by userId — all events for a user are ordered
- Risk: hot partition if key distribution is uneven (one userId generating 80% of events)

**Round-robin** (no key, or StickyPartitioner with batching):
- Messages distributed evenly across all partitions
- Maximum throughput, no ordering guarantee
- Kafka 2.4+ uses `StickyPartitioner` by default — batches all records for a short period to the same partition before rotating (reduces small batch overhead)

**Custom partitioner**: implement `org.apache.kafka.clients.producer.Partitioner` interface. Use when business logic determines placement (e.g., "VIP customers always to partition 0 for priority processing").

**Partition count is a one-way door**: you can increase partition count but cannot reduce it without recreating the topic (which requires migrating consumer group offsets). Plan partition count based on:
- Max desired consumer parallelism (1 consumer per partition max)
- Expected throughput (each partition can handle ~10MB/s per broker, varies heavily with hardware)
- Key cardinality (at least 2× the number of consumers to avoid uneven assignment)
- Rule of thumb: start conservative (8–16), increase based on measured throughput — do not over-partition

### Replication and Durability

**Replication factor** of 3 means each partition has 1 leader and 2 followers. The leader handles all reads and writes. Followers replicate from the leader and are ready to take over on failure.

**ISR (In-Sync Replicas)**: the set of replicas that are currently caught up to the leader within `replica.lag.time.max.ms` (default 30 seconds). A follower that falls behind is removed from ISR. ISR shrinkage is a warning sign — monitor `UnderReplicatedPartitions` metric.

**Durability guarantee** with `acks=all` + `min.insync.replicas=2`:
- Producer waits for all ISR replicas to confirm the write
- `min.insync.replicas=2` means the leader will reject writes if fewer than 2 replicas are in ISR (prevents data loss if the leader fails immediately after acknowledging)
- This is the only configuration that guarantees durability with replication factor 3
- Setting `min.insync.replicas=1` with `acks=all` degrades to `acks=1` behavior when 2 followers are behind

**Never use `replication.factor=1` in production** — single point of failure, no recovery on broker loss.

### Producer Configuration (Production Reference)

```properties
# Durability — do not compromise
acks=all                              # Wait for all ISR replicas
enable.idempotence=true               # Exactly-once per partition, dedup by producer ID + sequence
retries=2147483647                    # MAX_INT — retry indefinitely (bounded by delivery.timeout.ms)
delivery.timeout.ms=120000            # 2 minutes total delivery budget
max.in.flight.requests.per.connection=5  # Up to 5 with idempotence (safe); set to 1 without idempotence for ordering

# Throughput tuning
batch.size=65536                      # 64KB batch (default 16384) — larger batches = better throughput
linger.ms=5                          # Wait up to 5ms to fill batch (default 0 = send immediately)
compression.type=snappy              # snappy: good balance of CPU and compression ratio
                                     # lz4: lower latency, slightly worse compression
                                     # gzip: best compression, higher CPU — for bandwidth-constrained links
                                     # zstd: (Kafka 2.1+) best compression ratio with reasonable CPU

# Buffer management
buffer.memory=67108864               # 64MB producer buffer (default 32MB)
max.block.ms=60000                   # Block send() for 60s if buffer full before throwing exception
```

**Idempotent producer**: assigned a `ProducerID` (PID) by the broker. Each message carries a monotonically increasing sequence number per partition. Broker deduplicates retries by (PID, partition, sequence). Sequence gaps trigger `OutOfOrderSequenceException`.

### Consumer Configuration (Production Reference)

```properties
# Group identity
group.id=my-consumer-group           # Required — all consumers with same ID form one group

# Offset behavior
auto.offset.reset=earliest           # Start from beginning if no committed offset exists
                                     # latest = start from newest messages (miss historical)
                                     # none = throw exception if no offset (safe for prod if you set offsets manually)
enable.auto.commit=false             # NEVER true in production — manual commit for exactly-once
auto.commit.interval.ms=5000        # Only relevant when auto.commit=true — do not rely on this

# Polling
max.poll.records=500                 # Max records per poll() call — tune based on processing time
max.poll.interval.ms=300000          # 5 min max between polls before consumer considered dead
fetch.min.bytes=1                    # Fetch at least 1 byte (default — triggers fetch immediately)
fetch.max.wait.ms=500               # Max wait for fetch.min.bytes to accumulate

# Liveness
session.timeout.ms=45000            # Broker considers consumer dead after 45s without heartbeat
heartbeat.interval.ms=15000         # Send heartbeat every 15s (must be < session.timeout.ms / 3)
# Rule: session.timeout.ms >= 3 × heartbeat.interval.ms
```

**Consumer group mechanics**: partition assignment — each partition is assigned to exactly one consumer in a group. Adding consumers beyond partition count yields idle consumers. Rebalancing occurs when: new consumer joins, consumer leaves/crashes, partition count changes, subscription pattern changes.

**Rebalancing strategies**:
- **Eager (Stop-the-World)**: all consumers revoke all partitions, then re-assign. Simple, causes pause. Default for older clients.
- **Cooperative (Incremental)**: only reassigned partitions are revoked. No full pause. Enabled with `CooperativeStickyAssignor` (Kafka 2.4+, default in 3.x). **Use this in production.**

### Exactly-Once Semantics (EOS)

Three levels of delivery guarantee:
1. **At-most-once**: producer doesn't retry, consumer commits before processing → possible message loss
2. **At-least-once**: producer retries, consumer commits after processing → possible duplicates
3. **Exactly-once**: no loss, no duplicates — requires both idempotent producer AND transactional API

**Idempotent producer** (within a session, per partition): handles retries safely. Does NOT span crashes — new session = new PID.

**Transactional API** (cross-partition atomic writes):
```java
producer.initTransactions();
// In the processing loop:
producer.beginTransaction();
try {
    producer.send(new ProducerRecord<>("output-topic", key, value));
    // Commit consumer offset atomically with the produce
    producer.sendOffsetsToTransaction(offsets, consumerGroupMetadata);
    producer.commitTransaction();
} catch (Exception e) {
    producer.abortTransaction();
}
```

**Read-process-write pattern**: consume from topic A, process, write to topic B, and commit offsets — atomically. Consumer must set `isolation.level=read_committed` to not see in-flight or aborted transactions.

**EOS overhead**: transactions add ~20ms latency overhead (transaction coordinator round trips). Not free — use only where duplicate processing has real consequences.

### Kafka Streams

Kafka Streams is a **Java library** (not a separate cluster) for building stream processing applications that read from and write to Kafka.

**Stateless operations** (no state maintained):
- `map(KeyValueMapper)` — transform key and value
- `filter(Predicate)` — remove records matching condition
- `flatMap(KeyValueMapper)` — one record → N records
- `branch(Predicate...)` — split stream into multiple streams
- `merge(KStream)` — combine two streams

**Stateful operations** (maintain state in RocksDB state stores):
- `groupBy(KeyValueMapper).count()` — count by key
- `groupBy(KeyValueMapper).aggregate(Initializer, Aggregator)` — arbitrary accumulation
- `windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(5)))` — time-windowed aggregations
- `join(KStream, ValueJoiner, JoinWindows)` — stream-stream join within time window
- `leftJoin(KTable, ValueJoiner)` — stream-table join (table is the reference data)

**KStream vs KTable**:
- `KStream`: unbounded sequence of records. Every record is an event (fact). Append semantics.
- `KTable`: changelog stream representing the latest value per key. Upsert semantics. Backed by compacted topic.
- `GlobalKTable`: replicated to all app instances (small reference tables). No partitioning — all instances see all data.

**Interactive queries**: access RocksDB state stores from outside the Kafka Streams app (for serving query results). Use `KafkaStreams.store(StoreQueryParameters)` to get a `ReadOnlyKeyValueStore`. Enable `application.server` config for distributed queries across instances.

**State store types**: in-memory (fast, not durable), persistent RocksDB (default, survives restart), custom. Changelog topic backs RocksDB for recovery.

### ksqlDB

ksqlDB is a **streaming SQL engine** built on Kafka Streams. It runs as a separate server cluster. Use it for:
- Real-time ETL (filter, transform, enrich streams with SQL)
- Event-driven microservices that need stream processing without writing Java
- Materialized views over Kafka topics (pull queries for point lookups, push queries for streaming results)

```sql
-- Create stream from Kafka topic
CREATE STREAM orders_stream (
  order_id VARCHAR KEY,
  user_id VARCHAR,
  amount DOUBLE,
  status VARCHAR
) WITH (KAFKA_TOPIC='orders', VALUE_FORMAT='AVRO');

-- Create materialized table (aggregation)
CREATE TABLE orders_by_user AS
  SELECT user_id, COUNT(*) AS order_count, SUM(amount) AS total
  FROM orders_stream
  GROUP BY user_id
  EMIT CHANGES;

-- Pull query (point-in-time lookup)
SELECT * FROM orders_by_user WHERE user_id = 'u123';
```

ksqlDB materializes state in its own internal Kafka topics and RocksDB stores. Not for OLAP — use for low-latency aggregations over recent data.

### Schema Registry (Confluent)

**Why schemas matter**: without a schema contract, producers can change message format and silently break consumers. Schema Registry enforces a contract and manages schema evolution.

**Supported formats**:
- **Avro**: binary, compact, schema embedded in registry (not in message). Industry standard for Kafka. Good tooling.
- **Protobuf**: binary, better language support, forward-compatible by default. Growing adoption.
- **JSON Schema**: human-readable, more overhead, weaker type system. Use when humans need to read raw messages.

**Compatibility modes** (set per subject — a subject = topic name + `-value` or `-key`):
- `BACKWARD` (default): new schema can read data written by previous schema. Consumers can upgrade before producers. Safe for adding optional fields with defaults, deleting required fields.
- `FORWARD`: previous schema can read data written by new schema. Producers can upgrade before consumers. Safe for adding required fields (old consumers ignore unknown fields in Avro/Protobuf).
- `FULL`: both BACKWARD and FORWARD. Safest, most restrictive.
- `NONE`: no compatibility check. Danger zone.

**Schema evolution rules for Avro BACKWARD compatibility**:
- ✅ Add optional field with default value
- ✅ Remove field with no default (consumers that had the field will get the default)
- ❌ Remove field with no default and the field was required
- ❌ Change field type (int → string breaks binary encoding)
- ❌ Rename field without alias

**Upcasting**: Kafka Streams mechanism to upgrade old events to new schema format during replay. Required for event sourcing patterns with long retention.

---

## RabbitMQ: AMQP Mastery

### Architecture: Exchanges, Queues, Bindings

Messages flow: **Producer → Exchange → (Binding + Routing Key) → Queue → Consumer**

Exchanges are routing engines, not storage. Queues are the actual message stores.

**Exchange types**:

| Type | Routing Logic | Use Case |
|------|---------------|----------|
| `direct` | Exact routing key match | Task distribution, specific service targeting |
| `fanout` | Ignores routing key — delivers to all bound queues | Broadcast, cache invalidation |
| `topic` | Wildcard routing key (`*` = one word, `#` = zero or more words) | Selective pub/sub by category |
| `headers` | Match on message header attributes (not routing key) | Complex routing by metadata |

```python
# Topic exchange example
channel.exchange_declare('events', 'topic')
# Bind queue to receive orders.*
channel.queue_bind('order-processor', 'events', 'orders.*')
# Bind queue to receive all audit events
channel.queue_bind('audit-log', 'events', '#')
# Publish to orders.created — received by order-processor AND audit-log
channel.basic_publish('events', 'orders.created', body)
```

### Dead Letter Exchanges (DLX)

A dead letter exchange receives messages that are:
- Rejected by a consumer with `basic.nack` or `basic.reject` and `requeue=false`
- Expired (TTL exceeded on queue or message)
- Queue length limit exceeded

```python
# Declare queue with DLX
channel.queue_declare('orders', arguments={
    'x-dead-letter-exchange': 'dlx',
    'x-dead-letter-routing-key': 'orders.dead',
    'x-message-ttl': 30000,  # 30s TTL
    'x-max-length': 10000    # max 10k messages
})
channel.exchange_declare('dlx', 'direct')
channel.queue_declare('orders-dead')
channel.queue_bind('orders-dead', 'dlx', 'orders.dead')
```

**Poison message handling**: a message that always fails processing will loop forever if requeued. Use DLX with a retry queue (with TTL) that republishes to the original queue after delay. After N retries (tracked via `x-death` header), route to permanent DLQ for manual investigation.

### Quorum Queues

Classic mirrored queues (deprecated in 3.x) had split-brain issues. **Quorum queues** (RabbitMQ 3.8+) use the Raft consensus algorithm for replication:
- Writes confirmed only after majority of replicas (quorum) acknowledge
- No split-brain — only the quorum leader accepts writes
- Automatic recovery without data loss on node failure
- **Use quorum queues for any durable, critical queue in production**

```python
channel.queue_declare('critical-orders', arguments={
    'x-queue-type': 'quorum',
    'x-quorum-initial-group-size': 3  # Replicate to 3 nodes
})
```

Quorum queues do NOT support per-message TTL (only per-queue TTL), priorities, or some classic queue arguments. Check compatibility before migrating.

### Consumer Prefetch and Publisher Confirms

**Prefetch count** (`basic.qos`): how many unacked messages the broker sends to a consumer at once. Without prefetch, RabbitMQ will send all queued messages to the first consumer (unfair dispatch).

```python
channel.basic_qos(prefetch_count=10)  # Consumer buffers max 10 unacked messages
```
- Too low: consumer starves waiting for individual acks (high latency)
- Too high: slow consumers accumulate large backlogs in memory, reducing throughput of other consumers
- Tune based on processing time per message and memory constraints. Start with 10–50.

**Publisher confirms**: asynchronous acknowledgment that the broker has received and persisted the message. Without confirms, fire-and-forget has no durability guarantee.

```python
channel.confirm_select()  # Enable publisher confirms
channel.basic_publish('exchange', 'key', body, properties=pika.BasicProperties(delivery_mode=2))
channel.wait_for_confirms()  # Block until broker confirms
```

---

## AWS SQS and SNS

### SQS: Queue Fundamentals

**Visibility timeout**: after a consumer receives a message, it becomes invisible to other consumers for the visibility timeout duration. If the consumer does not delete the message before the timeout expires, the message becomes visible again and can be delivered to another consumer.

- Default visibility timeout: 30 seconds
- **Must be greater than your processing time** — if processing takes 45s but timeout is 30s, the message is reprocessed concurrently
- Extend with `ChangeMessageVisibility` for long-running jobs
- Maximum: 12 hours

**Standard vs FIFO queues**:

| Property | Standard | FIFO |
|----------|----------|------|
| Ordering | Best-effort | Strict FIFO per message group |
| Delivery | At-least-once | Exactly-once processing |
| Throughput | Nearly unlimited | 300 TPS (3,000 with batching) |
| Deduplication | No | Yes (5-min dedup window) |
| Cost | Lower | Higher |

**FIFO queues** require a `MessageGroupId` (ordering within a group) and optionally a `MessageDeduplicationId` (or content-based deduplication enabled). Use FIFO only when ordering and exactly-once matter — the throughput limit (300 TPS) is a hard constraint.

**Dead Letter Queue (DLQ)**: configure `maxReceiveCount` on the source queue. After a message is received N times without deletion, it moves to the DLQ. Monitor DLQ message count as a health signal. Investigate DLQ messages — they indicate processing failures.

**Long polling**: `ReceiveMessage` with `WaitTimeSeconds=20` (max). Without long polling (short polling), empty receives cost money and add latency. Long polling eliminates most empty receives. **Always use long polling in production.**

**Message attributes**: up to 10 metadata attributes per message. Use for filtering in SNS subscriptions, routing decisions, or passing metadata without inflating the message body.

### SNS: Fan-Out Pattern

SNS delivers to multiple subscribers simultaneously. Core fan-out pattern:
```
SNS Topic "order-events"
    ├── SQS Queue "order-fulfillment" (fulfillment service)
    ├── SQS Queue "order-analytics" (analytics pipeline)
    ├── SQS Queue "order-notifications" (email/push service)
    └── Lambda function (real-time fraud check)
```

Each subscriber gets an independent copy. Failure in one subscriber does not affect others.

**Message filtering** (subscription filter policies): reduce processing overhead by delivering only relevant messages to each subscriber.
```json
// Subscription filter policy — only receive messages where status = "completed"
{
  "status": ["completed"],
  "amount": [{"numeric": [">=", 100]}]
}
```

**SNS DLQ**: configure on the SNS subscription (not the SNS topic) for failed deliveries. SNS retries with exponential backoff before routing to DLQ.

**SNS FIFO + SQS FIFO**: for ordered fan-out to multiple consumers. SNS FIFO topics deliver to SQS FIFO queues only. Throughput limited to SQS FIFO limits.

---

## NATS and JetStream

### Core NATS: Pub/Sub

NATS is a **high-performance, low-latency** messaging system. Core NATS (without JetStream) is fire-and-forget — no persistence, no acknowledgment. A message is lost if no subscriber is listening.

```go
nc, _ := nats.Connect("nats://localhost:4222")

// Subscribe
nc.Subscribe("orders.created", func(msg *nats.Msg) {
    fmt.Println(string(msg.Data))
})

// Publish (fire-and-forget)
nc.Publish("orders.created", []byte(`{"order_id":"123"}`))
```

**Subject hierarchy**: `orders.created`, `orders.updated`, `orders.>` (wildcard for all orders subjects), `orders.*` (one token wildcard).

**Request-reply**: built-in, uses a reply subject.
```go
msg, err := nc.Request("inventory.check", []byte(`{"sku":"ABC"}`), 2*time.Second)
```
Server generates a unique inbox reply subject and routes the response back to the requestor.

### JetStream: Persistence and Delivery Guarantees

JetStream adds persistence, replay, and delivery guarantees to NATS. Requires JetStream-enabled server.

**Streams**: durable log of messages on subjects. Configure retention:
- `LimitsPolicy`: retain up to N messages or N bytes or N age — oldest purged first
- `InterestPolicy`: retain while at least one consumer is interested (like Kafka)
- `WorkQueuePolicy`: message deleted after acknowledged by one consumer (like SQS)

```go
js, _ := nc.JetStream()
js.AddStream(&nats.StreamConfig{
    Name:     "ORDERS",
    Subjects: []string{"orders.*"},
    MaxAge:   24 * time.Hour,
    Storage:  nats.FileStorage,  // or MemoryStorage
    Replicas: 3,                 // Raft-based replication
})
```

**Consumers** (durable subscribers with state):
- **Push consumer**: server pushes messages to subscriber. Higher throughput.
- **Pull consumer**: consumer explicitly requests messages. Better flow control, preferred for most cases.

```go
// Pull consumer
sub, _ := js.PullSubscribe("orders.*", "order-processor",
    nats.Durable("order-processor"),
    nats.AckExplicit(),
)
msgs, _ := sub.Fetch(10, nats.MaxWait(5*time.Second))
for _, msg := range msgs {
    // process
    msg.Ack()  // or msg.Nak() to redeliver, msg.Term() to never redeliver
}
```

**Exactly-once with JetStream**: use `Nats-Msg-Id` header for publisher-side deduplication (5-minute dedup window). Consumer side: `AckExplicit` + idempotent processing.

**Key-Value store on JetStream**: built-in KV store backed by a JetStream stream. Supports get, put, delete, watch (stream of changes to a key), purge. Use for config, coordination, lightweight state.

---

## Apache Pulsar: Multi-Tenancy and Geo-Replication

Pulsar separates serving (brokers) from storage (BookKeeper ledgers), enabling stateless brokers that scale independently.

**Multi-tenancy model**: `tenant/namespace/topic`. Tenants have their own authentication, quotas, and policies. Namespaces configure retention, replication, encryption, and TTL. This structure is first-class, unlike Kafka which has namespace-by-convention.

**Topic types**:
- **Persistent** (`persistent://tenant/namespace/topic`): backed by BookKeeper, replicated, durable
- **Non-persistent** (`non-persistent://...`): in-memory only, no durability, maximum throughput

**Subscription types** (Pulsar's analogue to consumer groups + queue models in one):
- `Exclusive`: single consumer
- `Failover`: one active consumer, failover to standby
- `Shared`: round-robin across consumers (like SQS)
- `Key_Shared`: same key → same consumer (like Kafka partitioning, but dynamic)

**Geo-replication**: built-in async replication between clusters in different regions. Configure at namespace level. Active-active or active-passive. Pulsar handles message deduplication across regions.

**Tiered storage**: offload older segments to object storage (S3, GCS, Azure Blob). BookKeeper holds recent data; object storage holds historical data. Transparent to consumers — Pulsar serves from either tier.

**When to choose Pulsar over Kafka**:
- Strong multi-tenancy requirements (multiple isolated teams/products on one cluster)
- Built-in geo-replication without external tools
- Mixed queue + pub-sub semantics (Key_Shared subscription)
- Tiered storage for very long retention periods
- When stateless brokers (independent scaling of compute and storage) matter

---

## Message Design Patterns

### Envelope Pattern

Wrap every message in an envelope with standard metadata:
```json
{
  "metadata": {
    "event_type": "order.created",
    "event_id": "uuid-v4",
    "event_version": "1",
    "source_service": "order-service",
    "timestamp": "2024-01-15T10:30:00Z",
    "correlation_id": "trace-id-from-upstream",
    "causation_id": "event-id-that-caused-this",
    "idempotency_key": "order-123-create"
  },
  "payload": {
    "order_id": "order-123",
    "user_id": "user-456",
    "amount": 99.99
  }
}
```

- `event_id`: unique message identifier for deduplication
- `correlation_id`: trace ID for distributed tracing — propagate from the incoming HTTP request
- `causation_id`: the `event_id` of the message that caused this message (event chain reconstruction)
- `idempotency_key`: business-level idempotency (same order, same operation = same key)
- `event_version`: for schema evolution — consumers route to correct handler by version

### Idempotent Consumer Pattern

Consumers MUST be idempotent because at-least-once delivery is the guarantee in most systems. Idempotency strategies:
1. **Natural idempotency**: the operation itself is safe to repeat (e.g., SET value = X is idempotent; INCREMENT is not)
2. **Idempotency table**: store processed `event_id` in DB. Before processing, check if already processed.
3. **Conditional write**: use optimistic locking / database upsert with conflict detection

```sql
-- Idempotency table approach
INSERT INTO processed_events (event_id, processed_at)
VALUES ($1, NOW())
ON CONFLICT (event_id) DO NOTHING;

-- If 0 rows inserted, this event was already processed — skip
```

### Schema Versioning Strategy

Never break consumers by changing message format. Version your events:
1. Add new optional fields (backward compatible)
2. Publish both old and new formats during migration period (dual-write)
3. Consumers migrate to new format
4. Stop publishing old format
5. Never remove fields without this sequence

---

## Cross-Domain Connections

**Kafka + CDC (Change Data Capture)**: Debezium is a Kafka Connect source connector that reads database transaction logs (PostgreSQL WAL, MySQL binlog) and publishes row-level change events to Kafka topics. This enables event-driven architectures that react to database changes without polling.

**SQS/SNS + Serverless**: Lambda can be triggered directly from SQS (batch window and batch size configurable). Lambda scales from 0 to concurrency limit = queue consumers. DLQ integration handles function failures. This is the canonical AWS serverless event-driven pattern.

**Message Streaming + ML**: Kafka is commonly used as the feature pipeline transport for ML systems. Feature values are computed from events and published to Kafka topics. A feature store (Feast, Tecton) consumes these topics and serves features at low latency for model inference. The same events that drive business logic also drive model training.

**Kafka + Microservices**: each microservice owns its topics (event ownership). The service publishes events when state changes. Other services subscribe. This is the event-driven microservices pattern — no synchronous coupling, no shared database.

---

## System Selection Guide

| Requirement | Recommended System |
|-------------|-------------------|
| High throughput event streaming, long retention, replay | Kafka |
| Complex routing, protocol flexibility (AMQP), task queues | RabbitMQ |
| AWS-native, serverless, simple operations | SQS/SNS |
| Ultra-low latency, cloud-native, simple ops, request-reply | NATS + JetStream |
| Multi-tenancy, geo-replication first-class, tiered storage | Pulsar |
| Ordered processing with deduplication | SQS FIFO or Kafka |
| Fan-out to many heterogeneous subscribers | SNS or Kafka with multiple consumer groups |

---

## Self-Review Checklist

Before submitting any message streaming design or recommendation, verify:

1. **Partition count** — have you considered the maximum consumer parallelism needed? Will you need to increase later (cannot decrease)?
2. **Replication factor** — is it 3 for production? Is `min.insync.replicas=2` set with `acks=all`?
3. **Idempotent producer** — is `enable.idempotence=true` set? Is `max.in.flight.requests.per.connection≤5`?
4. **Consumer commit strategy** — is `enable.auto.commit=false`? Are you committing offsets only after successful processing?
5. **Consumer liveness** — is `session.timeout.ms ≥ 3 × heartbeat.interval.ms`? Is `max.poll.interval.ms` large enough for your processing time?
6. **Rebalancing strategy** — are you using `CooperativeStickyAssignor` (Kafka 2.4+) to avoid stop-the-world rebalances?
7. **Schema registry** — is schema compatibility mode set? Is the schema registered before deploying new producers?
8. **Exactly-once** — if EOS is required, are you using transactions + `isolation.level=read_committed` on consumers?
9. **DLQ/DLX** — is there a dead letter destination for failed messages? Are you monitoring its depth?
10. **Visibility timeout** (SQS) — is the visibility timeout greater than the maximum processing time? Are you extending it for long-running jobs?
11. **FIFO necessity** — did you truly need FIFO ordering or just assumed? Are you within the 300 TPS limit?
12. **Prefetch count** (RabbitMQ) — is `basic.qos` set? Is it tuned for your processing time and memory?
13. **Publisher confirms** (RabbitMQ) — are you using publisher confirms for durability? Are Quorum queues used instead of classic?
14. **Message envelope** — does every message carry: `event_id`, `correlation_id`, `event_type`, `timestamp`?
15. **Idempotent consumers** — can your consumer safely process the same message twice? What is your deduplication strategy?

---

## Anti-Hallucination Reminders

- Kafka **does not** support message TTL natively per message (only log retention by time/size). Use a separate topic + consumer for delay queues.
- Kafka **cannot** decrease partition count — this is a hard limitation as of Kafka 3.x. Verify current release notes before advising otherwise.
- `acks=all` does not guarantee durability if `min.insync.replicas=1` — this combination is weaker than it appears.
- NATS Core (without JetStream) provides **no persistence** — messages are lost if no subscriber exists at publish time.
- RabbitMQ **quorum queues do not support** per-message TTL (only queue-level TTL). Verify feature support in your target RabbitMQ version.
- SQS FIFO is **300 TPS limit** (3,000 with high throughput mode and batching as of 2023 — verify current AWS limits).
- Pulsar's geo-replication is async by default — there is a replication lag. It does NOT provide synchronous multi-region writes without specific configuration.
- Always check the exact Kafka version when referencing features — Kafka 3.x has significant improvements over 2.x in rebalancing, EOS, and KRaft mode.
