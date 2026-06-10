---
name: god-redis-mastery
description: "God-level Redis deep dive. Comprehensive coverage of Redis data structures (Strings, Hashes, Lists, Sets, Sorted Sets, Streams, HyperLogLog, Bitmaps, Geospatial), Lua scripting for atomicity, Redis Cluster (hash slots, resharding, failover), Redis Sentinel (HA without clustering), pub/sub and Streams for messaging, Redis modules (RedisJSON, RediSearch, RedisBloom, RedisTimeSeries), persistence tuning (RDB, AOF, hybrid), memory analysis and optimization (object encoding, memory fragmentation), connection pooling, pipelining, key expiration strategies, eviction policies, ACL security, TLS configuration, and production operational patterns. Never fabricate Redis commands — verify against redis.io/commands. Covers Redis 7.x."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Redis Mastery

## Anti-Hallucination Rules

- NEVER invent Redis commands — every command must be verifiable at redis.io/commands.
- NEVER confuse Redis Cluster with Redis Sentinel — they serve different purposes.
- NEVER claim a feature exists without checking the Redis version (e.g., ACL is Redis 6+, Functions is Redis 7+).
- NEVER fabricate Redis module commands — RedisJSON uses `JSON.SET`, not `JSONSET`. Verify exact syntax.
- ALWAYS specify whether a command is blocking or non-blocking, and its time complexity.

---

## 1. Data Structures Deep Dive

### 1.1 Strings

```redis
# Strings are binary-safe — up to 512MB
SET user:1:name "Alice"
GET user:1:name

# Atomic increment/decrement (counters)
INCR page:views:home         # Atomic +1
INCRBY page:views:home 10    # Atomic +10
INCRBYFLOAT account:balance 99.95

# Conditional set
SET session:abc123 "user_data" EX 3600 NX
# EX = expiry in seconds, PX = expiry in milliseconds
# NX = set only if NOT exists (distributed lock pattern)
# XX = set only if EXISTS (update only)
# GET = return old value (Redis 6.2+)

# GETDEL, GETEX (Redis 6.2+)
GETDEL temp:token:abc          # Get and delete atomically
GETEX session:abc EX 7200      # Get and update expiry

# Bit operations
SETBIT user:1:features 0 1    # Feature flag at bit 0
GETBIT user:1:features 0
BITCOUNT user:1:features      # Count set bits
BITOP AND result key1 key2    # Bitwise AND across keys
```

### 1.2 Hashes

```redis
# Hashes — ideal for objects (memory-efficient for small hashes via ziplist encoding)
HSET user:1 name "Alice" email "alice@example.com" age 30 role "admin"
HGET user:1 name
HMGET user:1 name email age
HGETALL user:1

HINCRBY user:1 age 1           # Atomic field increment
HEXISTS user:1 role
HDEL user:1 role
HLEN user:1

# Hash scan (safe iteration)
HSCAN user:1 0 MATCH "na*" COUNT 10

# Memory optimization:
# Hashes with < hash-max-ziplist-entries (default 128) fields
# and values < hash-max-ziplist-value (default 64 bytes)
# are stored as ziplist (compact, O(N) but tiny N = fast)
```

### 1.3 Lists

```redis
LPUSH queue:tasks "task1" "task2"   # Push to left (head)
RPUSH queue:tasks "task3"           # Push to right (tail)
LRANGE queue:tasks 0 -1             # Get all elements
LLEN queue:tasks

# Blocking pop (worker queue pattern)
BRPOP queue:tasks 30                # Block for 30s waiting for element
BLPOP queue:high queue:low 0        # Block on multiple queues, priority order

# Trim (bounded list — e.g., recent activity feed)
LPUSH feed:user:1 "new_activity"
LTRIM feed:user:1 0 99              # Keep only latest 100 items

# LPOS (Redis 6.0.6+) — find element position
LPOS queue:tasks "task2"            # Returns index of element
LPOS queue:tasks "task2" RANK 2     # Find second occurrence
```

### 1.4 Sets

```redis
SADD tags:article:1 "redis" "database" "nosql"
SMEMBERS tags:article:1
SISMEMBER tags:article:1 "redis"    # O(1) membership test
SCARD tags:article:1                # Cardinality (count)

# Set operations
SINTER tags:article:1 tags:article:2     # Intersection
SUNION tags:article:1 tags:article:2     # Union
SDIFF tags:article:1 tags:article:2      # Difference

# Random member
SRANDMEMBER tags:article:1 3             # Get 3 random members
SPOP tags:article:1                      # Remove and return random member
```

### 1.5 Sorted Sets

```redis
# Sorted sets — elements sorted by score, O(log N) operations
ZADD leaderboard 1500 "alice" 1200 "bob" 1800 "charlie"
ZRANGE leaderboard 0 -1 WITHSCORES      # Ascending
ZREVRANGE leaderboard 0 2 WITHSCORES    # Top 3, descending
ZRANK leaderboard "alice"                # Rank (0-indexed, ascending)
ZREVRANK leaderboard "alice"             # Rank (descending)

ZINCRBY leaderboard 50 "alice"           # Atomic score increment

# Range by score
ZRANGEBYSCORE leaderboard 1000 2000 WITHSCORES
ZRANGEBYSCORE leaderboard -inf +inf LIMIT 0 10

# Lexicographic range (when all scores are equal)
ZRANGEBYLEX leaderboard "[a" "[d"

# Remove by rank (trim leaderboard to top 100)
ZREMRANGEBYRANK leaderboard 0 -101

# Intersection/Union with aggregation
ZUNIONSTORE combined 2 leaderboard:week1 leaderboard:week2 WEIGHTS 1 2 AGGREGATE SUM
```

### 1.6 Streams

```redis
# Streams — append-only log (like Kafka, but built into Redis)
XADD events:orders * user_id 42 product_id 100 amount 29.99
# * = auto-generate ID (timestamp-sequence)

# Consumer groups
XGROUP CREATE events:orders order-processors $ MKSTREAM
# $ = only new messages, 0 = all messages from beginning

# Read as consumer in group
XREADGROUP GROUP order-processors consumer-1 COUNT 10 BLOCK 5000 STREAMS events:orders >
# > = undelivered messages only

# Acknowledge processed message
XACK events:orders order-processors 1234567890-0

# Check pending (unacknowledged) messages
XPENDING events:orders order-processors - + 10

# Claim stale messages (consumer died)
XAUTOCLAIM events:orders order-processors consumer-2 60000 0-0 COUNT 10
# Claim messages idle for > 60s

# Stream info
XINFO STREAM events:orders
XINFO GROUPS events:orders
XLEN events:orders

# Trim stream (cap size)
XTRIM events:orders MAXLEN ~ 10000    # ~ = approximate trim (more efficient)
```

---

## 2. Lua Scripting

```redis
# Lua scripts execute atomically — no other command runs during execution
# KEYS[] = key arguments, ARGV[] = value arguments

-- Rate limiter (sliding window)
EVAL "
local key = KEYS[1]
local window = tonumber(ARGV[1])
local max_requests = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

-- Remove old entries outside the window
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

-- Count current entries
local count = redis.call('ZCARD', key)

if count < max_requests then
    -- Add current request
    redis.call('ZADD', key, now, now .. ':' .. math.random())
    redis.call('EXPIRE', key, window)
    return 1  -- allowed
else
    return 0  -- rate limited
end
" 1 rate_limit:user:42 60 100 1705334553

# Redis Functions (Redis 7+) — replaces EVAL for production use
FUNCTION LOAD "#!lua name=mylib\n redis.register_function('my_rate_limit', function(keys, args) ... end)"
FCALL my_rate_limit 1 rate_limit:user:42 60 100
```

---

## 3. Redis Cluster

```
Hash Slots: 16,384 slots distributed across master nodes
  CRC16(key) % 16384 = slot number

3-master minimum cluster:
  Master A: slots 0-5460      → Replica A'
  Master B: slots 5461-10922  → Replica B'
  Master C: slots 10923-16383 → Replica C'

Hash Tags: Force keys to same slot
  {user:42}.profile   ← same slot
  {user:42}.sessions  ← same slot (hash on "user:42")
  Required for: MGET, transactions, Lua scripts across multiple keys
```

```bash
# Create cluster
redis-cli --cluster create \
  node1:6379 node2:6379 node3:6379 \
  node4:6379 node5:6379 node6:6379 \
  --cluster-replicas 1

# Cluster operations
redis-cli --cluster info node1:6379
redis-cli --cluster check node1:6379
redis-cli --cluster reshard node1:6379

# Move slots
redis-cli --cluster reshard node1:6379 \
  --cluster-from <source-node-id> \
  --cluster-to <target-node-id> \
  --cluster-slots 1000 \
  --cluster-yes
```

---

## 4. Redis Sentinel

```
Sentinel provides HA without sharding:
  - Monitors master and replica health
  - Automatic failover when master is down
  - Notifies clients of new master

Minimum: 3 Sentinel instances (quorum-based decisions)
```

```ini
# sentinel.conf
sentinel monitor mymaster 10.0.0.1 6379 2     # 2 = quorum
sentinel down-after-milliseconds mymaster 5000  # 5s to mark as down
sentinel failover-timeout mymaster 60000        # 60s failover timeout
sentinel parallel-syncs mymaster 1              # 1 replica syncs at a time
sentinel auth-pass mymaster <password>
```

```python
# Python client with Sentinel support
from redis.sentinel import Sentinel

sentinel = Sentinel(
    [('sentinel1', 26379), ('sentinel2', 26379), ('sentinel3', 26379)],
    socket_timeout=0.5
)
master = sentinel.master_for('mymaster', socket_timeout=0.5)
slave = sentinel.slave_for('mymaster', socket_timeout=0.5)

master.set('key', 'value')       # Write to master
value = slave.get('key')         # Read from replica
```

---

## 5. Redis Modules

```redis
# RedisJSON — native JSON support
JSON.SET user:1 $ '{"name":"Alice","age":30,"address":{"city":"NYC"}}'
JSON.GET user:1 $.name                    # "Alice"
JSON.NUMINCRBY user:1 $.age 1           # Atomic increment
JSON.ARRAPPEND user:1 $.tags '"redis"'   # Append to array

# RediSearch — full-text search + secondary indexing
FT.CREATE idx:users ON JSON PREFIX 1 user: SCHEMA
  $.name AS name TEXT SORTABLE
  $.email AS email TAG
  $.age AS age NUMERIC SORTABLE
  $.city AS city TEXT

FT.SEARCH idx:users "@name:Alice @age:[25 35]"
FT.SEARCH idx:users "@city:NYC" SORTBY age ASC LIMIT 0 10

# RedisBloom — probabilistic data structures
BF.ADD bloom:emails "alice@example.com"
BF.EXISTS bloom:emails "alice@example.com"    # 1 (yes)
BF.EXISTS bloom:emails "bob@example.com"      # 0 (definitely no)
# No false negatives, small false positive rate (~1% default)

# RedisTimeSeries — time series data
TS.CREATE sensor:temp:1 RETENTION 86400000 LABELS location "datacenter-1"
TS.ADD sensor:temp:1 * 72.5                   # Auto-timestamp
TS.RANGE sensor:temp:1 - + AGGREGATION avg 3600000  # Hourly average
```

---

## 6. Memory Analysis and Optimization

```redis
# Memory usage per key
MEMORY USAGE user:1              # Bytes used by this key
OBJECT ENCODING user:1           # Internal encoding (ziplist, hashtable, etc.)
OBJECT IDLETIME user:1           # Seconds since last access

# Memory report
INFO memory
# used_memory: total allocated
# used_memory_rss: OS-reported memory (includes fragmentation)
# mem_fragmentation_ratio: rss/used_memory (>1.5 = high fragmentation)
# used_memory_peak: highest memory usage

# MEMORY DOCTOR (Redis 4+)
MEMORY DOCTOR                    # Diagnostic suggestions

# Key analysis
redis-cli --bigkeys              # Find largest keys per type
redis-cli --memkeys              # Find keys using most memory
```

**Encoding optimization:**
```
Type        Small encoding    Large encoding    Threshold
─────────────────────────────────────────────────────────
Hash        ziplist           hashtable         hash-max-ziplist-entries=128
List        listpack          quicklist         list-max-ziplist-size=-2
Set         listpack          hashtable         set-max-intset-entries=512
Sorted Set  listpack          skiplist          zset-max-ziplist-entries=128
```

---

## 7. Production Configuration

```conf
# redis.conf — production essentials
maxmemory 4gb
maxmemory-policy allkeys-lfu        # LFU for cache workloads

# Persistence (hybrid recommended)
save ""                              # Disable RDB snapshots (or keep as backup)
appendonly yes
appendfsync everysec
aof-use-rdb-preamble yes            # Hybrid: RDB + AOF (Redis 4.0+)

# Security
requirepass <strong-password>
rename-command FLUSHALL ""           # Disable dangerous commands
rename-command FLUSHDB ""
rename-command DEBUG ""
rename-command CONFIG ""              # Disable CONFIG in production

# ACL (Redis 6+)
user default off                     # Disable default user
user app-user on >app-password ~app:* +@read +@write -@admin
user admin-user on >admin-password ~* +@all

# TLS (Redis 6+)
tls-port 6380
port 0                               # Disable non-TLS port
tls-cert-file /etc/redis/tls/redis.crt
tls-key-file /etc/redis/tls/redis.key
tls-ca-cert-file /etc/redis/tls/ca.crt

# Performance
tcp-backlog 511
timeout 300                          # Close idle connections after 5min
tcp-keepalive 60
hz 10                                # Server tick frequency (10-100)
```

---

## Cross-Domain Connections

**Redis ↔ Application Cache:** Cache-aside pattern (check cache → miss → query DB → populate cache). Set TTL to prevent stale data. Use `SET NX` for cache stampede prevention (only one request populates cache).

**Redis ↔ Session Store:** Use Hashes for session data with `EXPIRE`. Redis Sentinel/Cluster provides HA so sessions survive node failure.

**Redis ↔ Rate Limiting:** Sorted Sets or Lua scripts implement sliding window rate limiting. Redis atomic operations prevent race conditions.

**Redis ↔ Kubernetes:** Deploy Redis Cluster or Sentinel via Helm chart (bitnami/redis, bitnami/redis-cluster). Use PersistentVolumeClaims for data persistence. Monitor with redis_exporter → Prometheus.

---

## Self-Review Checklist

- [ ] `maxmemory` and `maxmemory-policy` configured (never run without limits)
- [ ] Persistence mode chosen and configured (RDB for cache, hybrid for durability)
- [ ] Dangerous commands disabled or renamed (FLUSHALL, FLUSHDB, DEBUG)
- [ ] ACLs configured (Redis 6+) — no default user access
- [ ] TLS enabled for production (Redis 6+)
- [ ] Connection pooling used in application clients
- [ ] Pipelining used for bulk operations (not individual commands)
- [ ] Hash tags used for multi-key operations in Cluster mode
- [ ] Key naming convention established (e.g., `entity:id:field`)
- [ ] TTL set on all cache keys (no indefinite cache entries)
- [ ] Memory fragmentation ratio monitored (< 1.5)
- [ ] `--bigkeys` scan run periodically to detect hot/large keys
- [ ] Lua scripts kept short (< 5ms) to avoid blocking other operations
- [ ] Sentinel or Cluster deployed for HA (never single-instance in production)
