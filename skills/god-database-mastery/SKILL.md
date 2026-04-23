---
name: god-database-mastery
description: "God-level database mastery covering SQL (PostgreSQL deep dive, MySQL differences), NoSQL (MongoDB, Cassandra, DynamoDB), NewSQL (CockroachDB, Spanner), caching (Redis deep dive — data structures, persistence, clustering, pub/sub), message streaming (Apache Kafka — architecture, partitioning, consumer groups, exactly-once semantics), Elasticsearch/OpenSearch (indexing, mapping, search relevance, aggregations), time-series (InfluxDB, TimescaleDB), graph databases (Neo4j), schema design, query optimization, indexing strategies, ACID vs BASE, CAP theorem, replication, sharding, and connection pooling. A developer who does not understand their database is a developer who will eventually bring it to its knees."
metadata:
  domain: "\"databases\""
  sources: " - \"Designing Data-Intensive Applications — Martin Kleppmann (O'Reilly, 2017)\" - \"PostgreSQL Documentation — postgresql.org/docs\" - \"MongoDB Documentation — docs.mongodb.com\" - \"Redis Documentation — redis.io/docs\" - \"Apache Kafka Documentation — kafka.apache.org/documentation\" - \"Cassandra Documentation — cassandra.apache.org/doc\""
  version: "\"1.0\""
  cross_domain: "''"
---

# God-Level Database Mastery

## Researcher-Warrior Mindset

You do not take the ORM's word for what SQL it generates. You run `EXPLAIN ANALYZE`. You do not assume the index is being used — you prove it. You read the slow query log. You know that every abstraction leaks, and at some point you will be debugging a production incident with a 3-second database lock hold, and the engineer who understood the query planner will fix it in 10 minutes while the engineer who trusted the ORM sits confused. Know your database at the level of its internals.

---

## Anti-Hallucination Rules

**NEVER fabricate:**
- PostgreSQL GUC parameter names — verify against `pg_settings` or official docs (e.g., `max_connections` not `max_db_connections`)
- Redis command names — `ZADD`, `ZRANGE`, `GEORADIUS` exist; invented commands do not
- Kafka configuration keys — `bootstrap.servers` not `bootstrap_servers` in producer config; verify Java vs Python client differences
- MongoDB aggregation stage names — `$match`, `$group`, `$lookup`, `$unwind`, `$project` are real; invented stages are not
- Cassandra consistency levels — ALL, QUORUM, LOCAL_QUORUM, ONE, LOCAL_ONE, EACH_QUORUM — verify per operation type
- CockroachDB/Spanner claimed behaviors — only state what is documented in official sources
- PgBouncer pool modes — session, transaction, statement — verify behavior of each

**ALWAYS verify:**
- PostgreSQL index types available in a given version — BRIN was added in 9.5, covering indexes (`INCLUDE`) in 11
- Redis data type command sets — LPOS added in Redis 6.0.6; Bloom Filter requires RedisBloom module
- Kafka exactly-once semantics versions — idempotent producer GA in 0.11; transactions GA in 0.11; exactly-once consumer in 2.5
- MySQL vs PostgreSQL syntax differences — UPSERT syntax differs (INSERT ... ON CONFLICT in PG, INSERT ... ON DUPLICATE KEY in MySQL)

---

## 1. ACID Properties

**Atomicity:** A transaction is all-or-nothing. Either all operations succeed and are committed, or none are applied. No partial writes visible to other transactions.

**Consistency:** A transaction brings the database from one valid state to another. All defined constraints (foreign keys, unique constraints, check constraints) hold after the transaction commits. Note: "Consistency" in ACID is enforced by the *application* defining valid states, not just the database.

**Isolation:** Concurrent transactions execute as if they were sequential. The level of isolation is tunable (Read Uncommitted → Read Committed → Repeatable Read → Serializable). Higher isolation = higher contention = lower throughput.

```
Isolation Level       | Dirty Read | Non-Repeatable Read | Phantom Read
----------------------|------------|---------------------|-------------
Read Uncommitted      | Possible   | Possible            | Possible
Read Committed        | Prevented  | Possible            | Possible
Repeatable Read       | Prevented  | Prevented           | Possible
Serializable          | Prevented  | Prevented           | Prevented

PostgreSQL default: Read Committed
MySQL InnoDB default: Repeatable Read
PostgreSQL SSI: true serializable via Serializable Snapshot Isolation
```

**Durability:** Once a transaction commits, it survives crashes. Achieved via WAL (Write-Ahead Log) in PostgreSQL — changes are written to the WAL before being applied to data pages, so they can be replayed after a crash.

**Cost of ACID:** Write amplification (WAL + heap writes), lock contention at high isolation levels, fsync overhead for durability. This is why high-throughput use cases often choose relaxed consistency.

**Which databases guarantee full ACID:**
- PostgreSQL: Full ACID, including true Serializable
- MySQL InnoDB: Full ACID (MyISAM does not)
- CockroachDB: Distributed ACID (serializable isolation by default)
- MongoDB: ACID for multi-document transactions since 4.0 (single-document operations are always atomic)
- Redis: Partial — MULTI/EXEC blocks are atomic but not durable by default without AOF fsync=always

---

## 2. BASE

**Basically Available:** The system guarantees availability (per the CAP theorem interpretation) — responds to every request, possibly with stale or partial data.

**Soft State:** State may change over time even without input, due to eventual consistency propagation.

**Eventually Consistent:** Given no new updates, all replicas will converge to the same value — eventually. The window could be milliseconds or seconds depending on the system.

**When BASE is acceptable:**
- User profile cache (slightly stale is fine — user doesn't care if their bio update takes 2s to propagate)
- Product catalog search results (showing yesterday's inventory count is acceptable)
- Social media timelines (eventual consistency is invisible to users)
- Analytics counters (exact count vs approximate count is often irrelevant)

**When BASE is dangerous:**
- Financial transactions (cannot have two debits from the same account proceed simultaneously)
- Inventory deduction (two users buying the last item must not both succeed)
- Authentication (a revoked token must not be accepted on any replica)
- Medical records (stale data can cause patient harm)

---

## 3. CAP Theorem and PACELC

**CAP Theorem (Brewer, 2000; formally proven by Gilbert and Lynch, 2002):**
In the presence of a network partition, a distributed system can provide either Consistency or Availability, but not both simultaneously.

**The key insight:** Partition tolerance is NOT optional — network partitions happen in any distributed system. The real choice is C or A during a partition.

```
CP Systems: Prefer consistency over availability during partitions
  HBase, Zookeeper, MongoDB (with majority write concern), 
  CockroachDB, etcd, Consul

AP Systems: Prefer availability over consistency during partitions
  Cassandra, DynamoDB (default), CouchDB, Riak,
  DNS, many CDNs
```

**PACELC Model (Abadi, 2012) — more practical than CAP:**
- **P**: If partition: choose A or C (same as CAP)
- **ELC**: Else (no partition): choose Latency or Consistency

```
PACELC classification:
  Cassandra: PA/EL — available during partition, low latency normally (tunable)
  DynamoDB: PA/EL — available, eventually consistent (tunable per operation)
  PostgreSQL: PC/EC — consistent during partition, consistent normally (single-node)
  CockroachDB: PC/EC — consistent always (serializable) at latency cost
  Spanner: PC/EC — global consistency via TrueTime
```

---

## 4. PostgreSQL Deep Dive

### MVCC (Multi-Version Concurrency Control)

PostgreSQL uses MVCC to allow readers and writers not to block each other. Every row has `xmin` (transaction ID that created it) and `xmax` (transaction ID that deleted/updated it). A reader sees the version of the row that was committed before the reader's transaction started.

**Consequence: VACUUM is mandatory.** Dead tuples (rows invisible to all transactions) accumulate. Without VACUUM, tables bloat and `pg_clog` (transaction status log) fills. `autovacuum` handles this automatically but must be configured correctly.

```sql
-- Monitor vacuum health
SELECT schemaname, tablename, 
       n_dead_tup, n_live_tup, 
       last_autovacuum, last_analyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- Force vacuum on a bloated table
VACUUM ANALYZE my_table;

-- Reclaim space (requires exclusive lock — use with care)
VACUUM FULL my_table;
```

### EXPLAIN ANALYZE Output Reading
```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT u.id, u.email, o.total
FROM users u
JOIN orders o ON o.user_id = u.id
WHERE u.created_at > '2024-01-01'
  AND o.status = 'completed';
```

**Reading the output:**
```
Hash Join  (cost=123.45..456.78 rows=1000 width=60) 
           (actual time=5.123..45.678 rows=892 loops=1)
  Buffers: shared hit=245 read=12
  ->  Seq Scan on orders o  (cost=0..234.56 rows=5000 width=20)
            (actual time=0.012..12.345 rows=4987 loops=1)
        Filter: (status = 'completed')
        Rows Removed by Filter: 13013
  ->  Hash  (cost=89.00..89.00 rows=3000 width=40)
            (actual time=4.567..4.567 rows=2987 loops=1)
        ->  Index Scan using users_created_at_idx on users u
                  (actual time=0.034..3.456 rows=2987 loops=1)
            Index Cond: (created_at > '2024-01-01')

Key fields:
  cost=X..Y: estimated startup cost .. total cost (in arbitrary units)
  actual time=X..Y: measured startup ms .. total ms
  rows: actual rows (vs estimated rows — large difference = stale statistics)
  Buffers shared hit: pages from buffer cache (fast)
  Buffers shared read: pages from disk (slow — if high, add index or more memory)
  loops: how many times this node was executed
```

**Red flags:**
- `Seq Scan` on large table with filter: likely missing index
- Large difference between estimated and actual rows: run `ANALYZE`
- High `Rows Removed by Filter`: index exists but not selective enough
- `loops` > 1 on expensive node: nested loop join on large dataset (consider hash join)

### PostgreSQL Index Types

```sql
-- B-tree (default): equality and range queries on comparable types
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_users_email ON users(email);

-- Hash: equality only, faster than B-tree for pure equality
-- (B-tree is generally preferred — Hash not WAL-logged in old versions)
CREATE INDEX idx_sessions_token ON sessions USING HASH (token);

-- GiST: geometric types, full-text search (tsvector), range types, geographic
CREATE INDEX idx_locations_geom ON locations USING GIST (location_point);

-- GIN: full-text search (tsvector), JSONB keys, array containment
CREATE INDEX idx_articles_search ON articles USING GIN (to_tsvector('english', content));
CREATE INDEX idx_products_tags ON products USING GIN (tags);  -- for array @> queries
CREATE INDEX idx_events_data ON events USING GIN (data jsonb_path_ops);  -- for JSONB

-- BRIN (Block Range Index): very large tables with natural physical ordering
-- (e.g., time-series data inserted in order)
-- Tiny index (stores min/max per block range), appropriate when sequential scan is acceptable
CREATE INDEX idx_logs_timestamp_brin ON logs USING BRIN (created_at);

-- Partial index: index only rows matching a condition
CREATE INDEX idx_orders_pending ON orders(created_at) WHERE status = 'pending';

-- Covering index (PostgreSQL 11+): include non-key columns to satisfy queries from index alone
CREATE INDEX idx_users_email_covering ON users(email) INCLUDE (id, name);
```

### Window Functions and CTEs
```sql
-- Window function: ranking, running totals, moving averages
SELECT 
  user_id,
  order_total,
  SUM(order_total) OVER (PARTITION BY user_id ORDER BY created_at) as running_total,
  RANK() OVER (PARTITION BY region ORDER BY order_total DESC) as rank_in_region,
  LAG(order_total) OVER (PARTITION BY user_id ORDER BY created_at) as prev_order
FROM orders;

-- CTE: readable complex queries (not always faster — optimizer may or may not inline)
WITH monthly_revenue AS (
  SELECT 
    DATE_TRUNC('month', created_at) as month,
    SUM(total) as revenue
  FROM orders
  WHERE status = 'completed'
  GROUP BY 1
),
growth AS (
  SELECT 
    month,
    revenue,
    LAG(revenue) OVER (ORDER BY month) as prev_revenue,
    (revenue - LAG(revenue) OVER (ORDER BY month)) / LAG(revenue) OVER (ORDER BY month) * 100 as growth_pct
  FROM monthly_revenue
)
SELECT * FROM growth ORDER BY month;
```

### Connection Pooling with PgBouncer

```ini
# pgbouncer.ini — verified configuration keys
[databases]
mydb = host=127.0.0.1 port=5432 dbname=mydb

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

# Pool modes:
# session: connection held for entire client session (compatible with all features)
# transaction: connection returned after each transaction (most efficient, incompatible with 
#              session-level features: LISTEN/NOTIFY, prepared statements, advisory locks)
# statement: connection returned after each statement (rarely used)
pool_mode = transaction

max_client_conn = 1000      # max clients connecting to PgBouncer
default_pool_size = 20      # connections per database/user pair to PostgreSQL

server_idle_timeout = 600   # return idle connections to PostgreSQL after N seconds
client_idle_timeout = 0     # keep client connections indefinitely (0 = disabled)
```

**Why connection pooling:** PostgreSQL creates a new OS process per connection. 10,000 connections = 10,000 processes. Memory consumption is ~5-10MB per connection even when idle. Connection setup adds latency. PgBouncer multiplexes many client connections onto few server connections.

---

## 5. Query Optimization: N+1 Problem

```python
# N+1 problem: 1 query to get users + N queries to get each user's orders
users = User.objects.all()  # SELECT * FROM users — 1 query
for user in users:
    orders = user.orders.all()  # SELECT * FROM orders WHERE user_id = ? — N queries
    print(f"{user.name}: {len(orders)} orders")

# Solution: JOIN-based prefetch
# Django ORM:
users = User.objects.prefetch_related('orders').all()
# Generates: SELECT * FROM users; SELECT * FROM orders WHERE user_id IN (...)

# SQLAlchemy:
users = session.query(User).options(joinedload(User.orders)).all()
# Generates: SELECT users.*, orders.* FROM users LEFT JOIN orders ON ...
```

**Detection:** Enable slow query logging (`log_min_duration_statement = 100` in PostgreSQL), then look for repeated identical queries with different parameter values in rapid succession.

---

## 6. PostgreSQL Replication

**Streaming Replication (physical):**
- Ships WAL bytes from primary to standbys
- Standbys are read-only replicas, exact byte-for-byte copies
- `synchronous_commit = on` — primary waits for standby acknowledgment (no data loss)
- `synchronous_commit = off` — asynchronous replication (faster, up to 1 WAL segment loss)
- Monitor lag: `SELECT now() - pg_last_xact_replay_timestamp() AS replication_delay;`

**Logical Replication:**
- Ships row-level changes (INSERT/UPDATE/DELETE) as logical messages
- Standby can be a different PostgreSQL version, can have different schema
- Selective: can replicate individual tables
- Enables migration with near-zero downtime (replicate, cut over, stop old primary)

---

## 7. MongoDB

### Document Model and Schema Patterns

**Embedding vs Referencing:**
```javascript
// Embedding (denormalized): good for 1-to-few, frequently read together
{
  _id: ObjectId("..."),
  title: "My Blog Post",
  author: { name: "Alice", email: "alice@example.com" },  // embedded
  tags: ["mongodb", "nosql"],                              // embedded array
  comments: [                                              // embedded (if few)
    { author: "Bob", text: "Great post!", date: ISODate("...") }
  ]
}

// Referencing (normalized): good for 1-to-many, data reused across documents
{
  _id: ObjectId("..."),
  title: "My Blog Post",
  author_id: ObjectId("..."),    // reference to users collection
  comment_ids: [ObjectId("..."), ObjectId("...")]  // references
}
```

### Aggregation Pipeline
```javascript
// Verified MongoDB aggregation pipeline syntax
db.orders.aggregate([
  // $match first — reduces documents before expensive stages
  { $match: { status: "completed", created_at: { $gte: new Date("2024-01-01") } } },
  
  // $lookup: left join with another collection
  { $lookup: {
    from: "users",
    localField: "user_id",
    foreignField: "_id",
    as: "user"
  }},
  
  { $unwind: "$user" },  // flatten the array from $lookup
  
  // $group: aggregate
  { $group: {
    _id: "$user.region",
    total_revenue: { $sum: "$total" },
    order_count: { $sum: 1 },
    avg_order: { $avg: "$total" }
  }},
  
  { $sort: { total_revenue: -1 } },
  { $limit: 10 }
])
```

**Shard key selection (critical for performance):**
- Good: high cardinality (many distinct values), even distribution, aligned with query patterns
- Bad: monotonically increasing (ObjectId, timestamps) — all writes go to one shard
- Bad: low cardinality (boolean, status with few values) — data skew
- Consider hashed shard key for write distribution: `sh.shardCollection("db.col", { _id: "hashed" })`

---

## 8. Redis Deep Dive

### Data Structures and Use Cases

```
String:      GET/SET/INCR/DECR — cache, counters, rate limiting, feature flags
Hash:        HGET/HSET/HMGET — user sessions, object storage (avoid if >512 fields)
List:        LPUSH/RPUSH/LRANGE/BLPOP — queues, recent items, activity feeds
Set:         SADD/SMEMBERS/SINTER/SUNION — unique visitors, tags, friend lists
Sorted Set:  ZADD/ZRANGE/ZRANGEBYSCORE — leaderboards, rate limiting, time-ordered events
Stream:      XADD/XREAD/XGROUP — durable message queues, event sourcing
HyperLogLog: PFADD/PFCOUNT — approximate unique count, ~0.81% error, O(1) memory
Bloom Filter: BF.ADD/BF.EXISTS (RedisBloom module) — membership test, no false negatives
```

### Persistence Options

```
RDB (Redis Database Backup):
  - Point-in-time snapshots at configurable intervals
  - Configured: save 900 1, save 300 10, save 60 10000
    (save if at least 1 change in 900s, 10 changes in 300s, 10000 changes in 60s)
  - Fast restart, compact files
  - Potential data loss: up to the interval since last snapshot
  - Use for: cache, non-critical data

AOF (Append-Only File):
  - Log every write operation, replay on restart
  - appendfsync: always (safest, slowest), everysec (1s loss, recommended), no (OS decides)
  - AOF rewrite compacts log periodically
  - Use for: data that must survive restarts with minimal loss

Hybrid (RDB + AOF, Redis 4.0+):
  - AOF uses RDB snapshot as base, then appends changes
  - Faster restart than pure AOF, better durability than pure RDB
  - Recommended for production Redis with durability requirements
```

### Redis Cluster (Hash Slots)
```
Redis Cluster uses 16,384 hash slots.
Each key is assigned to a slot: CRC16(key) % 16384
Slots are distributed across master nodes (and their replicas).

Example with 3 masters:
  Node 1: slots 0-5460
  Node 2: slots 5461-10922
  Node 3: slots 10923-16383

Hash tags: {user}.sessions and {user}.profile go to the same slot
           because the key is hashed on the substring in {}
           This enables multi-key operations across logically related keys.

CLUSTER INFO, CLUSTER NODES commands for cluster status.
```

### Lua Scripting for Atomicity
```lua
-- Redis Lua scripts run atomically — no other command executes during the script
-- Use for: check-and-set, conditional updates, rate limiting

-- Rate limiter script (token bucket)
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])

local current = redis.call('INCR', key)
if current == 1 then
  redis.call('EXPIRE', key, window)
end
if current > limit then
  return 0  -- rate limited
else
  return 1  -- allowed
end

-- Invoke: EVAL script 1 rate_limit:user:123 100 60
```

### Eviction Policies
```
noeviction: return error when memory full (safe for critical data)
allkeys-lru: evict least recently used key from all keys
volatile-lru: evict LRU from keys with TTL set
allkeys-lfu: evict least frequently used (Redis 4.0+)
volatile-lfu: evict LFU from keys with TTL set
allkeys-random: evict random key
volatile-random: evict random key with TTL
volatile-ttl: evict key with nearest expiration

For cache: allkeys-lru or allkeys-lfu
For session store: volatile-lru (protect keys without TTL)
```

---

## 9. Apache Kafka

### Architecture Fundamentals

```
Topics → Partitions → Offsets (immutable, ordered log per partition)

Partition count = maximum parallelism ceiling for consumers in a consumer group.
  10 partitions → max 10 consumers in a group (11th consumer is idle)
  Scale consumers? Scale partitions first (cannot reduce partitions without recreation)

Replication factor: how many broker copies exist per partition
  replication.factor=3: each partition on 3 different brokers
  min.insync.replicas=2: producer requires 2 replicas to acknowledge before ack
```

### Consumer Groups and Offset Management
```python
# Kafka consumer — Python (confluent-kafka), verified config keys
from confluent_kafka import Consumer

consumer = Consumer({
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'my-consumer-group',
    'auto.offset.reset': 'earliest',      # start from beginning if no committed offset
    'enable.auto.commit': False,           # manual commit for control
    'max.poll.interval.ms': 300000,        # 5 minutes — must process within this time
    'session.timeout.ms': 10000,           # heartbeat timeout
})

consumer.subscribe(['my-topic'])

while True:
    msg = consumer.poll(timeout=1.0)
    if msg is None:
        continue
    if msg.error():
        handle_error(msg.error())
        continue
    
    process(msg.value())
    consumer.commit(asynchronous=False)  # commit after successful processing
```

### Exactly-Once Semantics

```
At-most-once: produce fire-and-forget (acks=0) — messages may be lost
At-least-once: produce with acks=all, retry on failure — duplicates possible
Exactly-once: idempotent producer + transactional API

Idempotent producer (enable.idempotence=true):
  Each producer gets a PID, each message gets a sequence number.
  Broker deduplicates retries. Prevents duplicates from network retransmission.
  Guarantee: within a single producer session, each message is written once.

Transactional API (exactly-once across partitions):
  transactional.id = 'my-producer-id'
  Enables atomic writes to multiple partitions: all succeed or all fail.
  Consumer isolation.level=read_committed: reads only committed transactions.

Exactly-once stream processing (Kafka Streams):
  processing.guarantee = exactly_once_v2  (Kafka 2.5+ — preferred)
  or exactly_once  (older)
  Internally: transactional producer + consumer offset in same transaction
```

### Producer/Consumer Config Tuning
```
Producer:
  acks=all: wait for all ISR replicas (safest, higher latency)
  acks=1: wait for leader only (faster, data loss if leader fails before replication)
  linger.ms=5: wait 5ms to batch more messages (throughput vs latency)
  batch.size=16384: 16KB batches (increase to 65536+ for throughput)
  compression.type=lz4: compress batches (CPU for network savings, worth it)

Consumer:
  fetch.min.bytes=1: fetch as soon as 1 byte available (low latency)
  fetch.min.bytes=50000: wait for 50KB (higher throughput, higher latency)
  fetch.max.wait.ms=500: max wait for fetch.min.bytes condition
  max.poll.records=500: max records per poll()
```

---

## 10. Elasticsearch/OpenSearch: Inverted Index and Search

**Inverted index:** Maps from terms to document IDs. "quick brown fox" → `quick: [doc1, doc3]`, `brown: [doc1, doc2]`. Text search is a lookup in this inverted index — O(1) term lookup, not O(n) scan.

**Analyzers:**
```json
// Standard analyzer: lowercase, tokenize on whitespace/punctuation, basic stemming
// Whitespace analyzer: tokenize on whitespace only, no lowercasing
// Keyword analyzer: no tokenization (treat as single token) — for exact matches, IDs, enums

// Custom analyzer example
PUT /my-index
{
  "settings": {
    "analysis": {
      "analyzer": {
        "my_english": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "stop", "snowball"]
        }
      }
    }
  }
}
```

**Query types:**
```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "title": "elasticsearch guide" } }
      ],
      "filter": [
        { "term": { "status": "published" } },
        { "range": { "date": { "gte": "2024-01-01" } } }
      ],
      "should": [
        { "match": { "tags": "search" } }
      ],
      "must_not": [
        { "term": { "hidden": true } }
      ]
    }
  }
}
```

**`filter` vs `must`:** `filter` does not affect relevance score and is cached. Use `filter` for exact matches (term, range). Use `must` when relevance scoring matters (match, multi_match).

---

## 11. Cassandra and DynamoDB: Partition Key Design

**The hot partition problem:** If your partition key is not evenly distributed (e.g., a popular celebrity's user_id, or today's date), all traffic concentrates on one shard while others are idle.

```
Bad partition key: date (only today's partition gets all writes)
Bad partition key: status (only 3-5 values, massive hot partitions)
Good partition key: user_id (if users are distributed)
Good partition key: hash(user_id) % 100 (if natural distribution is skewed)
```

**Cassandra consistency levels (verified):**
```
Write path:
  ANY: any node accepts (lowest durability)
  ONE: at least 1 replica acknowledges
  LOCAL_ONE: at least 1 replica in local DC acknowledges
  QUORUM: majority of replicas across all DCs (RF/2 + 1)
  LOCAL_QUORUM: majority in local DC (use for multi-DC)
  ALL: all replicas (highest durability, lowest availability)

Read path: same levels — ONE is fastest, ALL is strongest consistency
Tunable consistency: write QUORUM + read QUORUM = strong consistency for RF=3
```

---

## 12. Connection Pooling Strategy

**HikariCP (Java) — verified configuration:**
```java
HikariConfig config = new HikariConfig();
config.setJdbcUrl("jdbc:postgresql://host:5432/db");
config.setUsername("user");
config.setPassword("password");
config.setMaximumPoolSize(10);           // max connections to PostgreSQL
config.setMinimumIdle(5);               // min connections kept alive
config.setConnectionTimeout(30000);      // 30s — throw exception if no connection available
config.setIdleTimeout(600000);           // 10m — close idle connections
config.setMaxLifetime(1800000);          // 30m — max connection lifetime (rotate before DB timeout)
config.setConnectionTestQuery("SELECT 1"); // health check query
HikariDataSource ds = new HikariDataSource(config);
```

**SQLAlchemy Pool (Python) — verified parameters:**
```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql+psycopg2://user:password@host:5432/db",
    pool_size=10,           # persistent connections
    max_overflow=20,        # extra connections above pool_size under load
    pool_timeout=30,        # seconds to wait for connection before exception
    pool_recycle=1800,      # recycle connections every 30 minutes
    pool_pre_ping=True,     # verify connection health before use
)
```

---

## 13. Schema Migration

**Migration tools (verified):**
- **Flyway**: SQL-file-based, versioned migrations (`V1__init.sql`, `V2__add_index.sql`), Java/Kotlin native
- **Liquibase**: XML/YAML/JSON/SQL changelogs, supports rollback, database-agnostic
- **Alembic**: Python, SQLAlchemy-integrated, auto-generates migration scripts via `alembic revision --autogenerate`

**Backward compatibility rules for zero-downtime deployments:**
```
Safe operations (can deploy anytime):
  - Adding a nullable column
  - Adding a new table
  - Adding a new index (use CONCURRENTLY in PostgreSQL)

Unsafe operations (require multi-step deployment):
  - Renaming a column (old code still references old name)
  - Dropping a column (deploy code that doesn't use it first)
  - Adding a NOT NULL column without a default (fails for existing rows)
  - Changing column type (may require full table rewrite)

Pattern for renaming a column:
  Step 1: Add new column, write to both old and new in code
  Step 2: Backfill old data into new column
  Step 3: Make reads from new column only
  Step 4: Stop writing to old column
  Step 5: Drop old column
```

---

## Cross-Domain Connections

**Database ↔ Observability:** Export PostgreSQL metrics via `postgres_exporter` to Prometheus. Metrics: `pg_stat_activity_count`, `pg_stat_user_tables_n_dead_tup`, `pg_replication_slots_lag_bytes`. Slow queries via `log_min_duration_statement`. Trace database spans with `db.system=postgresql`, `db.statement` (truncated — don't log full query with params).

**Database ↔ SRE:** Database failures are some of the most severe production incidents. Connection pool exhaustion is a P1 incident. Replication lag crossing a threshold is a reliability failure. SLIs must cover database availability and query latency, not just API response codes.

**Database ↔ Data Engineering:** Data engineering pipelines read from operational databases via CDC (Change Data Capture with Debezium reading PostgreSQL WAL, MongoDB oplog), batch exports, or direct query. Schema changes in operational databases break downstream pipelines — data contracts prevent this.

**Database ↔ Security:** SQL injection prevention at the ORM/query level. Principle of least privilege: application user has SELECT/INSERT/UPDATE, not DROP/TRUNCATE. Encryption at rest and in transit. Audit logs for sensitive table access.

---

## Self-Review Checklist

```
Fundamentals
□ 1. ACID properties understood and verified for the databases in use
□ 2. Isolation level explicitly configured (not relying on defaults)
□ 3. CAP/PACELC tradeoffs documented for each database choice
□ 4. BASE consistency appropriate for the use case (not default-to-BASE)

PostgreSQL
□ 5. EXPLAIN ANALYZE reviewed for all slow queries (not just EXPLAIN)
□ 6. Index types chosen appropriately (GIN for JSONB/arrays, GiST for geo, BRIN for time-series)
□ 7. Covering indexes used for high-frequency read queries
□ 8. Autovacuum configured and dead tuple counts monitored
□ 9. Replication lag monitored and alerting configured

Query Design
□ 10. N+1 queries eliminated in all ORM usage
□ 11. All JOIN queries have indexes on foreign key columns
□ 12. Large result sets paginated with keyset/cursor (not OFFSET)

Schema Migration
□ 13. All migrations tested for backward compatibility (old code + new schema)
□ 14. Indexes created with CONCURRENTLY flag in PostgreSQL
□ 15. Column drops are three-step process (code → backfill → drop)

Redis
□ 16. Eviction policy chosen explicitly based on use case
□ 17. Persistence mode configured (RDB for cache, AOF/hybrid for durability)
□ 18. Memory limit set with maxmemory in redis.conf

Kafka
□ 19. Partition count decided based on target consumer parallelism
□ 20. Exactly-once semantics configured if duplicate processing is unacceptable
```
