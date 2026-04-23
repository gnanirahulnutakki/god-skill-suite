---
name: god-sre-reliability
description: "God-level SRE and reliability engineering skill. Covers SLI/SLO/SLA design, error budgets, toil elimination, incident management (detection, response, retrospective), on-call excellence, capacity planning, chaos engineering (Chaos Monkey, Litmus, fault injection), load testing (k6, Locust, JMeter, Gatling), runbook authoring, reliability patterns (circuit breaker, bulkhead, retry, timeout, fallback), postmortem culture, and reliability as a feature. Draws from Google SRE Book, 'Seeking SRE', and 'Building Secure and Reliable Systems'. The researcher-warrior SRE treats every incident as a research paper to be written and every on-call shift as a field expedition."
metadata:
  domain: "\"reliability-engineering\""
  sources: " - \"Google SRE Book (sre.google/sre-book)\" - \"Seeking SRE — O'Reilly\" - \"Building Secure and Reliable Systems — Google\" - \"Chaos Engineering — O'Reilly (Rosenthal et al.)\""
  version: "\"1.0\""
  cross_domain: "''"
---

# God-Level SRE & Reliability Engineering

## Researcher-Warrior Mindset

The SRE does not accept "it works on my machine" or "the vendor is looking into it." Every failure is a hypothesis to be tested, every alert is evidence to be analyzed, every postmortem is a paper to be published. You dig until you hit bedrock, and then you dig more. Systems fail in exactly the ways you did not test — so test everything, assume nothing, and treat production as a continuous experiment with humans as the subjects.

---

## Anti-Hallucination Rules

**NEVER fabricate:**
- SLO percentages and their downtime equivalents — calculate them explicitly
- Burn rate multipliers — derive them from the error budget math
- Tool CLI flags (k6, Locust, chaos tools) — cite official docs
- Incident severity definitions — every organization defines them differently; never assume
- PagerDuty/OpsGenie API field names — check current API docs
- Chaos engineering tool names: "Chaos Monkey" targets Netflix ASGs (Spinnaker-integrated), "Chaos Toolkit" is the CNCF-adjacent OSS tool, "Litmus" is CNCF, "Gremlin" is commercial — do not conflate them

**ALWAYS verify:**
- Google SRE Book chapter references before citing page numbers
- Prometheus alerting rule syntax against current Prometheus docs (not 1.x docs)
- k6 metric names (http_req_duration, http_req_failed) against k6 docs
- Error budget math with explicit calculation, not memory

---

## 1. SLI/SLO/SLA Framework

### Service Level Indicators (SLIs)

An SLI is a quantitative measure of some aspect of the service. It is a ratio: the number of good events divided by the total number of events, expressed as a percentage or proportion.

**SLI Types and Measurement Approaches:**

**Availability SLI**
```
Availability = (successful_requests / total_requests) × 100

Where "successful" means: HTTP status < 500, or gRPC status OK, 
or whatever the service contract defines as success.

Measurement: Count 5xx responses at the load balancer level (most accurate),
             not the application level (misses crashes before response).
```

**Latency SLI**
```
Latency SLI = (requests_served_within_threshold / total_requests) × 100

Example threshold: 300ms at p99.
Use histograms to measure, NOT averages — averages hide tail latency.
Prometheus: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

Two-tier latency: measure both p50 (median experience) and p99 (tail experience).
p99 latency is what your worst 1% of users experience.
```

**Throughput SLI**
```
Throughput SLI = actual_rps / target_rps × 100

Measure: rate(http_requests_total[1m]) in Prometheus.
Alert when dropping below agreed capacity — distinct from latency degradation.
```

**Error Rate SLI**
```
Error Rate = (failed_requests / total_requests) × 100
Error Rate SLI = 100 - Error Rate (inverted for SLO compliance)

Classify errors: client errors (4xx) are NOT your errors unless you caused them.
Server errors (5xx) and timeouts ARE your errors.
```

**Saturation SLI**
```
Saturation = max(cpu_utilization, memory_utilization, disk_utilization, 
                  connection_pool_utilization, queue_depth_fraction)

No single metric captures saturation. Define per-resource thresholds.
Prometheus: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

### SLO Math — Verified Calculations

```
SLO        | Downtime/Month  | Downtime/Year   | Error Budget (30-day)
-----------|-----------------|-----------------|----------------------
99.0%      | 7h 18m 17s      | 3d 15h 39m 29s  | 43,200 seconds / month
99.5%      | 3h 39m 8s       | 1d 19h 49m 44s  | 21,600 seconds / month
99.9%      | 43m 49s         | 8h 45m 57s      | 2,592 seconds / month
99.95%     | 21m 54s         | 4h 22m 58s      | 1,296 seconds / month
99.99%     | 4m 22s          | 52m 35s         | 259.2 seconds / month
99.999%    | 26s             | 5m 15s          | 25.9 seconds / month

Calculation: downtime = (1 - SLO_decimal) × seconds_in_period
30-day month = 2,592,000 seconds
```

**Error Budget Calculation:**
```
error_budget_seconds = (1 - slo) × 2592000
error_budget_consumed = unavailable_seconds / error_budget_seconds × 100

Example: 99.9% SLO, 600 seconds of downtime in the month:
  budget = 0.001 × 2592000 = 2592 seconds
  consumed = 600 / 2592 = 23.1%
  remaining = 76.9%
```

**Error Budget Policy (what happens when budget is exhausted):**
1. **>50% consumed in first week**: Alert on burn rate, investigate lead causes
2. **>75% consumed**: Mandatory reliability review, hold on new feature deployments
3. **100% consumed (budget exhausted)**: Feature freeze enforced by SRE team, reliability sprint activated, all engineering effort redirected to reliability until SLO is restored over rolling window
4. **Policy must be documented and signed by product + engineering leadership** — without teeth it is theater

---

## 2. Alerting on Burn Rate (Not Thresholds)

Alerting on raw thresholds (e.g., "error rate > 1%") fails because:
- A brief spike that doesn't consume significant budget pages you
- A slow sustained burn that depletes the budget goes undetected

**Burn Rate Model (from Google SRE Workbook Chapter 5):**

```
burn_rate = error_rate / (1 - SLO)

At burn_rate = 1: consuming budget at exactly the rate it replenishes
At burn_rate = 14.4: will exhaust 30-day budget in 2 hours (the "fast burn")
At burn_rate = 1: will exhaust budget in exactly 30 days
```

**Multi-Window Multi-Burn-Rate Alerting:**

```yaml
# Prometheus alerting rules — verified syntax for Prometheus 2.x
groups:
  - name: slo_burn_rate
    rules:
      # Fast burn: 2% budget in 1 hour = burn rate 14.4
      - alert: HighErrorBudgetBurn
        expr: |
          (
            job:slo_errors:ratio_rate1h{job="my-service"} > (14.4 * 0.001)
          )
          and
          (
            job:slo_errors:ratio_rate5m{job="my-service"} > (14.4 * 0.001)
          )
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error budget burn rate (page immediately)"

      # Slow burn: 5% budget in 6 hours = burn rate 2.4
      - alert: MediumErrorBudgetBurn
        expr: |
          (
            job:slo_errors:ratio_rate6h{job="my-service"} > (2.4 * 0.001)
          )
          and
          (
            job:slo_errors:ratio_rate30m{job="my-service"} > (2.4 * 0.001)
          )
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Elevated error budget burn (ticket, next business day)"
```

The two-window approach prevents alert flapping: the long window detects sustained burn, the short window confirms it is still happening.

---

## 3. Incident Command Structure

**IC (Incident Commander):** Coordinates the response. Does NOT do technical work during the incident. Manages communication cadence, declares severity, calls for escalation.

**Comms Lead (Communications Lead):** Owns external and internal communication. Updates status page. Sends stakeholder notifications at defined intervals (every 30 min for P1). Shields the technical team from distraction.

**Tech Lead (Operations Lead):** Directs technical investigation and remediation. Coordinates SMEs. Owns the timeline log. Delegates investigation threads.

**Scribe:** Documents everything in real-time — who said what, what was tried, what was found, exact timestamps.

**War Room Protocol:**
1. Dedicated bridge/channel immediately — all incident comms move there
2. IC announces themselves within 5 minutes of P1 declaration
3. Status page updated within 10 minutes
4. No "drive-by suggestions" — all actions approved by Tech Lead
5. "Mitigated" ≠ "resolved" — declare mitigation separately from full resolution
6. **5-minute update rule**: if nothing has changed, say so on the bridge anyway

**Severity Definitions (customize per org, but document explicitly):**
```
P1/SEV1: Customer-facing, complete outage or data loss, revenue impact
P2/SEV2: Degraded service, partial outage, significant customer impact
P3/SEV3: Partial degradation, workaround available, minor customer impact
P4/SEV4: No customer impact, internal degradation, monitor
```

---

## 4. Postmortem Template

```markdown
## Incident Postmortem: [Service] [Date] [Duration]

### Summary
One paragraph. What happened, how long, what was the impact. 
Write this last, even though it appears first.

### Impact
- User-facing: X% of users affected, Y requests failed
- Revenue: $Z estimated impact (if calculable)
- Data integrity: [none / describe if applicable]
- Duration: HH:MM from first alert to full resolution

### Timeline (all times UTC)
| Time     | Event                                         | Actor       |
|----------|-----------------------------------------------|-------------|
| 14:02:00 | Monitoring detected elevated error rate       | PagerDuty   |
| 14:04:30 | On-call engineer paged                        | Automated   |
| 14:07:00 | Engineer acknowledged, began investigation    | [Name]      |
| 14:09:00 | Identified DB connection pool exhaustion      | [Name]      |
| 14:18:00 | Mitigated: connection pool limit increased    | [Name]      |
| 14:45:00 | Full resolution confirmed                     | [Name]      |

### Root Cause(s) — Always Plural in Complex Systems
1. Primary: Connection pool limit (20) too low for traffic at 14:00 UTC peak
2. Contributing: Recent ORM change introduced N+1 query pattern, tripling connections
3. Contributing: No alerting on connection pool saturation existed
4. Latent: Capacity planning did not account for Thursday traffic patterns

### What Went Well
- Detection was fast (2 minutes from failure to alert)
- Mitigation did not require a deployment
- Team communication was clear

### What Went Wrong
- No runbook for connection pool exhaustion
- Pool saturation metric not monitored
- N+1 query introduced without performance review

### Action Items
| Item                                     | Owner   | Due Date   | Priority |
|------------------------------------------|---------|------------|----------|
| Add connection pool saturation alert     | [Name]  | 2024-02-01 | P1       |
| Fix N+1 query pattern in ORM layer       | [Name]  | 2024-02-07 | P1       |
| Create runbook: DB connection exhaustion | [Name]  | 2024-02-07 | P2       |
| Add DB load to capacity planning model   | [Name]  | 2024-02-14 | P2       |
```

---

## 5. Blameless Culture

**The fundamental principle:** Systems fail, not people. When a human made a decision that contributed to an incident, the question is not "why did they do that?" but "what made that decision seem reasonable at the time?"

**5 Whys Applied to Systems:**
```
Incident: Production database went down during a migration

Why 1: Migration script dropped a table in use
Why 2: Script did not have a dry-run mode; it ran destructively in prod
Why 3: The deployment process allowed migration scripts to run without review
Why 4: No policy existed requiring DBA review for schema changes
Why 5: The team grew from 3 to 30 engineers but deployment policies were never updated

Root cause: Organizational process failed to scale with team size.
Action: Require DBA or senior engineer review for all schema migrations.
```

**James Reason's Swiss Cheese Model:**
No single layer of defense is perfect (each slice has holes). Incidents occur when holes align — multiple defenses fail simultaneously. The SRE task is to add more slices and reduce hole sizes, not to blame the person standing at the last layer.

---

## 6. Chaos Engineering

**Hypothesis-driven chaos:** Never run chaos without a hypothesis.
```
Hypothesis format:
"We believe that [system] will [behavior] when [condition], 
 because [mechanism], and we will verify this by [measurement]."

Example:
"We believe that our API gateway will continue serving traffic 
 when the primary database replica fails, because we have read 
 replicas with automatic failover, and we will verify by measuring 
 error rate remaining below 0.1% during the experiment."
```

**Blast Radius Control:**
1. Start in staging, not production
2. Scope to one service, one AZ, one percentage of traffic
3. Have an abort condition defined before you start
4. Have a kill switch that immediately stops the experiment
5. Run during business hours when team is available (not at 2am)
6. Inform stakeholders before GameDay

**Tool Comparison (verified):**
- **Chaos Monkey**: Netflix OSS, targets AWS Auto Scaling Groups, terminates EC2 instances. Integrated with Spinnaker. Does one thing: random instance termination.
- **Chaos Toolkit** (`chaostoolkit.org`): OSS, extensible via Python drivers, supports GCP/AWS/K8s/Prometheus. YAML-based experiments.
- **Litmus** (`litmuschaos.io`): CNCF project, Kubernetes-native ChaosExperiment CRDs, LitmusChaos Hub with pre-built experiments.
- **Gremlin**: Commercial SaaS, widest attack surface (CPU, memory, network, disk, process, state, security), teams/reporting built in.
- **AWS Fault Injection Service (FIS)**: Native AWS, IAM-controlled, experiment templates, stop conditions via CloudWatch alarms.

**GameDay Format:**
```
1. Pre-GameDay (1 week before):
   - Define hypotheses for each experiment
   - Agree on blast radius and abort conditions
   - Verify monitoring coverage for affected systems
   - Brief all teams involved

2. GameDay Execution:
   - Assign IC, observer, and experiment runner roles
   - Start with lowest-blast-radius experiments
   - Record all measurements in real-time
   - Call abort immediately if unexpected behavior observed

3. Post-GameDay:
   - Document: what broke that shouldn't have, what held that we expected to break
   - File action items for every unexpected finding
   - Schedule follow-up GameDay to verify fixes
```

---

## 7. Toil Elimination

**Google's exact definition of toil** (from SRE Book, Chapter 5):
> "Toil is the kind of work tied to running a production service that tends to be manual, repetitive, automatable, tactical, devoid of enduring value, and that scales linearly as a service grows."

The six properties of toil: manual, repetitive, automatable, tactical (reactive, not proactive), no enduring value, O(n) growth with service scale.

**Toil Identification Exercise:**
For each on-call task performed in the last month, score it:
- Manual (vs automated): +1
- Repetitive (done >3 times): +1  
- Automatable (clear rules exist): +1
- Reactive (not proactive engineering): +1
- No lasting value (not improving the system): +1

Score 4-5: High toil, automate immediately. Score 2-3: Medium toil, plan automation. Score 0-1: Acceptable overhead.

**Toil Elimination Strategies:**
1. **Runbook → Script → Service**: Manual runbook → automated script → self-healing service
2. **Alert → Auto-remediation**: For known-cause alerts, build auto-remediation before accepting the alert as permanent
3. **Ticket-driven work → API-driven self-service**: Reduce human-in-the-loop for provisioning
4. **SRE toil budget**: Google recommends <50% of SRE time on toil; track and enforce

---

## 8. Load Testing

### k6 Script Example
```javascript
// k6 — https://k6.io/docs/ — verified API as of k6 v0.47+
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '2m', target: 100 },   // ramp up to 100 VUs
    { duration: '5m', target: 100 },   // hold at 100 VUs
    { duration: '2m', target: 200 },   // ramp up to 200 VUs
    { duration: '5m', target: 200 },   // hold at 200 VUs
    { duration: '2m', target: 0 },     // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(99)<500'],  // 99th percentile under 500ms
    errors: ['rate<0.01'],             // error rate under 1%
    http_req_failed: ['rate<0.01'],    // k6 built-in failure rate
  },
};

export default function () {
  const res = http.get('https://api.example.com/v1/resource');
  
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  errorRate.add(!success);
  sleep(1);
}
```

**Key k6 metrics to watch:**
- `http_req_duration`: latency distribution (p50, p90, p95, p99)
- `http_req_failed`: rate of failed requests (non-2xx or network error)
- `http_reqs`: total request count and rate
- `vus`: active virtual users
- `iteration_duration`: total iteration time including sleep

### Locust Example
```python
# Locust — https://locust.io/ — verified API for Locust 2.x
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)  # wait 1-3 seconds between tasks
    
    @task(3)  # weight: called 3x more often than weight-1 tasks
    def get_resource(self):
        with self.client.get(
            "/v1/resource",
            catch_response=True,
            name="/v1/resource [GET]"  # groups similar URLs in stats
        ) as response:
            if response.elapsed.total_seconds() > 0.5:
                response.failure(f"Too slow: {response.elapsed.total_seconds()}s")
            elif response.status_code != 200:
                response.failure(f"Got status {response.status_code}")
    
    @task(1)
    def post_resource(self):
        self.client.post(
            "/v1/resource",
            json={"key": "value"},
            headers={"Content-Type": "application/json"}
        )
```

**Interpreting load test results — what to look for:**
1. **The knee of the curve**: Latency remains flat, then suddenly explodes. The VU count before that explosion is your safe operating capacity.
2. **Error rate inflection**: When does error rate leave zero? That is your saturation point.
3. **Throughput ceiling**: RPS stops increasing despite VU increase — you've hit a resource bottleneck (identify which: CPU, connections, downstream service).
4. **Memory growth under load**: Heap growth that doesn't plateau signals a memory leak exacerbated by concurrency.
5. **p99 vs p50 divergence**: If p99 grows much faster than p50, you have tail latency variance (GC pauses, lock contention, cold starts).

---

## 9. Reliability Patterns

### Circuit Breaker
The circuit breaker prevents cascade failures by stopping calls to a failing dependency.

```
States:
  CLOSED (normal): calls pass through, failures counted
  OPEN (tripped): calls immediately rejected, no downstream call made
  HALF-OPEN (recovering): limited calls allowed to test if service recovered

Transition rules:
  CLOSED → OPEN: failure_count > threshold in time_window
  OPEN → HALF-OPEN: after reset_timeout expires
  HALF-OPEN → CLOSED: probe calls succeed
  HALF-OPEN → OPEN: probe calls fail
```

**Implementations:**
- **Resilience4j** (Java): `CircuitBreaker` annotation or programmatic API, integrates with Micrometer for metrics. Correct import: `io.github.resilience4j:resilience4j-circuitbreaker`.
- **Polly** (.NET): `Policy.Handle<HttpRequestException>().CircuitBreaker()`
- **Hystrix** (Java, Netflix OSS): deprecated, use Resilience4j instead — Hystrix entered maintenance mode in 2018.
- **go-resilience**: For Go, `github.com/eapache/go-resiliency/breaker`

### Bulkhead
Isolate resources per consumer to prevent one tenant/use-case from exhausting shared resources.
```
Thread pool bulkhead: separate thread pools per downstream service
Semaphore bulkhead: limit concurrent calls without separate thread pools
Connection pool bulkhead: separate DB connection pools per service tier
```

### Retry with Jitter
```
Naive retry (wrong): wait(base_delay * attempt_number)
Exponential backoff (better): wait(base_delay * 2^attempt)
Exponential backoff with jitter (correct):
  wait = min(cap, base_delay * 2^attempt) * random(0, 1)

Why jitter: Without it, all retrying clients synchronize, creating 
retry storms that worsen the outage they're trying to recover from.
```

### Timeout Hierarchy
```
Client HTTP timeout > Server request timeout > DB query timeout > External API timeout

Verify all timeouts are set (default = infinite = dangerous):
  HTTP client: connect timeout AND read timeout (separate!)
  Database: statement_timeout in PostgreSQL, connectTimeout in JDBC
  Cache: Redis: socket_timeout, connection_timeout
  Message queue: consumer poll timeout, session timeout
```

---

## 10. Capacity Planning

**Lead time for capacity:** Cloud (AWS/GCP/Azure) — minutes to hours for most resources. Bare metal — weeks to months. Plan capacity to account for provisioning lead time plus headroom.

**Growth models:**
```python
def project_capacity(current_load, growth_rate_monthly, months_ahead):
    """
    growth_rate_monthly: decimal, e.g. 0.15 for 15% month-over-month
    """
    return current_load * ((1 + growth_rate_monthly) ** months_ahead)

# Example: 1000 RPS today, 15% MoM growth, plan 6 months out
future_load = project_capacity(1000, 0.15, 6)  # ≈ 2313 RPS

# Add headroom factor (typically 30-50% above projected peak):
capacity_needed = future_load * 1.4  # 40% headroom
```

**Headroom calculation:**
- Compute: 30-40% headroom above projected peak
- Storage: 30% headroom — storage fills linearly, deletion is hard
- Database connections: 20% headroom — connection exhaustion is catastrophic
- Network: 50% headroom — burst traffic can be 2-3x average

**Capacity planning inputs:**
1. Historical growth rate (last 3 months, 6 months, 1 year — use shortest for safety)
2. Upcoming planned events (product launches, marketing campaigns)
3. Seasonal patterns (holiday traffic, fiscal year end)
4. Efficiency improvements (pending optimizations that will reduce load)

---

## 11. Runbook Format

```markdown
## Runbook: [Alert Name] — [Service Name]

### Condition
Alert: `[AlertName]` fires when `[PromQL expression]` is true for `[duration]`.
Severity: [P1/P2/P3]
Typical time to trigger: [e.g., "during traffic spikes" or "after deployments"]

### Immediate Assessment (first 5 minutes)
1. Check the Grafana dashboard: [link to specific dashboard + panel]
2. Verify it is not a monitoring issue: `curl -I https://[service-health-endpoint]`
3. Check for recent deployments: [link to deployment log / CD system]
4. Check downstream dependencies: [link to dependency health dashboard]

### Diagnosis Steps
Step 1: Quantify impact
  - How many users affected? [query/dashboard link]
  - What percentage of requests failing? [query]
  - Is it getting better or worse? [trend query]

Step 2: Isolate the component
  - Check application logs: [log query in Kibana/Loki]
  - Check database: [specific metrics to look at]
  - Check upstream load balancer: [metrics]

### Remediation Actions
Action A (if DB connection pool exhaustion):
  1. Check current pool usage: `SELECT count(*) FROM pg_stat_activity;`
  2. Kill idle connections: [safe SQL command]
  3. Increase pool limit temporarily: [config change + restart command]
  4. File ticket for permanent fix: [link to template]

Action B (if memory pressure):
  1. Identify top memory consumers: `kubectl top pods -n [namespace]`
  2. Rolling restart if leak suspected: `kubectl rollout restart deployment/[name]`

### Escalation Path
- 5 minutes without progress: page [secondary on-call]
- 15 minutes without mitigation: engage [service owner]
- P1 with no mitigation in 30 minutes: engage IC + Comms Lead

### Rollback Procedure
1. Identify last known good deployment: [command]
2. Initiate rollback: [exact command]
3. Verify rollback completed: [health check command]
4. Confirm with monitoring: [dashboard link]
```

---

## 12. On-Call Excellence

**The three tests for a page-worthy alert:**
1. **Urgent**: Requires action within minutes, not hours
2. **Actionable**: The on-call engineer can take a specific action to mitigate
3. **Novel**: Not firing constantly; if it fires 10x/week it has stopped being an alert and started being noise

**Reducing alert fatigue:**
- Every alert that fires must have a runbook entry — if no runbook, the alert is not ready
- Track alert disposition: ACK'd and fixed, ACK'd and no action, silenced — silenced alerts are candidates for deletion
- Monthly alert review: remove alerts that fired zero times, tune thresholds on chronic false positives
- Combine related alerts: "DB is slow AND DB connections are high AND API latency is high" should be one incident, not three pages

**Handoff protocol:**
```
On-call handoff checklist:
□ Any ongoing incidents or known degradation?
□ Any alerts that fired but were determined noise (do not wake up next person)?
□ Any planned changes in next shift that will affect services?
□ Any services in a fragile state requiring extra monitoring?
□ Error budget status for key services?
□ Anything weird that you noticed but couldn't fully investigate?
```

---

## Cross-Domain Connections

**SRE ↔ Observability:** SLI measurement requires correct instrumentation. You cannot alert on burn rate if your metrics are wrong. The observability skill defines how to build the metrics the SRE skill consumes.

**SRE ↔ Database:** Database performance is frequently the root cause of reliability incidents. Connection pool exhaustion, slow queries under load, replication lag — all show up as SLO violations. SREs must be able to read `EXPLAIN ANALYZE` and query `pg_stat_activity`.

**SRE ↔ Data Engineering:** Data pipelines have their own SLOs (freshness, completeness, accuracy). A data pipeline failure is a production incident. SRE concepts (error budgets, runbooks, on-call) apply to data platform teams.

**SRE ↔ Security:** Chaos engineering shares methodology with adversarial security testing. Fault injection is cousin to penetration testing. "Building Secure and Reliable Systems" (Google, 2020) treats security and reliability as inseparable.

---

## Self-Review Checklist

Before declaring any reliability work complete, verify all 20 items:

```
SLI/SLO Design
□ 1. SLI is measured at the right point (user-facing, not internal)
□ 2. SLO has been agreed upon by product AND engineering AND business
□ 3. Error budget policy is written down and has organizational teeth
□ 4. SLO window defined (rolling 30-day, calendar month, etc.)
□ 5. Latency SLI uses histogram percentiles, not averages

Alerting
□ 6. Alerts are on burn rate, not raw thresholds
□ 7. Multi-window alerting implemented (both fast and slow burn)
□ 8. Every alert has a corresponding runbook
□ 9. Alert fatigue is tracked monthly with action to reduce
□ 10. On-call handoff process exists and is followed

Incidents & Postmortems
□ 11. Incident severity definitions are documented and agreed
□ 12. IC, Comms, Tech Lead roles are defined and trained
□ 13. Postmortem is completed within 48-72 hours of resolution
□ 14. Postmortem action items have owners and due dates
□ 15. Blameless culture enforced — postmortem reviews on systems, not people

Reliability Engineering
□ 16. Chaos experiments follow hypothesis-driven format
□ 17. All chaos experiments have abort conditions defined
□ 18. Circuit breakers configured on all external dependency calls
□ 19. All HTTP clients have explicit connect AND read timeouts
□ 20. Capacity plan extends 6 months out with headroom calculated
```
