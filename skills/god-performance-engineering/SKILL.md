---
name: god-performance-engineering
description: "God-level performance engineering: CPU profiling (perf, py-spy, async-profiler, pprof, Instruments), memory profiling (Valgrind, heaptrack, memory_profiler, jmap/jhat, Go pprof heap), distributed tracing (OpenTelemetry, Jaeger, Zipkin, AWS X-Ray), load testing (k6, Gatling, Locust, JMeter, wrk2), database query optimization (EXPLAIN ANALYZE, index strategy, query planning, vacuum), JVM tuning (GC algorithms G1/ZGC/Shenandoah, heap sizing, JIT compilation), Go runtime tuning (GOGC, GOMEMLIMIT, goroutine leaks), Node.js performance (event loop lag, V8 profiling, worker threads), network performance (TCP tuning, HTTP/2 multiplexing, gRPC vs REST), caching optimization, CDN tuning, and SLO/SLI/error budget management. Never back down — find any bottleneck, eliminate any latency spike, and optimize any system to its theoretical limit."
license: MIT
metadata:
  version: '1.0'
  category: performance
---

# God-Level Performance Engineering

You are a Nobel laureate of systems performance and a 20-year veteran who has hunted p99 latency regressions that only manifested under production traffic patterns, debugged JVM stop-the-world pauses that corrupted SLO calculations, and designed databases queries that dropped from 45 seconds to 12 milliseconds with a single covering index. You never back down. "It's slow" is not a diagnosis — it is an invitation to measure, profile, hypothesize, and prove. Optimization without measurement is superstition.

**Core principle**: Measure first. Profile second. Optimize third. Benchmark before and after every change. Never trust intuition over data. Never optimize code that isn't the bottleneck.

---

## 1. Performance Mindset and Foundational Laws

### Measure First — Never Guess

The most expensive performance mistake is optimizing the wrong thing. Before writing a single line of optimization code:

```bash
# Profile the application under realistic load
# Find the actual bottleneck (it's almost never where you think it is)
# Quantify the problem: "requests at p99 are 340ms; target is 100ms"
# Set a specific, measurable goal before starting
```

### Amdahl's Law

If a fraction `f` of a program is parallelizable, the maximum speedup from `N` processors is:

```
Speedup = 1 / ((1 - f) + f/N)

Example: 80% parallelizable (f=0.8), 100 processors (N=100):
Speedup = 1 / (0.2 + 0.8/100) = 1 / 0.208 = ~4.8x (not 100x!)

Implication: the serial fraction dominates at scale.
Serial bottlenecks (single-threaded code, global locks, sequential DB queries)
MUST be eliminated before throwing more hardware at a problem.
```

### Little's Law

L = λW — the fundamental relationship between throughput, latency, and concurrency:

```
L = average number of requests in the system (concurrency)
λ = throughput (requests per second)
W = average latency (seconds)

Example: 1000 req/s throughput, 50ms average latency:
L = 1000 * 0.050 = 50 concurrent requests

To support 2000 req/s at the same 50ms latency, need to support 100 concurrent requests.
If your thread pool or connection pool has only 50 slots, you will queue and degrade.
```

### USE Method (Brendan Gregg)

For every resource (CPU, memory, disk I/O, network, locks):

```
Utilization  — what % of time the resource is busy
Saturation   — how much work is queued/waiting (queue depth, wait time)
Errors        — error rate for the resource

High utilization (>80%) + high saturation = bottleneck
High errors independent of utilization = hardware/driver fault
```

### RED Method (Tom Wilkie)

For microservices (request-centric):

```
Rate    — requests per second
Errors  — failed requests per second (or error rate %)
Duration — latency distribution (p50, p95, p99)
```

---

## 2. CPU Profiling

### Linux perf

```bash
# System-wide CPU statistics
perf stat -a sleep 5
# Shows: cycles, instructions, IPC (instructions per cycle), cache misses, branch mispredictions

# Profile a specific process for 30 seconds
perf record -F 99 -p <pid> -g -- sleep 30
# -F 99: sample at 99 Hz (avoids lockstep with 100Hz timer)
# -g: capture call stack (DWARF or frame pointer)

# Or run a command under profiling
perf record -F 99 -g -- ./my-binary --args

# Generate report
perf report --stdio | head -50

# Generate flame graph (requires Brendan Gregg's FlameGraph tools)
perf script | stackcollapse-perf.pl | flamegraph.pl > cpu-flamegraph.svg

# One-liner perf on a live PID
perf top -p <pid> -g --sort comm,dso,symbol

# Annotate with source (requires debug symbols)
perf annotate --stdio -l
```

### py-spy (Python)

```bash
# Install
pip install py-spy

# Live top-like view (attaches to running process)
sudo py-spy top --pid <pid>

# Record and generate flame graph (SVG)
sudo py-spy record -o profile.svg --pid <pid> --duration 30

# Or profile a command directly
py-spy record -o profile.svg -- python myapp.py

# Speedscope format (for https://www.speedscope.app)
py-spy record -o profile.speedscope.json --format speedscope --pid <pid>

# Dump current stack traces of all threads (like jstack for Python)
sudo py-spy dump --pid <pid>

# Non-blocking sampling (does not pause GIL — use in production with care)
py-spy record --nonblocking -o profile.svg --pid <pid>
```

### async-profiler (Java)

```bash
# Download: https://github.com/async-profiler/async-profiler/releases
# Uses Linux perf_events for CPU profiling and AsyncGetCallTrace for allocation

# CPU profile for 30 seconds, output flame graph
./profiler.sh -e cpu -d 30 -f /tmp/cpu.html <pid>

# Allocation profiling
./profiler.sh -e alloc -d 30 -f /tmp/alloc.html <pid>

# Wall-clock profiling (includes threads blocked in I/O — useful for finding I/O wait)
./profiler.sh -e wall -d 30 -f /tmp/wall.html <pid>

# Via jattach (attach to running JVM)
jattach <pid> load instrument false async-profiler.jar

# In JVM startup flags (for profiling from start)
-agentpath:/path/to/libasyncProfiler.so=start,event=cpu,file=/tmp/profile.html

# JVM Flight Recorder (JDK 11+, built-in, low overhead)
jcmd <pid> JFR.start duration=60s filename=/tmp/recording.jfr
jcmd <pid> JFR.stop
# Analyze with JDK Mission Control (JMC)
```

### Go pprof

```go
// Enable pprof HTTP endpoint in your application
import _ "net/http/pprof"
import "net/http"

go func() {
    log.Println(http.ListenAndServe("localhost:6060", nil))
}()
```

```bash
# Collect and analyze CPU profile (30 seconds)
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

# Within pprof interactive mode:
(pprof) top10                    # top 10 functions by CPU time
(pprof) list mypackage.Function  # annotated source
(pprof) web                      # open call graph SVG in browser
(pprof) svg > cpu.svg            # save to file

# Goroutine profile (all goroutines + stack traces)
go tool pprof http://localhost:6060/debug/pprof/goroutine

# Mutex contention profile
go tool pprof http://localhost:6060/debug/pprof/mutex

# Block profile (blocking operations: channel waits, sync.Mutex waits)
# Enable first: runtime.SetBlockProfileRate(1)
go tool pprof http://localhost:6060/debug/pprof/block

# Flame graph via pprof -http
go tool pprof -http=:8888 http://localhost:6060/debug/pprof/profile?seconds=30
# Opens browser with interactive flame graph, graph, and top views
```

---

## 3. Memory Profiling

### Valgrind (C/C++)

```bash
# Memory error detection (buffer overflows, use-after-free, leaks)
valgrind --tool=memcheck --leak-check=full --show-leak-kinds=all \
  --track-origins=yes --verbose ./my-binary 2>&1 | tee valgrind.log

# Heap profiling with Massif
valgrind --tool=massif --pages-as-heap=yes ./my-binary
ms_print massif.out.<pid> | head -100

# Visualize Massif output
massif-visualizer massif.out.<pid>   # GUI tool
```

### heaptrack (Linux, lower overhead than Valgrind)

```bash
# Install: apt install heaptrack / brew install heaptrack
heaptrack ./my-binary --args

# Analyze
heaptrack_print heaptrack.my-binary.<pid>.gz | head -50

# GUI analysis
heaptrack_gui heaptrack.my-binary.<pid>.gz
```

### Python memory_profiler

```python
# Install: pip install memory-profiler
from memory_profiler import profile

@profile
def process_large_dataset(data):
    result = [transform(item) for item in data]  # Line-by-line memory shown
    return result

# Output shows MiB increment per line
```

```bash
# Command-line profiling
python -m memory_profiler myapp.py

# Time-series memory tracking
mprof run python myapp.py
mprof plot   # generates matplotlib chart of memory over time

# Memory usage of a running process
from memory_profiler import memory_usage
mem = memory_usage((my_function, (arg1, arg2)), interval=0.1)
print(f"Peak memory: {max(mem):.1f} MiB")
```

### Java Memory Profiling

```bash
# Heap histogram (quick snapshot, no dump needed)
jmap -histo:live <pid> | head -30

# Heap dump for MAT (Memory Analyzer Tool) analysis
jmap -dump:format=b,file=/tmp/heap.hprof <pid>

# Or trigger OOMError dump automatically:
# -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/heap-oom.hprof

# Analyze heap dump with Eclipse MAT
# mat.sh /tmp/heap.hprof
# Look for: Leak Suspects report, Dominator Tree, Object Histograms

# jhat (simple browser-based analysis, JDK bundled)
jhat /tmp/heap.hprof
# Opens at http://localhost:7000

# Java Flight Recorder heap analysis
jcmd <pid> JFR.start settings=profile duration=60s filename=/tmp/recording.jfr
# Analyze in JDK Mission Control: Memory tab → Heap Live Set
```

### Go Heap Profiling

```bash
# Heap profile (in-use objects)
go tool pprof http://localhost:6060/debug/pprof/heap

# Within pprof:
(pprof) top               # top allocators by inuse_space
(pprof) -sample_index alloc_space  # show total allocated (not just in-use)
(pprof) list mypackage.Func        # source-level breakdown

# Difference: inuse_space (currently allocated) vs alloc_space (total allocated over time)
# Use inuse_space to find memory leaks
# Use alloc_space to find allocation hotspots (GC pressure)

# Allocs profile (allocation sampling)
go tool pprof http://localhost:6060/debug/pprof/allocs

# Escape analysis: see what escapes to heap
go build -gcflags='-m -m' ./... 2>&1 | grep "escapes to heap"
```

---

## 4. Flame Graphs

Flame graphs (invented by Brendan Gregg) visualize stack traces sampled from profilers:

```
Y-axis: call stack depth (bottom = on-CPU code, top = bottom of call stack)
X-axis: time spent in that stack (width proportional to sample count)
Color:  random (for legibility, not semantics) unless it's a differential flame graph

Wide towers: functions spending a lot of CPU time — investigate these
Narrow towers: infrequently called — usually not a bottleneck
Flat tops: function appears at top of many samples — it IS the CPU consumer
```

```bash
# Generate from perf output
git clone https://github.com/brendangregg/FlameGraph
perf record -F 99 -g -p <pid> -- sleep 30
perf script | ./FlameGraph/stackcollapse-perf.pl | ./FlameGraph/flamegraph.pl > flame.svg

# Off-CPU flame graphs (blocking time analysis: I/O, locks)
perf record -e 'sched:sched_switch' -a -g -- sleep 30
perf script | ./FlameGraph/stackcollapse-perf.pl | ./FlameGraph/flamegraph.pl \
  --color=io --title="Off-CPU" > offcpu.svg

# Differential flame graph (before vs after optimization)
./FlameGraph/difffolded.pl before.folded after.folded | ./FlameGraph/flamegraph.pl \
  --negate > diff.svg
# Blue = decreased after change (good)
# Red = increased after change (investigate)
```

---

## 5. JVM Tuning

### GC Algorithm Selection

```bash
# G1GC (Garbage First) — DEFAULT in JDK 9+
# Best for: most applications, heap 4GB-100GB, latency-throughput balance
# Typical pause: 10-200ms
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200     # target pause goal (not a guarantee)
-XX:G1HeapRegionSize=16m     # for large heaps; auto-calculated by default

# ZGC — ultra-low pause (<1ms for most workloads)
# Best for: latency-sensitive, heap up to 16TB
# Available: JDK 15+ for production use
-XX:+UseZGC
-XX:ZUncommitDelay=300       # return unused memory to OS after 5 minutes

# Shenandoah — concurrent, low-pause (Red Hat / OpenJDK)
# Similar goals to ZGC, different algorithm
# Available in OpenJDK 12+
-XX:+UseShenandoahGC
-XX:ShenandoahGCHeuristics=adaptive   # default; also: static, compact, aggressive

# SerialGC — single-threaded, tiny heaps (<1GB), CLI tools, containers
-XX:+UseSerialGC

# ParallelGC — throughput-first, acceptable pauses, batch processing
-XX:+UseParallelGC
```

### Heap Sizing

```bash
# Initial and max heap
-Xms4g -Xmx4g    # set equal to prevent resizing pauses (production best practice)

# Young generation size (G1GC manages this automatically; set if needed)
-Xmn1g            # young gen size (avoid with G1; let G1 manage it)

# Metaspace (class metadata; replaces PermGen)
-XX:MetaspaceSize=256m -XX:MaxMetaspaceSize=512m

# Container awareness (JDK 10+, critical for Kubernetes)
# JVM reads cgroup limits automatically
# -XX:MaxRAMPercentage=75.0  (use 75% of container memory limit for heap)
# Example: 2GB container → 1.5GB max heap
-XX:InitialRAMPercentage=50.0
-XX:MaxRAMPercentage=75.0
```

### GC Logging

```bash
# JDK 9+ unified logging
-Xlog:gc*:file=/var/log/gc.log:time,uptime,pid:filecount=5,filesize=20m

# Critical GC events: gc+pause (pause times), gc+heap (heap usage), gc+age (tenuring)
-Xlog:gc+pause=debug,gc+heap=info,gc+age=trace:file=/var/log/gc-detail.log

# Analyze with:
# GCViewer: https://github.com/chewiebug/GCViewer
# GCEasy: https://gceasy.io/ (web-based, free tier)
# JDK Mission Control: JFR integration
```

### JIT Compilation

```bash
# Print JIT compilation events (verbose — use only for profiling, not production)
-XX:+PrintCompilation

# Tiered compilation (C1 → C2 pipeline, enabled by default JDK 8+)
-XX:+TieredCompilation    # already default

# Compilation threshold (method call count before JIT)
-XX:CompileThreshold=10000   # default; lower for warm-up-sensitive apps

# AOT compilation (GraalVM Native Image for startup performance)
native-image -jar myapp.jar myapp-native
# Results in a native binary with <50ms startup vs 3-5s for JVM warmup
```

---

## 6. Go Runtime Tuning

### GOGC and GOMEMLIMIT

```go
// GOGC: target GC percentage (default 100)
// GC triggers when heap size = 2x live set at previous GC
// GOGC=50: more frequent GC, less memory overhead
// GOGC=200: less frequent GC, more memory overhead
// GOGC=off: disable GC (use only in short-lived batch programs)

import "runtime"
runtime.GOMAXPROCS(0)   // 0 = use all CPUs (default)
runtime.SetGCPercent(50) // equivalent to GOGC=50
```

```bash
# Set via environment
GOGC=100 ./myapp           # default
GOGC=50 ./myapp            # lower memory, more GC CPU
GOMEMLIMIT=500MiB ./myapp  # soft heap limit (Go 1.19+)
```

`GOMEMLIMIT` (Go 1.19+) is critical for containers. Without it, the Go GC doesn't know about the container memory limit and will OOM-kill before collecting garbage. Set `GOMEMLIMIT` to ~90% of container memory limit.

```go
import "runtime/debug"
// Set programmatically
debug.SetMemoryLimit(450 * 1024 * 1024)  // 450 MiB
```

### Goroutine Leak Detection

```go
// goleak: test for goroutine leaks
import "go.uber.org/goleak"

func TestNoGoroutineLeaks(t *testing.T) {
    defer goleak.VerifyNone(t)
    // Run code that might leak goroutines
    doSomething()
}
// If goroutines exist at defer point that didn't exist at start → test fails

// pprof goroutine profile shows all current goroutines
go tool pprof http://localhost:6060/debug/pprof/goroutine
(pprof) top              # top goroutine creators
(pprof) traces           # full stack traces of all goroutines
```

### sync.Pool for Allocation Reduction

```go
var bufferPool = sync.Pool{
    New: func() interface{} {
        return make([]byte, 0, 4096)
    },
}

func processRequest(data []byte) []byte {
    buf := bufferPool.Get().([]byte)
    defer func() {
        buf = buf[:0]  // reset length, keep capacity
        bufferPool.Put(buf)
    }()

    buf = append(buf, data...)
    // process...
    return buf
}
// sync.Pool objects may be collected at any GC; don't store long-lived state
```

---

## 7. Node.js Performance

### Event Loop Lag

```javascript
// Measure event loop lag
const { monitorEventLoopDelay } = require('perf_hooks')
const h = monitorEventLoopDelay({ resolution: 20 })
h.enable()
setInterval(() => {
  console.log(`Event loop delay p99: ${h.percentile(99) / 1e6}ms`)
  h.reset()
}, 5000)

// clinic.js: comprehensive Node.js diagnostics
npm install -g clinic
clinic doctor -- node myapp.js     # detects event loop delay, I/O issues
clinic flame -- node myapp.js      # CPU flame graph
clinic bubbleprof -- node myapp.js # async operation profiling
```

### V8 CPU Profiling

```bash
# Built-in profiling
node --prof myapp.js
node --prof-process isolate-*.log > processed.txt

# Inspect with --prof-process
node --prof-process --preprocess -j isolate-*.log | node --prof-process

# Chrome DevTools via --inspect
node --inspect myapp.js
# Open Chrome → chrome://inspect → Connect → Profiler tab

# 0x: beautiful flame graphs for Node.js
npm install -g 0x
0x myapp.js   # records and generates flame graph automatically
```

### Worker Threads for CPU-Bound Work

```javascript
// main.js
const { Worker, isMainThread, parentPort, workerData } = require('worker_threads')

if (isMainThread) {
  function computeInWorker(data) {
    return new Promise((resolve, reject) => {
      const worker = new Worker(__filename, { workerData: data })
      worker.on('message', resolve)
      worker.on('error', reject)
      worker.on('exit', (code) => {
        if (code !== 0) reject(new Error(`Worker stopped with exit code ${code}`))
      })
    })
  }

  // Use a worker pool for repeated CPU-bound tasks
  // (piscina is the canonical worker pool library)
  const Piscina = require('piscina')
  const pool = new Piscina({ filename: './worker.js', maxThreads: 4 })
  const result = await pool.run({ input: largeDataset })
} else {
  // Worker thread code
  const result = expensiveComputation(workerData)
  parentPort.postMessage(result)
}

// libuv thread pool (for fs, dns, crypto operations)
// Default: 4 threads — increase for I/O-heavy workloads
// UV_THREADPOOL_SIZE=16 node myapp.js
```

---

## 8. Database Query Optimization

### PostgreSQL EXPLAIN ANALYZE

```sql
-- Always use EXPLAIN (ANALYZE, BUFFERS) for real execution data
EXPLAIN (ANALYZE, BUFFERS, VERBOSE, FORMAT TEXT)
SELECT u.id, u.email, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.created_at >= '2024-01-01'
GROUP BY u.id
ORDER BY order_count DESC
LIMIT 100;

-- Key metrics to read:
-- "Seq Scan" = no index used (often bad for large tables)
-- "Index Scan" = index used, fetches heap pages
-- "Index Only Scan" = covering index, no heap access (best)
-- actual rows vs estimated rows: large divergence = stale statistics
--   Fix: ANALYZE users; or adjust autovacuum_analyze_scale_factor

-- Slow query log
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- log queries > 1 second
SELECT pg_reload_conf();
-- Or per-session: SET log_min_duration_statement = 500;

-- pg_stat_statements: aggregate query stats (requires extension)
SELECT query, calls, mean_exec_time, total_exec_time, rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

### Index Strategy

```sql
-- B-tree: default, best for equality and range on ordered data
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_orders_created_at ON orders(created_at);

-- Partial index: only index rows matching condition (smaller, faster)
CREATE INDEX idx_orders_pending ON orders(user_id)
WHERE status = 'pending';

-- Covering index (INCLUDE): stores extra columns, enables index-only scans
CREATE INDEX idx_users_email_covering ON users(email) INCLUDE (id, name, created_at);
-- Query SELECT id, name FROM users WHERE email = ? → index-only scan

-- Composite index: column order matters (leftmost prefix rule)
CREATE INDEX idx_orders_user_status ON orders(user_id, status, created_at);
-- Can satisfy: WHERE user_id = ? (yes), WHERE user_id = ? AND status = ? (yes)
-- Cannot efficiently satisfy: WHERE status = ? alone (needs sequential scan or bitmap)

-- GIN: for full-text search, JSONB containment, arrays
CREATE INDEX idx_products_tags ON products USING GIN(tags);
-- WHERE tags @> '{electronics}'::text[]

-- GiST: for geometric/range types, full-text (ts_vector)
CREATE INDEX idx_events_range ON events USING GIST(during);
-- WHERE during && '[2024-01-01, 2024-12-31)'::tsrange

-- BRIN: for naturally ordered data (time-series), very small index
CREATE INDEX idx_metrics_timestamp ON metrics USING BRIN(recorded_at);
-- Efficient for: WHERE recorded_at BETWEEN x AND y on append-only tables

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;  -- idx_scan = 0 → unused index, consider removing
```

### VACUUM and Autovacuum

```sql
-- Manual vacuum (reclaim dead tuples space, update visibility map)
VACUUM ANALYZE users;

-- Aggressive vacuum (reclaims space for reuse, but doesn't return to OS)
VACUUM (FULL, ANALYZE) orders;  -- FULL rewrites table — locks table, use during maintenance

-- Check bloat
SELECT relname, n_dead_tup, n_live_tup,
       round(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct
FROM pg_stat_user_tables
ORDER BY dead_pct DESC;

-- Tune autovacuum for high-write tables
ALTER TABLE orders SET (
    autovacuum_vacuum_scale_factor = 0.01,   -- vacuum when 1% of rows are dead (not 20%)
    autovacuum_analyze_scale_factor = 0.005, -- analyze when 0.5% new rows
    autovacuum_vacuum_cost_delay = 2         -- reduce I/O throttling (ms)
);

-- PgBouncer connection pooling
# pgbouncer.ini
[databases]
myapp = host=127.0.0.1 port=5432 dbname=myapp

[pgbouncer]
pool_mode = transaction      # transaction-level pooling (most efficient)
max_client_conn = 1000       # total client connections
default_pool_size = 25       # server connections per database+user pair
# Rule of thumb: PostgreSQL max_connections = PgBouncer pools × pool_size
# E.g., 4 app pods × 25 pool_size = 100 server connections; set max_connections = 110
```

---

## 9. Network Performance

### TCP Tuning (Linux)

```bash
# View current settings
sysctl net.ipv4.tcp_rmem net.ipv4.tcp_wmem net.core.somaxconn

# Increase TCP buffers for high-throughput connections
echo "net.ipv4.tcp_rmem = 4096 87380 16777216" >> /etc/sysctl.conf
echo "net.ipv4.tcp_wmem = 4096 65536 16777216" >> /etc/sysctl.conf
sysctl -p

# TCP_NODELAY: disable Nagle's algorithm for low-latency (e.g., gRPC, Kafka)
# In application code (Go): conn.(*net.TCPConn).SetNoDelay(true)
# In Linux: already done by most frameworks, but verify

# SO_REUSEPORT: multiple sockets on same port (improves multi-core accept performance)
# Enabled by: nginx, envoy, many modern servers by default
echo "net.ipv4.tcp_fastopen = 3" >> /etc/sysctl.conf  # TCP Fast Open

# Connection backlog (accept queue depth)
echo "net.core.somaxconn = 65535" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65535" >> /etc/sysctl.conf

# TIME_WAIT reuse (for client-side connection exhaustion)
echo "net.ipv4.tcp_tw_reuse = 1" >> /etc/sysctl.conf
```

### HTTP/2 and gRPC

```
HTTP/1.1 with keep-alive: multiple requests on one TCP connection, but sequential
  → Head-of-line blocking: slow request blocks subsequent ones

HTTP/2 multiplexing: multiple concurrent streams over ONE TCP connection
  → No head-of-line blocking at HTTP layer
  → Reduces connection overhead (connection establishment + TLS handshake is expensive)

HTTP/3 + QUIC: HTTP/2 semantics over UDP
  → Eliminates TCP head-of-line blocking (TCP retransmission stalls all streams)
  → 0-RTT reconnection
  → Better on lossy networks (mobile)

gRPC vs REST (HTTP/1.1):
  gRPC: HTTP/2 transport + Protocol Buffers (binary, ~3-10x smaller than JSON)
  gRPC streaming: client/server/bidirectional streaming without new connections
  REST: text-based (JSON), simpler tooling, browser-native

When gRPC wins:
  - High-throughput internal microservice communication
  - Polyglot environments (codegen from .proto)
  - Streaming workloads (real-time, ML inference)

When REST wins:
  - Public APIs (browser compatibility, REST semantics, HTTP caching)
  - Simple request-response, low volume
  - Existing REST ecosystem (Swagger, API gateways)
```

### TLS Session Resumption

```nginx
# TLS session tickets (stateless server-side, fast resumption)
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;  # 50MB ≈ ~200,000 sessions
ssl_session_tickets on;
ssl_session_ticket_key /etc/nginx/ssl/session_ticket.key;  # rotate regularly

# TLS 1.3 session resumption via PSK (pre-shared key) — faster than tickets
# Enabled automatically when ssl_protocols includes TLSv1.3
```

---

## 10. Load Testing Methodology

### Test Types

```
Baseline test: low load, establish performance floor and response time baseline

Stress test: gradually increase load until service degrades
  Goal: find the breaking point; what is maximum throughput before errors spike?

Soak test: sustained moderate load for extended period (30min to 24h)
  Goal: find memory leaks, connection pool exhaustion, log disk fill, GC degradation

Spike test: sudden very high load (10x normal) for short burst
  Goal: find auto-scaling lag, queue buildup, connection pool exhaustion

Breakpoint test: find the exact RPS where the system fails
  Goal: know your capacity ceiling
```

### wrk2 (Constant-Throughput Load Testing)

```bash
# wrk2 uses coordinated omission correction (critical for accurate latency)
# Unlike wrk, wrk2 maintains constant request rate regardless of response time

# Install: git clone https://github.com/giltene/wrk2 && make
./wrk2 -t4 -c100 -d60s -R10000 --latency https://api.example.com/endpoint
# -t4: 4 threads
# -c100: 100 connections
# -d60s: 60 second test
# -R10000: target 10,000 requests/second
# --latency: print latency distribution

# Output includes:
# Latency Distribution
#  50.000%    1.23ms
#  75.000%    1.89ms
#  90.000%    3.45ms
#  99.000%   12.34ms
#  99.900%   45.67ms
#  99.990%  123.45ms
# Requests/sec: 9987.23
```

**Why wrk over wrk**: wrk measures latency only when the system responds — if responses are slow, wrk fires fewer requests and misses the queuing latency. wrk2 fires requests at the configured rate regardless, correctly measuring the full waiting experience.

### SLO Definition

```yaml
# Example SLO definition
service: payment-api
slo:
  - name: availability
    description: "99.9% of valid payment requests succeed"
    sli: good_requests / valid_requests
    target: 99.9%
    window: 30d

  - name: latency
    description: "95% of payment requests complete in under 500ms"
    sli: requests_under_500ms / valid_requests
    target: 95%
    window: 30d

  - name: latency_p99
    description: "99% of payment requests complete in under 2000ms"
    sli: requests_under_2000ms / valid_requests
    target: 99%
    window: 30d
```

### Error Budget and Burn Rate Alerting

```
Monthly error budget = 100% - SLO target
  For 99.9% availability SLO: budget = 0.1% per month = 43.8 minutes/month

Burn rate: how fast you're consuming the error budget
  Burn rate 1x: consuming budget at exactly the pace to exhaust it in 30 days
  Burn rate 6x: at current rate, budget exhausted in 5 days (30/6)
  Burn rate 60x: budget exhausted in 12 hours (30*24/60)

Google SRE-style multi-window alerting:
  Fast burn alert (urgent):    burn_rate > 14x for last 1h AND last 5m
    → exhausts 5% budget in 1 hour; page on-call immediately
  Slow burn alert (warning):   burn_rate > 1x for last 6h AND last 30m
    → exhausts 10% budget in 3 days; ticket for next business day
```

---

## 11. Caching Optimization

### Cache Hit Ratio Analysis

```bash
# Redis: check hit rate
redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses"
# hit_rate = keyspace_hits / (keyspace_hits + keyspace_misses)
# Target: > 90% for most use cases

# Redis memory optimization: check encoding
redis-cli OBJECT ENCODING mykey
# "ziplist" / "listpack": compact, memory-efficient (small values)
# "hashtable": standard (large hash)
# Tune thresholds:
redis-cli CONFIG SET hash-max-listpack-entries 128
redis-cli CONFIG SET hash-max-listpack-value 64

# Monitor evictions
redis-cli INFO stats | grep evicted_keys  # should be 0 unless maxmemory is set
```

### Cache Patterns

```python
# Cache-aside (most common): application manages the cache
def get_user(user_id: str) -> User:
    cached = redis.get(f"user:{user_id}")
    if cached:
        return User.from_json(cached)

    user = db.query_user(user_id)        # cache miss: hit database
    redis.setex(f"user:{user_id}", 300, user.to_json())  # cache 5 minutes
    return user

# Write-through: write to cache and DB simultaneously
def update_user(user_id: str, data: dict) -> User:
    user = db.update_user(user_id, data)
    redis.setex(f"user:{user_id}", 300, user.to_json())  # keep in sync
    return user

# Cache stampede / thundering herd protection
# Probabilistic early expiry (prevents many requests hitting DB simultaneously)
import random, math

def get_with_stampede_protection(key: str, ttl: int, beta: float = 1.0):
    cached = redis.get(key)
    if cached:
        value, expiry_time = parse_cache(cached)
        # Probabilistically decide to recompute before expiry
        delta = time.time() - (expiry_time - ttl)
        if delta * beta * math.log(random.random()) > 0:
            return value  # serve from cache
    # Recompute: either cache miss or probabilistic early refresh
    value = compute_expensive_value(key)
    redis.setex(key, ttl, encode_cache(value, time.time() + ttl))
    return value
```

---

## 12. CDN Performance

### Cache-Control Headers

```http
# Static assets (hashed filenames, immutable)
Cache-Control: public, max-age=31536000, immutable
# immutable: browser won't revalidate even on reload (Chrome/Firefox only)

# HTML pages (short cache, allow stale while revalidating)
Cache-Control: public, max-age=300, stale-while-revalidate=3600, stale-if-error=86400

# API responses (CDN caches, but revalidate)
Cache-Control: public, s-maxage=60, max-age=0, must-revalidate
# s-maxage: CDN TTL (60s); max-age=0: browser always revalidates

# User-specific data: never cache at CDN
Cache-Control: private, no-store

# Vary header: different responses for different Accept-Encoding
Vary: Accept-Encoding    # different cached copy for gzip vs brotli vs none
Vary: Accept-Language    # different cached copy per language (expensive — many cache keys)
```

### Brotli vs gzip

```nginx
# nginx brotli configuration (requires ngx_brotli module)
brotli on;
brotli_comp_level 6;
brotli_types text/plain text/css application/json application/javascript;

# Brotli compression ratios (vs gzip):
# JavaScript: ~15-20% smaller than gzip
# HTML: ~20-25% smaller
# CSS: ~15-20% smaller
# Pre-compress static assets at build time; dynamic content use level 4-6

# Gzip fallback for clients that don't support brotli
gzip on;
gzip_comp_level 6;
gzip_vary on;
```

---

## 13. OpenTelemetry and Distributed Tracing

```go
// Go: OpenTelemetry SDK
import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
    "go.opentelemetry.io/otel/sdk/trace"
)

func initTracer(ctx context.Context) (*trace.TracerProvider, error) {
    exporter, err := otlptracehttp.New(ctx,
        otlptracehttp.WithEndpoint("otel-collector:4318"),
        otlptracehttp.WithInsecure(),
    )
    if err != nil {
        return nil, err
    }
    tp := trace.NewTracerProvider(
        trace.WithBatcher(exporter),
        trace.WithSampler(trace.TraceIDRatioBased(0.1)),  // 10% sampling
    )
    otel.SetTracerProvider(tp)
    return tp, nil
}

// Instrument a function
func processOrder(ctx context.Context, orderID string) error {
    tracer := otel.Tracer("payment-service")
    ctx, span := tracer.Start(ctx, "processOrder",
        oteltrace.WithAttributes(
            attribute.String("order.id", orderID),
            attribute.String("service.name", "payment-service"),
        ),
    )
    defer span.End()

    // Add event
    span.AddEvent("payment.authorized", oteltrace.WithAttributes(
        attribute.Float64("amount", 99.99),
    ))

    result, err := chargeCard(ctx, orderID)
    if err != nil {
        span.RecordError(err)
        span.SetStatus(codes.Error, err.Error())
        return err
    }

    span.SetAttributes(attribute.String("payment.id", result.ID))
    return nil
}
```

---

## 14. Continuous Performance

### Benchmarks in CI

```go
// Go benchmarks
func BenchmarkProcessOrder(b *testing.B) {
    b.ReportAllocs()
    order := makeTestOrder()

    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        _ = ProcessOrder(order)
    }
}

// Run and compare with benchstat
go test -bench=BenchmarkProcessOrder -benchmem -count=10 ./... > new.txt
benchstat old.txt new.txt
# Output:
# name             old time/op    new time/op    delta
# ProcessOrder     1.23ms ± 2%    0.89ms ± 3%   -27.6%  (p=0.000 n=10+10)
# ProcessOrder     45.2kB ± 0%    32.1kB ± 0%   -29.0%  (p=0.000 n=10+10)
# p=0.000 means statistically significant
```

```java
// JMH (Java Microbenchmark Harness) — the only trustworthy Java benchmark tool
@State(Scope.Thread)
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 10, time = 1)
public class OrderProcessorBenchmark {

    private OrderProcessor processor;
    private Order testOrder;

    @Setup
    public void setUp() {
        processor = new OrderProcessor();
        testOrder = OrderFactory.createTestOrder();
    }

    @Benchmark
    public OrderResult processOrder() {
        return processor.process(testOrder);
    }
}
```

```bash
# Run JMH
mvn package -DskipTests
java -jar target/benchmarks.jar -f 1 -wi 5 -i 10

# CI: fail build if benchmark degrades >10%
# Use JMH JSON output + custom comparison script
java -jar benchmarks.jar -rf json -rff baseline.json
java -jar benchmarks.jar -rf json -rff current.json
python compare_benchmarks.py --threshold 0.10 baseline.json current.json
```

---

## 15. Anti-Hallucination Protocol

1. **perf requires Linux**: `perf` is Linux-specific (uses kernel perf_events). On macOS, use Instruments (Xcode). On Windows, use Windows Performance Analyzer (WPA). Never recommend `perf` for macOS profiling.
2. **async-profiler vs JProfiler**: async-profiler is open source and uses the JVM's `AsyncGetCallTrace` API (accurate even during GC). JProfiler and YourKit are commercial. jvisualvm (bundled with JDK) uses safepoint-based sampling, which biases toward safepoints.
3. **GOGC=off warning**: GOGC=off disables garbage collection entirely — the process will consume memory until OOM. Safe only for short-lived batch programs that exit before memory becomes critical.
4. **GOMEMLIMIT is a soft limit**: Go's GOMEMLIMIT doesn't hard-cap memory — it adjusts GC aggressiveness to stay under the limit. The process can still exceed it briefly. It is not a substitute for operating system memory limits (cgroup limits).
5. **Node.js worker_threads vs cluster**: `worker_threads` shares memory (SharedArrayBuffer); `cluster` creates separate processes. For CPU-bound parallelism within a single process, use `worker_threads`. For horizontal scaling of the event loop, use `cluster` or deploy multiple container replicas.
6. **wrk vs wrk2**: wrk does NOT account for coordinated omission — if responses are slow, wrk fires fewer requests and underreports latency. wrk2 is the correct tool for constant-rate load testing. Always use wrk2 when latency accuracy matters.
7. **EXPLAIN vs EXPLAIN ANALYZE**: EXPLAIN shows the planner's estimated plan. EXPLAIN ANALYZE actually executes the query and shows real timing. For read operations, `EXPLAIN (ANALYZE, BUFFERS)` is safe. For write operations, wrap in a transaction and rollback: `BEGIN; EXPLAIN ANALYZE UPDATE ...; ROLLBACK;`
8. **pg_stat_statements requires extension**: `CREATE EXTENSION pg_stat_statements;` must be added to `shared_preload_libraries` before it collects data. It is not available by default on all managed PostgreSQL services.
9. **ZGC production-readiness**: ZGC was experimental until JDK 15, became production-ready in JDK 15 (Linux), macOS/Windows support in JDK 14. Always verify minimum JDK version requirement for GC algorithm selection.
10. **FIPS 140-3 for Go crypto**: Go's standard library crypto/tls is not FIPS 140 validated by default. FIPS-compliant Go requires a FIPS-validated build (e.g., using BoringSSL via `GOEXPERIMENT=boringcrypto` in specific Go toolchain builds from Google or Red Hat).

---

## 16. Self-Review Checklist

Before delivering any performance engineering advice:

- [ ] **Profiling precedes optimization** — every recommendation is backed by profiler data, not intuition or assumption.
- [ ] **Amdahl's Law applied** — if recommending parallelism, identified the serial fraction that limits maximum speedup.
- [ ] **perf tool availability confirmed** — `perf` is Linux-only; alternative tools noted for macOS/Windows.
- [ ] **JVM GC algorithm matched to JDK version** — ZGC production-ready from JDK 15, not JDK 11 or 12.
- [ ] **GOMEMLIMIT context provided** — always paired with advice to also set container memory limit and cgroup.
- [ ] **`EXPLAIN ANALYZE` transaction wrapping advised for write queries** — destructive queries without transaction wrapper will mutate production data.
- [ ] **pg_stat_statements extension requirement noted** — it must be preloaded; cannot be created on-the-fly.
- [ ] **wrk2 recommended over wrk for latency measurement** — coordinated omission correction is essential for accurate load test results.
- [ ] **Cache TTL strategy includes stampede protection** — popular keys with simultaneous expiry will cause a thundering herd on the database.
- [ ] **Connection pool sizing follows Little's Law** — pool_size × number_of_app_instances must be < database max_connections.
- [ ] **Benchmark statistical significance verified** — benchstat `-count=10` minimum; p-value < 0.05 required before declaring a regression or improvement.
- [ ] **SLO window type specified** — rolling window (last 30 days) vs calendar window (calendar month) have different engineering implications for alerting.
- [ ] **Flame graph tool chain verified** — `stackcollapse-perf.pl` and `flamegraph.pl` are separate scripts from Brendan Gregg's FlameGraph repo; they are not part of the `perf` binary.
- [ ] **async-profiler safe attachment conditions noted** — async-profiler requires `ptrace` capabilities or running as same user as JVM; container security contexts may block attachment.
- [ ] **Redis `OBJECT ENCODING` verified against Redis version** — `listpack` encoding was introduced in Redis 7.0 (replacing ziplist for some data types); `ziplist` terminology is correct for Redis < 7.0.
