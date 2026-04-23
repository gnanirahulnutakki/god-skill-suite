---
name: god-tech-support
description: "God-level technical support and debugging skill for any engineer who has to diagnose, troubleshoot, or resolve complex technical issues. Covers systematic root cause analysis (RCA), reading and interpreting stack traces (Java, Python, Go, Node.js, Rust), log analysis (structured and unstructured), Linux system debugging, Java heap dumps and thread dumps, Python profiling and memory analysis, Kubernetes pod debugging, network issue diagnosis, database query diagnosis, distributed system debugging, incident triage, and the researcher-warrior approach to never giving up on a problem. This skill turns any engineer into the person who solves the problem nobody else can solve."
metadata:
  version: "1.0.0"
---

# God-Level Technical Support and Debugging

> The best debugger in the world is an engineer who refuses to accept "I don't know" as a final answer. Every bug has a cause. Every cause has evidence. Your job is to find the evidence.

## Researcher-Warrior Mindset

You are a scientist investigating a crime scene. The system is the crime scene. Your assumptions are the enemy. When you walk in, you bring a hypothesis, tools, and zero ego. You change one variable at a time. You take notes. You are wrong multiple times before you are right. That is normal. That is the process.

**Anti-hallucination rules for this domain:**
- Never invent command flags. Verify flag syntax with `man <command>` or `--help` before using.
- Never guess at JVM flags without knowing the JVM version (behavior changed significantly from Java 8 → 11 → 17 → 21).
- When describing database EXPLAIN output, specify the database version (PostgreSQL 14 EXPLAIN ANALYZE differs from MySQL 8.0).
- Never claim a tool can diagnose something it cannot. `top` shows CPU/memory. It does not show disk I/O per process — use `iostat -p` or `iotop` for that.
- If a diagnostic step requires root/sudo in a production environment, flag it explicitly.

---

## 1. The Debugging Mindset — Scientific Method Applied to Systems

### The Rules
1. **Hypothesis before action.** Never click buttons or run commands randomly. Form a hypothesis about the cause before investigating.
2. **One change at a time.** If you change two things simultaneously and the problem disappears, you learned nothing.
3. **Take notes.** What you ran, what it returned, what you concluded. Without notes, you will repeat yourself.
4. **Distinguish observation from interpretation.** "The CPU is at 98%" is an observation. "The CPU is high because of the database query" is an interpretation that requires evidence.
5. **Ask: what changed?** Most production incidents are caused by a change — code deployment, config change, traffic increase, infrastructure change, dependency update. Start with the change timeline.

### The Scientific Loop
```
OBSERVE: What is the symptom? What exactly is broken?
HYPOTHESIZE: What could cause this observation?
PREDICT: If hypothesis H is true, then I should see X.
TEST: Run a diagnostic that would confirm or falsify X.
ANALYZE: Did I see X? If yes, more evidence for H. If no, eliminate H.
REPEAT: Until root cause is identified with sufficient confidence.
```

### Cognitive Biases to Resist
- **Confirmation bias**: you think it's a database issue, so you only look at database metrics. Force yourself to check other things.
- **Recency bias**: it "always worked before" is not evidence. The system changed.
- **Availability heuristic**: the last incident was a memory leak, so this one must be too. It might not be.

---

## 2. Stack Trace Reading

### Java Stack Traces

A Java exception trace reads bottom-up for causation, top-down for the most recent call.

```
java.lang.NullPointerException: Cannot invoke "String.length()" because "str" is null
    at com.example.UserService.validateEmail(UserService.java:47)   ← most recent
    at com.example.UserService.createUser(UserService.java:23)
    at com.example.UserController.register(UserController.java:89)
    at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
    ... 42 more frames (Spring/framework noise — skip down to your code)
Caused by: java.sql.SQLException: Connection refused
    at com.example.db.ConnectionPool.getConnection(ConnectionPool.java:112)
    ... 6 more frames
```

**How to read it:**
- Start at the top: `NullPointerException` at `UserService.java:47`. Go there first.
- If there is a `Caused by:` chain, the **deepest** `Caused by:` is the root cause. Work backward.
- Skip framework frames (Spring, Hibernate, Tomcat internal traces) to find YOUR code.
- Note the thread name in thread dumps: `"http-nio-8080-exec-1"` tells you the request thread.

**Deadlock detection in thread dumps:**
```
Found one Java-level deadlock:
"Thread-1":
  waiting to lock monitor 0x00007f... (object 0x..., a java.lang.Object),
  which is held by "Thread-2"
"Thread-2":
  waiting to lock monitor 0x00007f... (object 0x..., a java.lang.Object),
  which is held by "Thread-1"
```
The JVM detects deadlocks and reports them in `jstack` output. Thread-1 holds A and wants B. Thread-2 holds B and wants A. Classic deadlock.

### Python Tracebacks

```
Traceback (most recent call last):
  File "app.py", line 15, in <module>
    result = process_data(data)
  File "processor.py", line 42, in process_data
    return transform(item)          ← call chain, most recent last
  File "processor.py", line 67, in transform
    return item['value'] / item['count']
KeyError: 'count'                   ← the actual exception, at the bottom
```

Read the bottom line first: `KeyError: 'count'`. Then walk up the call chain to understand how you got there.

**asyncio task traces:**
```
Task exception was never retrieved
future: <Task finished name='Task-1' coro=<fetch_data() done> exception=aiohttp.ClientTimeout()>
Traceback (most recent call last):
  File "fetcher.py", line 34, in fetch_data
    async with session.get(url, timeout=5) as response:
aiohttp.ServerTimeoutError: Connection timeout
```
In asyncio, exceptions in fire-and-forget tasks are silently dropped unless the task is awaited or a `done_callback` is set. Enable `PYTHONASYNCIODEBUG=1` or call `asyncio.get_event_loop().set_debug(True)` to surface these.

### Go Goroutine Dumps

```
goroutine 1 [running]:
main.main()
        /app/main.go:25 +0x8a

goroutine 18 [chan receive]:
main.worker(0xc000012060)
        /app/worker.go:45 +0x1c4
created by main.main in goroutine 1
        /app/main.go:18 +0x6b

goroutine 23 [select, 2 minutes]:    ← blocked for 2 minutes
```

Goroutine states: `running`, `runnable`, `chan receive` (blocked on channel), `chan send` (blocked writing to full channel), `select` (blocked in select), `sleep`, `syscall`.

A goroutine blocked for minutes in `chan receive` often indicates a goroutine leak — the producer died but the consumer is still waiting.

**Panic trace:**
```
panic: runtime error: index out of range [5] with length 3

goroutine 1 [running]:
main.processSlice(...)
        /app/main.go:12 +0x1d4
```
Go panics include a full goroutine dump. Look for the exact panic reason and the first non-runtime frame in your code.

### Node.js Async Stack Traces

```
Error: connect ECONNREFUSED 127.0.0.1:5432
    at TCPConnectWrap.afterConnect [as oncomplete] (net.js:1141:16)
    at async pgPool.connect (/app/db.js:23:5)
    at async UserService.findById (/app/services/user.js:45:12)
    at async GET /users/:id (/app/routes/users.js:18:5)
```

Modern Node.js (v14+) with async/await produces reasonable stack traces. The old callback-style code produced truncated traces because the event loop would unwind the call stack between callbacks.

To get full async stack traces: run with `--async-context` flag (Node 18+) or use `node --stack-trace-limit=50` to increase captured frame depth.

### Rust Backtraces

```
RUST_BACKTRACE=1 cargo run
thread 'main' panicked at 'index out of bounds: the len is 3 but the index is 5', src/main.rs:12:5
stack backtrace:
   0: rust_begin_unwind
   1: core::panicking::panic_fmt
   2: core::slice::index::slice_index_usize_fail
   3: myapp::process_data           ← your code starts here
   4: myapp::main
```

Use `RUST_BACKTRACE=full` for complete traces including line numbers. For SIGSEGV in Rust code (rare in safe Rust, common in `unsafe` blocks), use `RUST_BACKTRACE=full` and look for the unsafe block.

---

## 3. Java Deep Debugging

### Heap Dump Analysis

Capture a heap dump from a running JVM:
```bash
jmap -dump:format=b,file=heap.hprof <pid>
# Or trigger automatically on OOM:
# -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/tmp/
```

Analyze with Eclipse Memory Analyzer (MAT) or VisualVM:
1. Open the `.hprof` file in MAT
2. Run "Leak Suspects Report" — MAT identifies the largest object retained in memory
3. Use "Dominator Tree" to find the object retaining the most memory
4. Use "OQL" (Object Query Language) to query specific classes: `SELECT * FROM java.util.HashMap`

**OutOfMemoryError types:**
- `java.lang.OutOfMemoryError: Java heap space` — heap is full. Check for memory leaks (retained objects), then consider increasing `-Xmx`.
- `java.lang.OutOfMemoryError: Metaspace` — class metadata space full. Classloader leak (common in app servers with hot reloading). Check: `jcmd <pid> VM.class_stats`.
- `java.lang.OutOfMemoryError: GC overhead limit exceeded` — GC spending >98% of time but recovering <2% of heap. Classic heap exhaustion pattern. Profile allocations before increasing heap.
- `java.lang.OutOfMemoryError: unable to create new native thread` — OS thread limit reached. Check: `ulimit -u`, `/proc/sys/kernel/threads-max`.

### Thread Dump Analysis

```bash
jstack <pid> > thread_dump.txt
# OR from within the JVM:
kill -3 <pid>   ← prints to stdout/logs (non-terminating SIGQUIT on JVM)
```

What to look for:
- Threads in `BLOCKED` state waiting for a lock → contention or deadlock
- Threads in `WAITING` or `TIMED_WAITING` on the same monitor → potential deadlock
- Many threads in the same state at the same location → bottleneck at that code path
- Thread pool exhaustion: all `http-nio-*-exec-*` threads in `BLOCKED` → upstream service is hanging

Use https://fastthread.io for automated thread dump analysis (paste thread dump, get visual analysis).

### GC Log Analysis

Enable GC logging (Java 9+):
```
-Xlog:gc*:file=/var/log/gc.log:time,uptime,level,tags:filecount=5,filesize=20m
```

Key events to look for:
- **Minor GC (Young GC)**: short pause, collects young generation. Normal if pause < 50ms.
- **Major GC / Full GC**: pauses entire application (stop-the-world). Pause > 1 second is a problem.
- **G1GC Evacuation Failure**: G1 couldn't move objects — heap fragmentation. Tune `-XX:G1HeapRegionSize`.
- **ZGC / Shenandoah**: designed for sub-millisecond pauses. Use for latency-sensitive applications on Java 15+.

---

## 4. Python Debugging

### Interactive Debugging
```python
import pdb; pdb.set_trace()   # drop into debugger at this line
# Python 3.7+:
breakpoint()                   # same thing, respects PYTHONBREAKPOINT env var
```

pdb commands: `n` (next), `s` (step into), `c` (continue), `p expr` (print), `l` (list source), `w` (where/stack), `q` (quit).

For Jupyter: use `%debug` magic after an exception, or `%pdb on` for auto-debugging.

### Memory Profiling

**tracemalloc** (stdlib, no installation required):
```python
import tracemalloc
tracemalloc.start()
# ... code under test ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

**memory_profiler** (line-by-line memory usage):
```bash
pip install memory-profiler
python -m memory_profiler my_script.py
```

**py-spy** (sampling profiler, zero code modification, works on live processes):
```bash
pip install py-spy
py-spy top --pid <pid>               # live flame graph in terminal
py-spy record -o profile.svg --pid <pid>  # SVG flame graph
```
py-spy is critical because it does not require modifying the running code and works on hung processes. Use it in production when you cannot modify the code.

### asyncio Debugging
```python
import asyncio
import logging
logging.basicConfig(level=logging.DEBUG)

async def main():
    loop = asyncio.get_event_loop()
    loop.set_debug(True)    # warns on slow callbacks, unawaited coroutines
    loop.slow_callback_duration = 0.1  # warn if callback takes > 100ms
```

---

## 5. Linux System Debugging

### CPU and Memory

```bash
top -H -p <pid>       # show individual threads for a process
htop                  # interactive, visual, press F5 for tree view
vmstat 1              # system-wide: procs blocked, memory, swap, io, cpu per second
pidstat -p <pid> 1    # per-process CPU/memory stats over time
```

**vmstat output interpretation:**
```
r: runnable processes (consistently > CPU count = CPU saturation)
b: blocked on I/O
swpd: swap used (any swap under memory pressure is concerning)
bi/bo: blocks in/out per second (disk I/O)
wa: CPU% waiting for I/O (> 20% = I/O bottleneck)
```

### Disk I/O

```bash
iostat -x 1           # extended I/O stats per device, every second
iotop -o              # which processes are doing the most I/O (requires root)
```

`iostat` `%util` column: > 80% sustained = disk is saturated.

### System Calls

```bash
strace -p <pid>       # trace system calls of a running process
strace -c -p <pid>    # count system calls, show most expensive (overhead: high)
strace -e trace=open,read,write -p <pid>  # filter to specific syscalls
```

**Warning**: `strace` adds ~10-50x overhead to the traced process. Use briefly in production, or use `perf trace` for lower overhead.

```bash
ltrace -p <pid>       # trace library calls (not syscalls)
```

### File and Network

```bash
lsof -p <pid>         # all open files, sockets, pipes for a process
lsof -i :8080         # which process is listening on port 8080
ss -tlnp              # listening TCP sockets with PID (replaces netstat -tlnp)
ss -s                 # socket summary (connection state counts)
ss -tp state ESTABLISHED  # all established connections
```

### CPU Profiling

```bash
perf top -p <pid>     # live CPU profiling (like top but per function)
perf record -g -p <pid> sleep 30   # record 30 seconds with call graph
perf report                        # analyze recording
```

### /proc Filesystem

```bash
cat /proc/<pid>/status        # memory, threads, file descriptors in use
cat /proc/<pid>/fd | wc -l    # count open file descriptors
ls -la /proc/<pid>/fd/        # what each fd points to
cat /proc/<pid>/limits        # current ulimits for the process
cat /proc/<pid>/net/tcp       # open TCP connections (hex addresses)
```

---

## 6. Log Analysis

### Structured Log Parsing with jq

```bash
# Filter JSON logs where level is ERROR
cat app.log | jq 'select(.level == "ERROR")'

# Count errors by error_code
cat app.log | jq -r '.error_code' | sort | uniq -c | sort -rn

# Find all requests with latency > 1000ms
cat app.log | jq 'select(.duration_ms > 1000) | {time: .timestamp, path: .path, duration: .duration_ms}'

# Correlate all logs for a trace_id
cat app.log | jq 'select(.trace_id == "abc123")'
```

### grep Patterns for Incident Investigation

```bash
# Count error occurrences per minute
grep "ERROR" app.log | grep -oP '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}' | sort | uniq -c

# Find the first occurrence of an error
grep -m 1 "OutOfMemoryError" app.log

# Find error with 5 lines of context
grep -A 5 -B 2 "NullPointerException" app.log

# Search across multiple compressed log files
zgrep "ERROR" /var/log/app/app.log.*.gz
```

### awk for Field Extraction

```bash
# Sum the 4th column (e.g., response time in access log)
awk '{sum += $4; count++} END {print "avg:", sum/count}' access.log

# Extract unique status codes and their counts
awk '{print $9}' access.log | sort | uniq -c | sort -rn
```

### Log Correlation by trace_id (Distributed Tracing)

In a microservices system, every request should carry a `trace_id` (a UUID generated at the entry point, propagated via headers — `X-Trace-Id` or `traceparent` from W3C Trace Context). Correlate incidents across services by searching all logs for the trace_id of the failing request.

```bash
# Find trace_id of a failed request
grep "500" api-gateway.log | tail -1 | jq '.trace_id'

# Search that trace_id across all service logs
for service in api-gateway user-service order-service; do
  echo "=== $service ===" 
  grep "abc-trace-id-123" /var/log/$service/app.log | jq '.'
done
```

---

## 7. Kubernetes Pod Debugging

### Basic Pod Inspection

```bash
kubectl describe pod <pod-name> -n <namespace>   # events, conditions, resource usage
kubectl logs <pod-name> -n <namespace>           # current logs
kubectl logs <pod-name> -n <namespace> --previous  # logs from previous (crashed) container
kubectl logs <pod-name> -n <namespace> -f        # follow
kubectl logs <pod-name> -n <namespace> --since=10m  # last 10 minutes
kubectl top pod <pod-name> -n <namespace>        # current CPU/memory
```

### Exec and Debug

```bash
# Shell into a running container
kubectl exec -it <pod-name> -n <namespace> -- /bin/sh

# Ephemeral debug container (kubectl 1.23+, no distroless limitation)
kubectl debug -it <pod-name> -n <namespace> --image=busybox --target=<container-name>

# Debug a node (requires node-shell plugin or privileged pod)
kubectl node-shell <node-name>   # requires kubectl-node-shell plugin
```

**Debugging distroless containers**: distroless images have no shell. Use `kubectl debug` with an ephemeral container that has debugging tools — the debug container shares the process namespace.

### Events — The Most Useful Section of `describe`

The `Events:` section at the bottom of `kubectl describe pod` shows: OOMKilled (exceeded memory limit), ImagePullBackOff (can't pull image), CrashLoopBackOff (container crashing repeatedly — check `--previous` logs), Pending (scheduling failure — check node resources).

```bash
# Watch events for the entire namespace
kubectl get events -n <namespace> --sort-by='.lastTimestamp' -w
```

### Network Policy Testing

```bash
# Deploy netshoot (network debug container) in the namespace
kubectl run netshoot --image=nicolaka/netshoot -n <namespace> --rm -it --restart=Never

# Inside netshoot: test connectivity
curl -v http://target-service.namespace.svc.cluster.local:8080
nslookup target-service.namespace.svc.cluster.local
tcpdump -i eth0 port 8080
```

---

## 8. Database Query Debugging

### PostgreSQL — EXPLAIN ANALYZE

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) 
SELECT * FROM orders WHERE user_id = 123 ORDER BY created_at DESC LIMIT 20;
```

What to look for:
- **Seq Scan** on a large table: missing index. Add index on the filter column.
- **Nested Loop** with many rows: can be expensive. Consider Hash Join or Merge Join.
- **Actual Rows** vs **Rows**: large discrepancy means outdated statistics. Run `ANALYZE orders`.
- **Buffers: shared hit vs read**: high `read` means data not in cache (cold cache or too little `shared_buffers`).
- **actual time**: the actual execution time of each node. Find the most expensive node.

Use https://explain.dalibo.com to visualize PostgreSQL explain output.

### MySQL — Slow Query Log

```sql
-- Enable slow query log
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1.0;  -- log queries > 1 second
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';

-- Analyze slow log
mysqldumpslow -s t -t 20 /var/log/mysql/slow.log  -- top 20 by total time

-- EXPLAIN for a specific query
EXPLAIN FORMAT=JSON SELECT * FROM orders WHERE user_id = 123;
```

### Redis Debugging

```bash
redis-cli MONITOR          # log all commands in real time — HIGH OVERHEAD, use briefly
redis-cli SLOWLOG GET 25   # last 25 slow commands (default threshold: 10ms)
redis-cli SLOWLOG RESET    # clear slow log
redis-cli INFO memory      # memory usage, fragmentation ratio
redis-cli INFO stats       # hits/misses, connections, keyspace
redis-cli --bigkeys        # find largest keys (uses SCAN, safe for production)
```

**Warning**: `MONITOR` doubles the memory bandwidth of the Redis server. Never leave it running in production.

---

## 9. Distributed System Debugging

### Tracing a Request Across 5 Microservices

1. Get the `trace_id` from the failing request (from gateway logs, from the user's error message, from your error tracking system).
2. Query your observability backend (Jaeger, Tempo, Zipkin, Datadog APM, AWS X-Ray) for that trace_id.
3. Find the span where the error occurred (red span in Jaeger).
4. Correlate the span with application logs by searching for `trace_id` in the service's logs.
5. Check: did the error originate in this service or did it propagate from a downstream call?

### Identifying Cascading Failures

Pattern: one service (Service C) becomes slow. Service B calls Service C and threads back up waiting. Service B's thread pool exhausts. Service A calls Service B and gets timeouts. Service A looks broken even though its code is fine.

Diagnosis: look at **latency** not just **error rate**. A service that is timing out rather than fast-failing will show elevated latency before elevated error rate. If latency spiked first, the issue is upstream from the error.

Circuit breaker pattern (Resilience4j, Hystrix, built into Istio): automatically stop calling a failing service and fast-fail instead of propagating latency.

### Correlating Latency with Deployment Events

```bash
# Pull deployment timestamps from your CI/CD system
# Then correlate with your metrics system (Prometheus, Datadog)

# Prometheus: check if latency spiked at the same time as the deployment
http_request_duration_seconds{quantile="0.99"}
```

Always add vertical "deployment" markers to your dashboards. The single most common cause of a latency spike is a code deployment that happened 10 minutes ago.

---

## 10. Incident Triage

### First 5 Minutes

1. **What is broken?** Define the exact symptom. "The site is slow" is not enough. "The /checkout endpoint returns HTTP 503 for 34% of requests" is.
2. **Who is affected?** All users? Some geographic regions? Users on a specific plan? New users only?
3. **What is the blast radius?** Revenue impact, user count, SLA implications.
4. **What changed?** Check deployment history, config changes, infrastructure changes, dependency updates in the last 2 hours.
5. **Start the incident thread.** Communication starts NOW, even before you have answers.

### Communication Cadence (During Incident)
- Every 15-30 minutes: status update to stakeholders, even if the update is "we are still investigating"
- When root cause is identified: immediate update with cause and ETA for resolution
- After resolution: incident timeline post-mortem (within 24-48 hours for major incidents)

### Escalation Criteria
- Escalate immediately if: data loss or corruption is possible, security breach suspected, incident duration exceeds 30 minutes with no progress, you need access you don't have.
- Escalate by adding people, not by waiting. Two people working a problem in parallel find it faster.

---

## 11. Root Cause Analysis (RCA) Methodology

### 5 Whys with Systems Thinking

The 5 Whys is a tool, not a religion. Ask why until you reach a cause you can act on — which is usually a process or design failure, not a human error.

**Bad 5 Whys** (stops at blame):
1. Why did the service go down? Because the engineer deployed broken code.
2. Why did the engineer deploy broken code? Because they didn't test it.
→ "Implement code review" (surface level, will not prevent recurrence)

**Good 5 Whys** (finds systemic cause):
1. Why did the service go down? Memory limit was exceeded.
2. Why was memory limit exceeded? A cache was never evicted.
3. Why was the cache never evicted? The eviction logic had an off-by-one bug.
4. Why did the off-by-one bug reach production? The test suite didn't cover the eviction code path.
5. Why was the eviction code path untested? There is no coverage requirement for edge cases in the CI pipeline.
→ **Action**: Add coverage gates to CI AND fix the eviction logic AND add regression test.

### Proximate vs Distal Cause
- **Proximate cause**: the immediate trigger (the bug in the code)
- **Distal cause**: the underlying condition that allowed the proximate cause to have impact (the lack of circuit breaker, the missing test, the insufficient monitoring)

A good post-mortem addresses both.

---

## 12. Never Give Up Rules

These are not suggestions. They are protocols.

- **30 minutes stuck**: Change your approach. You are now biased toward your current hypothesis. Take 5 minutes to write down three alternative hypotheses. Investigate one of the alternatives.
- **2 hours stuck**: Get another pair of eyes. Explaining the problem out loud (rubber duck debugging + human) will almost always surface something new. The person you bring in does not need to know the system — they need to ask "why" questions.
- **4 hours stuck with user impact**: Implement a mitigation/workaround to reduce user impact (feature flag off, rollback if applicable, increase rate limits to absorb traffic) WHILE continuing root cause investigation in parallel. Never hold users hostage to your debugging session.
- **1 day stuck**: Escalate AND keep working. Write up everything you know — symptoms, evidence, eliminated hypotheses, current hypothesis. This document is valuable even if you never find the cause. It will help the next person.
- **Rule**: "I don't know" is never a final answer. "I don't know yet, and here is what I'm doing to find out" is always an acceptable status.

---

## Cross-Domain Connections

- **Debugging + API design**: A well-designed API returns RFC 7807 error details that make client-side debugging immediate. An API that returns `{"error": "something went wrong"}` creates support tickets that require server-side log correlation every time.
- **Debugging + Distributed systems**: `trace_id` propagation is not optional. Without it, debugging distributed failures requires correlating logs across services by timestamp — imprecise and painful.
- **Java debugging + Kubernetes**: Kubernetes `OOMKilled` events mean the container exceeded its memory limit. The container limit and the JVM `-Xmx` are separate — the container limit must be larger than `-Xmx` plus JVM overhead (metaspace, code cache, thread stacks). Set `-Xmx` to 70-75% of the container memory limit.
- **Log analysis + Security**: Logs are also a security audit trail. Structured logging with user_id, ip, trace_id on every request enables forensic investigation. Missing structured logs is a security gap as much as a debugging gap.
- **Profiling + Cost**: py-spy and perf are the difference between "we need to 10x our server count" and "we found the 3-line hot path that was causing 80% of CPU usage." Profile before scaling.

---

## Self-Review Checklist (15 Items)

Before closing any debugging investigation or incident:

- [ ] 1. Root cause is identified with evidence, not just a hypothesis that "seems right"
- [ ] 2. The "what changed" question has been answered (code, config, traffic, dependency)
- [ ] 3. Symptoms are precisely defined with metrics (not "it was slow" but "p99 latency was 8s")
- [ ] 4. At least 3 alternative hypotheses were considered and either confirmed or eliminated
- [ ] 5. Changes during debugging were made one at a time and documented
- [ ] 6. A mitigation or workaround was put in place if users were affected while investigation continued
- [ ] 7. Relevant logs were captured and preserved before they rotated out
- [ ] 8. Diagnostic tool output was saved, not just read and forgotten
- [ ] 9. The incident was communicated to stakeholders with status updates every 15-30 minutes
- [ ] 10. A regression test exists (or is planned) that would catch this issue in the future
- [ ] 11. Monitoring/alerting has been improved so this is detected faster next time
- [ ] 12. RCA document covers both proximate cause and distal (systemic) cause
- [ ] 13. Action items from the RCA are assigned to owners with due dates
- [ ] 14. The post-mortem is blameless — it addresses process and system failures, not human failures
- [ ] 15. The "never give up" rules were followed — no investigation was abandoned without escalation
---
