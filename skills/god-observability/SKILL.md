---
name: god-observability
description: "God-level observability skill covering the three pillars (metrics, logs, traces), OpenTelemetry (OTel) instrumentation, Prometheus (PromQL, scrape config, alerting rules, recording rules), Grafana (dashboard design, alerting, data sources), ELK Stack (Elasticsearch, Logstash, Kibana), OpenSearch, Splunk, Jaeger, Zipkin, Tempo, Loki, structured logging, distributed tracing context propagation, alerting design (SLO-based, symptom-based), cardinality management, and the shift from monitoring to observability. A DevOps engineer who cannot read logs, query metrics, and trace requests is flying blind. A platform engineer who builds observability wrong creates more noise than signal."
metadata:
  domain: "\"observability\""
  sources: " - \"Observability Engineering — Majors, Fong-Jones, Miranda (O'Reilly, 2022)\" - \"Prometheus docs — prometheus.io/docs\" - \"OpenTelemetry docs — opentelemetry.io/docs\" - \"Grafana docs — grafana.com/docs\" - \"Elastic (ELK) docs — elastic.co/guide\" - \"OpenSearch docs — opensearch.org/docs\""
  version: "\"1.0\""
  cross_domain: "''"
---

# God-Level Observability Engineering

## Researcher-Warrior Mindset

You do not accept "the logs don't show anything." That means you instrumented incorrectly. You do not accept "we can't reproduce it in staging." That means your staging environment is not observable enough to tell you why. You instrument everything you care about, you structure every log so a machine can parse it, you propagate trace context across every boundary, and you treat cardinality as a first-class engineering concern. The observable system reveals its failures before the users notice them.

---

## Anti-Hallucination Rules

**NEVER fabricate:**
- Prometheus metric names — verify exact spelling (e.g., `node_memory_MemAvailable_bytes` not `node_memory_available`)
- PromQL function signatures — `rate()` requires a range vector, `histogram_quantile()` takes (φ, vector)
- OpenTelemetry SDK package names — they differ per language and version; cite docs
- ELK version-specific features — Elasticsearch APIs changed significantly between 6.x, 7.x, 8.x
- Logstash filter plugin names — `grok`, `mutate`, `date`, `json` are real; invented names are not
- W3C Trace Context header names — `traceparent` and `tracestate` are the standard, not `x-trace-id`
- Splunk SPL syntax — verify against Splunk Search Reference docs
- Grafana alert provisioning YAML schema — verify field names against current Grafana docs (8.x vs 9.x vs 10.x differ)

**ALWAYS verify:**
- PromQL expressions produce the intended result — check units (counters need `rate()`, not raw value)
- OpenTelemetry semantic conventions attribute names (use `semconv` spec, e.g., `http.request.method` in OTel 1.21+)
- Jaeger vs Zipkin vs Tempo differences — they are not interchangeable
- Loki LogQL vs PromQL — different query languages, different functions

---

## 1. Monitoring vs Observability

**Monitoring:** You decide in advance what metrics to collect and what thresholds to alert on. Works for known failure modes. Fails for unknown unknowns. You can tell something is wrong (the metric crossed a threshold), but you cannot explore why without additional data.

**Observability:** The system's internal state can be inferred from its external outputs. You can ask arbitrary questions about behavior without predicting in advance what questions you will need to ask. Comes from control theory (Kalman, 1960) — a system is "observable" if you can determine its internal state from its outputs.

**Practical distinction:**
```
Monitoring tells you: "HTTP error rate is 15%"
Observability lets you ask: "Which specific user IDs are failing, 
  from which geographic region, hitting which backend service, 
  after which deployment, correlating with which database query?"

You need BOTH: monitoring for known failure modes (SLO alerting), 
observability for investigating unknown failures.
```

---

## 2. The Three Pillars

### Metrics
- **Nature:** Aggregated, numerical, time-series
- **Cardinality:** Low — metrics are pre-aggregated. High-cardinality dimensions (user_id, request_id) do not belong in metric labels.
- **Strengths:** Efficient storage, fast queries, natural for alerting and dashboards
- **Weaknesses:** Aggregation loses detail. You know p99 latency is 2s, but not *which* requests are slow.

### Logs
- **Nature:** Discrete events, timestamped, unstructured or structured text
- **Cardinality:** High — logs can contain unique values per request
- **Strengths:** Full context per event, human-readable, supports ad-hoc investigation
- **Weaknesses:** Volume (expensive to store), unstructured logs are hard to query, no native correlation

### Traces
- **Nature:** Request flow across services, parent-child span relationships
- **Cardinality:** Very high — one trace per request
- **Strengths:** Shows the full journey of a request, latency breakdown per component
- **Weaknesses:** Sampling required at scale, instrumentation cost, context propagation across every boundary

**The fourth pillar: Events (Honeycomb's model)**
Wide events (structured, high-cardinality per-request records) as a superset of logs — they carry the richness of logs with the queryability of metrics.

---

## 3. OpenTelemetry (OTel)

OpenTelemetry is the CNCF standard for vendor-neutral instrumentation. It unifies metrics, logs, and traces under one SDK and wire protocol (OTLP — OpenTelemetry Protocol).

**Architecture:**
```
Application Code → OTel SDK → OTel Collector → Backend (Prometheus, Jaeger, Loki, etc.)
                                     ↑
                              (optional but recommended)
                              buffers, retries, fan-out, 
                              tail-based sampling, transforms
```

### SDK Instrumentation Examples

**Go (verified against opentelemetry-go v1.x):**
```go
import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/trace"
)

tracer := otel.Tracer("my-service")

func HandleRequest(ctx context.Context, req *http.Request) {
    ctx, span := tracer.Start(ctx, "HandleRequest",
        trace.WithAttributes(
            attribute.String("http.request.method", req.Method),
            attribute.String("url.path", req.URL.Path),
        ),
    )
    defer span.End()

    // Propagate context to downstream calls
    result, err := downstreamCall(ctx)
    if err != nil {
        span.RecordError(err)
        span.SetStatus(codes.Error, err.Error())
    }
}
```

**Python (verified against opentelemetry-sdk ≥ 1.0):**
```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
exporter = OTLPSpanExporter(endpoint="http://collector:4317")
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("my-service")

with tracer.start_as_current_span("process_request") as span:
    span.set_attribute("user.id", user_id)
    span.set_attribute("db.system", "postgresql")
    result = process(user_id)
```

**Java (verified against opentelemetry-java 1.x, OpenTelemetry BOM):**
```java
// Via auto-instrumentation agent (recommended): 
// java -javaagent:opentelemetry-javaagent.jar -jar app.jar
// Agent instruments common libraries (JDBC, HTTP clients, Spring) automatically

// Manual instrumentation:
import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.Tracer;

Tracer tracer = GlobalOpenTelemetry.getTracer("my-service");
Span span = tracer.spanBuilder("my-operation")
    .setAttribute("db.system", "postgresql")
    .startSpan();
try (Scope scope = span.makeCurrent()) {
    // work here
} finally {
    span.end();
}
```

**Node.js (verified against @opentelemetry/sdk-node):**
```javascript
// tracing.js — load before app starts
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-grpc');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({ url: 'http://collector:4317' }),
  instrumentations: [getNodeAutoInstrumentations()],
});
sdk.start();
```

### OTel Collector Config
```yaml
# otel-collector-config.yaml — verified against collector v0.90+
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: "0.0.0.0:4317"
      http:
        endpoint: "0.0.0.0:4318"

processors:
  batch:
    timeout: 10s
    send_batch_size: 1024
  memory_limiter:
    limit_mib: 512
    spike_limit_mib: 128
    check_interval: 5s

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
  otlp/jaeger:
    endpoint: "jaeger:4317"
    tls:
      insecure: true
  loki:
    endpoint: "http://loki:3100/loki/api/v1/push"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/jaeger]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [loki]
```

---

## 4. Prometheus

### Metric Types — Differences Matter

**Counter:** Monotonically increasing. Resets to 0 on restart. NEVER query raw counters — always use `rate()` or `increase()`.
```promql
# Wrong: raw counter value is meaningless
http_requests_total

# Right: per-second rate over 5 minutes
rate(http_requests_total[5m])

# Right: total increase over 1 hour
increase(http_requests_total[1h])
```

**Gauge:** Can go up or down. Represents current state (queue depth, memory usage, active connections). Query directly.
```promql
process_resident_memory_bytes
go_goroutines
redis_connected_clients
```

**Histogram:** Client-side bucketing of observations. Exports `_bucket`, `_count`, `_sum` series. Used for latency. Supports `histogram_quantile()`.
```promql
# p99 latency over 5 minutes — note: histogram_quantile(φ, range_vector)
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# p50 and p99 side by side
histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

**Summary:** Client-side quantile calculation. Exports pre-computed quantiles. Cannot be aggregated across instances — this is its critical limitation. Use histograms for aggregatable quantiles.

### Scrape Config
```yaml
# prometheus.yml — verified format for Prometheus 2.x
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'my-service'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scheme: http
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance

  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: 'true'
```

### PromQL Examples
```promql
# Rate of HTTP errors (5xx)
rate(http_requests_total{status=~"5.."}[5m])

# Error ratio (fraction of requests that failed)
rate(http_requests_total{status=~"5.."}[5m]) 
  / rate(http_requests_total[5m])

# irate: instantaneous rate — use for fast-moving counters, noisy
irate(http_requests_total[5m])

# CPU usage per core
100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory available
node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100

# 99th percentile with aggregation across instances
histogram_quantile(0.99, 
  sum by (le, job) (rate(http_request_duration_seconds_bucket[5m])))
```

### Recording Rules (for performance)
```yaml
# Pre-compute expensive queries — evaluated at scrape interval
# Store as new time series — much faster dashboard loading
groups:
  - name: http_slo_rules
    interval: 30s
    rules:
      - record: job:http_requests:rate5m
        expr: sum by (job, status) (rate(http_requests_total[5m]))
      
      - record: job:http_errors:ratio_rate5m
        expr: |
          sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))
          / sum by (job) (rate(http_requests_total[5m]))
      
      - record: job:http_request_duration_seconds:p99_rate5m
        expr: |
          histogram_quantile(0.99, 
            sum by (job, le) (rate(http_request_duration_seconds_bucket[5m])))
```

---

## 5. Grafana

### Dashboard Best Practices
1. **USE Method per resource** (Utilization, Saturation, Errors): CPU, memory, disk, network
2. **RED Method per service** (Rate, Errors, Duration): HTTP, gRPC, database queries
3. **First row = health summary**: traffic, error rate, p99 latency — enough to assess health at a glance
4. **Drill-down below the fold**: instance-level, per-endpoint breakdown — details visible on scroll
5. **Consistent time ranges across panels**: link all panels to the dashboard time range variable
6. **Color conventions**: green=good, yellow=warning, red=critical — never invert
7. **Unit annotation**: always set units on axes (bytes, ms, req/s) — unitless graphs cause misreads

### Grafana Loki Integration
```logql
# LogQL — log query language for Loki (different from PromQL)

# Filter by label and search term
{job="my-service", environment="production"} |= "ERROR"

# Parse JSON logs and filter on structured fields
{job="my-service"} | json | level="error" | status_code >= 500

# Metric query: log rate over time
rate({job="my-service"} |= "ERROR" [5m])

# Extract and count field values
{job="my-service"} | json | unwrap duration_ms | quantile_over_time(0.99, [5m])
```

---

## 6. ELK Stack

### Elasticsearch Index Design
```json
// Explicit mapping — never use fully dynamic mapping in production
// Dynamic mapping can cause "mapping explosion" (too many fields → OOM)
PUT /my-service-logs
{
  "mappings": {
    "dynamic": "strict",
    "properties": {
      "timestamp": { "type": "date", "format": "strict_date_time" },
      "level": { "type": "keyword" },
      "service": { "type": "keyword" },
      "message": { "type": "text", "analyzer": "standard" },
      "trace_id": { "type": "keyword", "index": true },
      "span_id": { "type": "keyword", "index": true },
      "user_id": { "type": "keyword" },
      "duration_ms": { "type": "long" },
      "status_code": { "type": "integer" }
    }
  },
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "index.lifecycle.name": "logs-policy"
  }
}
```

**Avoid mapping explosion:** Set `dynamic: strict` or `dynamic: false` in production. Every unique field with `dynamic: true` creates a new mapping entry — 10,000 unique JSON keys = cluster instability.

### Logstash Pipeline Config
```
# Verified Logstash 8.x pipeline syntax
input {
  kafka {
    bootstrap_servers => "kafka:9092"
    topics => ["app-logs"]
    codec => "json"
  }
}

filter {
  # Parse unstructured logs with grok — use sparingly; json filter is faster
  if [message] =~ /^\{/ {
    json {
      source => "message"
      target => "parsed"
    }
  } else {
    grok {
      match => { 
        "message" => "%{TIMESTAMP_ISO8601:timestamp} %{LOGLEVEL:level} %{GREEDYDATA:msg}" 
      }
    }
  }

  # Normalize timestamp
  date {
    match => ["timestamp", "ISO8601"]
    target => "@timestamp"
  }

  # Remove raw message after parsing
  mutate {
    remove_field => ["message", "timestamp"]
    rename => { "[parsed][service]" => "service" }
  }
}

output {
  elasticsearch {
    hosts => ["https://elasticsearch:9200"]
    index => "logs-%{[service]}-%{+YYYY.MM.dd}"
    user => "${ES_USER}"
    password => "${ES_PASSWORD}"
  }
}
```

### Kibana KQL Queries
```
# KQL — Kibana Query Language (not Lucene, simpler syntax)

# Filter by field value
level: "error"

# Wildcard
service: "payment-*"

# Range
duration_ms > 500

# AND/OR
level: "error" AND service: "checkout"

# NOT
NOT status_code: 200

# Phrase match
message: "connection refused"

# Nested: trace_id exact match for distributed trace correlation
trace_id: "4bf92f3577b34da6a3ce929d0e0e4736"
```

---

## 7. OpenSearch

OpenSearch is the open-source fork of Elasticsearch 7.10, created by AWS in 2021 after Elastic changed the license to SSPL. API is largely compatible with Elasticsearch 7.x but diverges for newer features.

**Key differences from Elasticsearch:**
- **ISM (Index State Management)** vs Elasticsearch's **ILM (Index Lifecycle Management)** — different API paths
- OpenSearch Dashboards = Kibana fork
- `_doc` is the only type (same as ES 7.x, both removed multi-type)
- Security plugin included by default in OpenSearch (was X-Pack in Elastic, requiring subscription)

**ISM Policy example (OpenSearch):**
```json
PUT _plugins/_ism/policies/logs-policy
{
  "policy": {
    "description": "Rotate logs daily, delete after 30 days",
    "states": [
      {
        "name": "hot",
        "actions": [{ "rollover": { "min_size": "50gb", "min_index_age": "1d" } }],
        "transitions": [{ "state_name": "warm", "conditions": { "min_index_age": "2d" } }]
      },
      {
        "name": "warm",
        "actions": [{ "force_merge": { "max_num_segments": 1 } }],
        "transitions": [{ "state_name": "delete", "conditions": { "min_index_age": "30d" } }]
      },
      {
        "name": "delete",
        "actions": [{ "delete": {} }],
        "transitions": []
      }
    ]
  }
}
```

---

## 8. Splunk SPL

```spl
# SPL — Search Processing Language

# Basic search with time range
index=prod_logs level=ERROR earliest=-1h latest=now

# Count errors by service
index=prod_logs level=ERROR 
| stats count by service 
| sort -count

# Calculate error rate over time
index=prod_logs 
| timechart span=5m 
    count(eval(level="ERROR")) as errors,
    count as total 
| eval error_rate = errors/total*100

# Top slow requests
index=prod_logs 
| where duration_ms > 1000 
| stats avg(duration_ms) as avg_latency, count by endpoint 
| sort -avg_latency 
| head 20

# Correlate by trace_id
index=prod_logs trace_id="abc123def456"
| sort _time
| table _time, service, level, message, duration_ms
```

---

## 9. Structured Logging

**JSON log format standard:**
```json
{
  "timestamp": "2024-01-15T14:02:33.412Z",
  "level": "error",
  "service": "payment-service",
  "version": "2.4.1",
  "environment": "production",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "user_id": "usr_7a2f9b4c",
  "request_id": "req_c3d4e5f6",
  "message": "Payment processing failed",
  "error": {
    "type": "PaymentGatewayError",
    "code": "INSUFFICIENT_FUNDS",
    "message": "Card declined by issuing bank"
  },
  "http": {
    "method": "POST",
    "url": "/v1/payments",
    "status_code": 402,
    "duration_ms": 234
  }
}
```

**Mandatory fields:** `timestamp` (ISO 8601, UTC), `level`, `service`, `trace_id`, `span_id`, `message`

**What NOT to log (security and compliance):**
- Passwords, API keys, secrets, tokens (mask entirely — not even partial)
- Credit card numbers, CVV, expiry (PCI-DSS violation)
- Social security numbers, national ID numbers (PII — GDPR/CCPA)
- Full request bodies without scrubbing (may contain all of the above)
- Session tokens, JWTs (can be used for session hijacking)
- Encryption keys

**Cross-role impact:** If a backend developer logs `{"user": {"email": "...", "password": "..."}}`, the ops team's log aggregation system now stores plaintext passwords. Log scrubbing at the application level is the developer's responsibility, not the ops team's.

---

## 10. Distributed Tracing

### W3C Trace Context Standard
The standard HTTP headers for trace context propagation (replaces proprietary `X-B3-*`, `X-Datadog-*` headers):

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             ^^                                                        ^^
             version                                                   flags (01 = sampled)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                      
                trace-id (128-bit hex, 32 chars)
                                                 ^^^^^^^^^^^^^^^^
                                                 parent-id/span-id (64-bit hex, 16 chars)

tracestate: vendor1=value1,vendor2=value2
```

**Context propagation across every boundary:**
- HTTP: inject `traceparent` header in outgoing requests, extract from incoming
- gRPC: inject via metadata
- Kafka: inject into record headers (not message body)
- Database: attach `db.statement` attribute to DB spans, correlate via trace_id in logs

### Span Types
```
SpanKind.SERVER  — incoming HTTP/gRPC request handler
SpanKind.CLIENT  — outgoing HTTP/gRPC call, DB query
SpanKind.PRODUCER — publishing to message queue
SpanKind.CONSUMER — consuming from message queue
SpanKind.INTERNAL — internal operation within a service
```

### Sampling Strategies
**Head-based sampling:** Decision made when the trace starts (at the first span). Simple, low overhead. Problem: you cannot decide to sample based on what happened downstream (you don't know yet that there was an error).

**Tail-based sampling:** Decision made after the trace completes. Can sample 100% of error traces and slow traces. Requires the collector to buffer complete traces. OTel Collector supports tail-based sampling via the `tailsampling` processor.

```yaml
# OTel Collector tail-based sampling
processors:
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: errors-policy
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow-traces-policy
        type: latency
        latency: { threshold_ms: 1000 }
      - name: probabilistic-policy
        type: probabilistic
        probabilistic: { sampling_percentage: 10 }
```

---

## 11. Jaeger vs Zipkin vs Tempo

**Jaeger** (CNCF, originally Uber):
- Native OTLP support (as of Jaeger v1.35+)
- Supports Cassandra, Elasticsearch, Badger backends
- UI has dependency graph, flame chart, comparison view
- Use when: you need a full-featured OSS tracing backend with rich UI

**Zipkin** (originally Twitter):
- Older project, B3 propagation format (now supports W3C too)
- Simpler deployment, supports Elasticsearch, MySQL, Cassandra
- Smaller community, less active development
- Use when: you have existing Zipkin infrastructure or B3 propagation constraints

**Grafana Tempo:**
- Designed for cost-efficient trace storage at scale (object storage: S3, GCS, Azure Blob)
- No index — trades query flexibility for storage efficiency (lookup by trace ID only, or via TraceQL)
- Integrates natively with Grafana, Loki (link from log line to trace), Prometheus (exemplars)
- TraceQL: `{span.http.method="POST" && duration>500ms}`
- Use when: you are already in the Grafana ecosystem, need cost-efficient storage

---

## 12. Alerting Design

**Symptom-based alerting (correct):** Alert on what the user experiences.
```
Alert: "p99 latency > 2s for >5 minutes" — users are experiencing slow responses
Alert: "Error rate > 1% for >10 minutes" — users are experiencing failures
```

**Cause-based alerting (use sparingly):** Alert on infrastructure state.
```
Alert: "CPU > 90% for >10 minutes" — may cause issues, but not necessarily
Problem: CPU at 90% may not affect users if it is sustained but stable
Better: alert on CPU AND latency, not CPU alone
```

**Multi-window multi-burn-rate (verified math):**
```
For 99.9% SLO (error budget = 0.1% of requests):

Window | Burn Rate | Budget Consumed | Severity
1h     | 14.4      | 2% of monthly   | Critical (page now)
6h     | 6.0       | 5% of monthly   | Warning (ticket)
1d     | 3.0       | 10% of monthly  | Warning (ticket)
3d     | 1.0       | 10% of monthly  | Info (trend watch)

Combined alert: fire only when BOTH the long window AND short window exceed threshold
(prevents flapping from momentary spikes)
```

---

## 13. Cardinality Management

**Why high cardinality kills Prometheus:**
Prometheus stores one time series per unique label combination. If you add `user_id` as a label on a service with 10 million users, you create 10 million time series for that single metric. Memory consumption grows linearly with cardinality.

**Signs of cardinality problems:**
- Prometheus memory usage growing without explanation
- `prometheus_tsdb_head_series` metric exceeding 10M+ per instance
- Slow TSDB compaction, increased chunk write latency

**What belongs in labels (low cardinality):**
```
environment: production | staging | dev           (3 values)
status_code_class: 2xx | 3xx | 4xx | 5xx         (4 values)
method: GET | POST | PUT | DELETE                 (4 values)
region: us-east-1 | eu-west-1 | ap-southeast-1   (handful)
```

**What does NOT belong in labels (high cardinality):**
```
user_id, request_id, session_id, email, IP address, trace_id
```

**Alternative for high-cardinality correlation: Exemplars**
Prometheus 2.26+ supports exemplars — attach a sample trace_id to histogram observations without creating a new time series. Link from a slow p99 histogram bucket to the specific trace_id in Jaeger.

---

## 14. Log Aggregation Patterns

**Sidecar (Fluent Bit):**
```
Application container → shared volume → Fluent Bit sidecar → Log backend
Pros: log routing per-pod, pod-level configuration
Cons: overhead per pod, more resource consumption
Use when: different pods need different log routing logic
```

**DaemonSet (Fluentd):**
```
All pods → node log files → Fluentd DaemonSet per node → Log backend
Pros: one agent per node, lower overhead
Cons: shared configuration, node-level resources
Use when: uniform log routing, large clusters
```

**Direct push:**
```
Application code → log backend SDK → Log backend
Pros: no infrastructure in the path, low latency
Cons: log backend failure impacts application, tight coupling
Use when: simple setups, serverless functions
```

---

## Cross-Domain Connections

**Observability ↔ SRE:** SLI measurement is an observability problem. You cannot calculate error rate without correct metrics. You cannot investigate why the SLO is breached without traces and logs. The burn rate alert fires — observability tells you why.

**Observability ↔ Databases:** Slow query logs from PostgreSQL (`log_min_duration_statement`) must be structured and shipped to your log backend. Database metrics (connections, lock wait time, replication lag) must be exported via `postgres_exporter` to Prometheus. Trace spans should include `db.statement`, `db.system`, `db.name` attributes per OTel semantic conventions.

**Observability ↔ Data Engineering:** Data pipeline observability is distinct from application observability. Pipeline-specific metrics: rows processed, rows failed, processing lag, checkpoint duration. Airflow has built-in StatsD/OpenTelemetry metric emission. Spark has Prometheus sink. Apply the same structured logging and trace context standards to data pipelines.

**Observability ↔ Security:** Logs are the primary security artifact. SIEM systems (Splunk, Elastic SIEM) consume the same log streams as your ops tooling. Structured logs with consistent fields enable security correlation queries. The field names and formats you choose affect security analysts' ability to detect intrusions.

---

## Self-Review Checklist

```
Metrics
□ 1. Counters are queried with rate() or increase(), never raw
□ 2. Histograms used for latency (not summaries) — aggregatable across instances
□ 3. Label cardinality reviewed — no user_id or request_id in metric labels
□ 4. Recording rules exist for expensive PromQL queries used in dashboards
□ 5. Prometheus scrape targets have explicit timeout and scrape_interval

Logs
□ 6. All logs are structured JSON with mandatory fields (timestamp, level, service, trace_id)
□ 7. No PII, passwords, tokens, or keys logged anywhere
□ 8. Elasticsearch/OpenSearch mapping is explicit (dynamic: strict or false)
□ 9. Log retention policy is defined and enforced via ILM/ISM
□ 10. Log volume estimated and storage capacity planned

Traces
□ 11. W3C traceparent/tracestate headers propagated across all service boundaries
□ 12. Kafka record headers carry trace context (not only HTTP)
□ 13. Database spans include db.statement and db.system attributes
□ 14. Sampling strategy is documented and appropriate for traffic volume
□ 15. Tail-based sampling configured for 100% error and slow trace capture

Alerting & Dashboards
□ 16. Alerts are symptom-based (user impact) not just cause-based (resource usage)
□ 17. Multi-window multi-burn-rate alerting implemented for SLO-backed services
□ 18. Every alert links to a runbook
□ 19. Grafana dashboards follow USE/RED structure with summary row first
□ 20. Alert noise tracked monthly and reduced — no chronic false positives
```
