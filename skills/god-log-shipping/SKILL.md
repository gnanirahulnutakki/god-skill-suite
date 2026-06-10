---
name: god-log-shipping
description: "God-level log shipping and aggregation mastery. Deep dive into Fluentd (Ruby-based, plugin ecosystem, buffer tuning), Fluent Bit (C-based, lightweight, K8s-native), Vector (Rust-based, VRL transforms), log routing architectures (sidecar vs DaemonSet vs direct push), parser configuration (regex, JSON, multiline), filter chains, Kubernetes metadata enrichment, output plugins (Elasticsearch, Loki, S3, Kafka, Splunk HEC), buffer management and backpressure handling, and production reliability patterns. Never fabricate plugin names — verify against official plugin registries."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Log Shipping & Aggregation

## Anti-Hallucination Rules

- NEVER invent Fluentd/Fluent Bit plugin names — verify against the official plugin registry.
- NEVER confuse Fluentd (Ruby, td-agent) with Fluent Bit (C, lightweight) — different config syntax, different plugins.
- NEVER fabricate Vector VRL functions — verify against vector.dev docs.
- ALWAYS specify which agent (Fluentd vs Fluent Bit vs Vector) when discussing config syntax — they are NOT interchangeable.
- ALWAYS note version-specific features — Fluent Bit multiline support changed significantly in v2.0+.

---

## 1. Architecture: When to Use What

```
Fluent Bit (recommended for K8s):
  - Written in C — ~450KB binary, ~1MB RSS memory
  - Low resource footprint — ideal as DaemonSet
  - Native K8s metadata enrichment
  - Supports: tail, forward, OTLP, HTTP inputs
  - Limited plugin ecosystem vs Fluentd
  - Use when: K8s log collection, resource-constrained environments

Fluentd (recommended for aggregation):
  - Written in Ruby — larger footprint (~40MB RSS)
  - Massive plugin ecosystem (900+ plugins)
  - Powerful filter chain for complex transformations
  - Use when: central log aggregator, complex routing, many output targets

Vector (modern alternative):
  - Written in Rust — high performance, type-safe
  - VRL (Vector Remap Language) for transforms
  - Built-in observability (internal metrics)
  - Use when: high throughput, complex transforms, replacing multiple tools
```

### K8s Log Pipeline Pattern

```
Pods → stdout/stderr → /var/log/containers/*.log
    ↓
Fluent Bit DaemonSet (per node)
  → Parse (JSON/regex)
  → Enrich with K8s metadata (namespace, pod, labels)
  → Filter (drop noise, redact PII)
  → Route by namespace/label
    ↓
Fluentd Aggregator (StatefulSet, 2-3 replicas)
  → Buffer (file-backed)
  → Transform
  → Output to multiple backends
    ├── Elasticsearch/OpenSearch (operational logs)
    ├── S3/GCS (archive/compliance)
    ├── Loki (Grafana stack)
    └── Kafka (streaming pipeline)
```

---

## 2. Fluent Bit Configuration

### 2.1 K8s DaemonSet Config

```ini
# fluent-bit.conf — Fluent Bit v2.x+ syntax
[SERVICE]
    Flush         5
    Log_Level     info
    Daemon        Off
    Parsers_File  parsers.conf
    HTTP_Server   On
    HTTP_Listen   0.0.0.0
    HTTP_Port     2020
    storage.path  /var/log/flb-storage/
    storage.sync  normal
    storage.checksum off
    storage.max_chunks_up 128

[INPUT]
    Name              tail
    Tag               kube.*
    Path              /var/log/containers/*.log
    Parser            cri                    # CRI log format (containerd)
    DB                /var/log/flb_kube.db   # Track file positions
    Mem_Buf_Limit     5MB
    Skip_Long_Lines   On
    Refresh_Interval  10
    Read_from_Head    False
    storage.type      filesystem

[FILTER]
    Name                kubernetes
    Match               kube.*
    Kube_URL            https://kubernetes.default.svc:443
    Kube_CA_File        /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
    Kube_Token_File     /var/run/secrets/kubernetes.io/serviceaccount/token
    Merge_Log           On           # Parse JSON log messages
    Merge_Log_Key       log_parsed
    Keep_Log            Off          # Remove raw log field after parsing
    K8S-Logging.Parser  On           # Use pod annotation for parser
    K8S-Logging.Exclude On           # Use pod annotation to exclude
    Labels              On           # Include pod labels
    Annotations         Off

# Drop health check logs (noise reduction)
[FILTER]
    Name    grep
    Match   kube.*
    Exclude log /health|/ready|/live

# Redact sensitive data
[FILTER]
    Name          modify
    Match         kube.*
    Condition     Key_Value_Matches  log  (?i)(password|secret|token|api.?key)
    Set           log   [REDACTED]

[OUTPUT]
    Name            es
    Match           kube.*
    Host            elasticsearch
    Port            9200
    Index           logs-${NAMESPACE}-%Y.%m.%d
    Type            _doc
    Logstash_Format On
    Logstash_Prefix fluent-bit
    Retry_Limit     5
    tls             On
    tls.verify      On
    HTTP_User       ${ES_USER}
    HTTP_Passwd     ${ES_PASSWORD}
    Buffer_Size     512KB
    storage.total_limit_size 5G

[OUTPUT]
    Name            loki
    Match           kube.*
    Host            loki
    Port            3100
    Labels          job=fluent-bit,namespace=$kubernetes['namespace_name'],pod=$kubernetes['pod_name']
    Label_Keys      $kubernetes['labels']['app']
    Remove_Keys     kubernetes,stream
    Line_Format     json
```

### 2.2 Multiline Parser (Stack Traces)

```ini
# parsers.conf
[MULTILINE_PARSER]
    Name          java-stack-trace
    Type          regex
    Flush_timeout 1000
    # First line starts with timestamp or log level
    Rule          "start_state"  "/^\d{4}-\d{2}-\d{2}|^[A-Z]{4,5}\s/"  "cont"
    # Continuation: lines starting with whitespace, "at", "Caused by", "..."
    Rule          "cont"         "/^\s+at\s|^\s+\.\.\.|^Caused by:/"     "cont"

[PARSER]
    Name        cri
    Format      regex
    Regex       ^(?<time>[^ ]+) (?<stream>stdout|stderr) (?<logtag>[^ ]*) (?<log>.*)$
    Time_Key    time
    Time_Format %Y-%m-%dT%H:%M:%S.%L%z

[PARSER]
    Name        json
    Format      json
    Time_Key    timestamp
    Time_Format %Y-%m-%dT%H:%M:%S.%L%z
```

---

## 3. Fluentd Configuration

### 3.1 Aggregator Config

```xml
# fluent.conf — Fluentd v1.x syntax
<system>
  log_level info
  workers 4
</system>

# Receive from Fluent Bit forwarders
<source>
  @type forward
  port 24224
  bind 0.0.0.0
  <transport tls>
    cert_path /etc/fluentd/certs/server.crt
    private_key_path /etc/fluentd/certs/server.key
  </transport>
</source>

# Parse JSON logs
<filter kube.**>
  @type parser
  key_name log
  reserve_data true
  remove_key_name_field true
  <parse>
    @type json
    time_key timestamp
    time_format %Y-%m-%dT%H:%M:%S.%L%z
  </parse>
</filter>

# Add environment tag
<filter kube.**>
  @type record_transformer
  <record>
    environment "#{ENV['ENVIRONMENT']}"
    cluster "#{ENV['CLUSTER_NAME']}"
  </record>
</filter>

# Route by namespace
<match kube.production.**>
  @type copy
  <store>
    @type elasticsearch
    host elasticsearch
    port 9200
    index_name prod-logs
    logstash_format true
    logstash_prefix prod-logs
    include_tag_key true
    <buffer tag, time>
      @type file
      path /var/log/fluentd/buffer/es-prod
      flush_mode interval
      flush_interval 10s
      chunk_limit_size 8MB
      total_limit_size 2GB
      retry_max_interval 30
      retry_forever true
      overflow_action block
    </buffer>
  </store>
  <store>
    @type s3
    s3_bucket logs-archive
    s3_region us-east-1
    path production/
    <buffer tag, time>
      @type file
      path /var/log/fluentd/buffer/s3-prod
      timekey 3600
      timekey_wait 10m
      chunk_limit_size 256MB
    </buffer>
  </store>
</match>
```

### 3.2 Buffer Tuning

```
Buffer parameters (critical for reliability):
  chunk_limit_size:    Max size per chunk (default 8MB for file buffer)
  total_limit_size:    Max total buffer size (prevent disk exhaustion)
  flush_interval:      How often to flush (lower = less data loss risk)
  retry_max_interval:  Max wait between retries
  overflow_action:     What to do when buffer is full:
    throw_exception:   Raise error (drop data)
    block:             Block input (backpressure — recommended)
    drop_oldest_chunk: Drop oldest data to make room
```

---

## 4. Vector Configuration

```yaml
# vector.yaml — Vector 0.34+
sources:
  kubernetes_logs:
    type: kubernetes_logs
    extra_label_selector: "app!=fluent-bit"
    extra_namespace_label_selector: "logging!=disabled"

transforms:
  parse_json:
    type: remap
    inputs: ["kubernetes_logs"]
    source: |
      # VRL (Vector Remap Language) — type-safe transforms
      . = parse_json!(.message) ?? .
      .timestamp = to_timestamp!(.timestamp) ?? now()
      .environment = get_env_var("ENVIRONMENT") ?? "unknown"
      
      # Redact sensitive fields
      if exists(.password) { .password = "***REDACTED***" }
      if exists(.api_key) { .api_key = "***REDACTED***" }
      
      # Drop health check noise
      if starts_with(.path, "/health") ?? false {
        abort
      }

  route_by_level:
    type: route
    inputs: ["parse_json"]
    route:
      errors: '.level == "error" || .level == "fatal"'
      warnings: '.level == "warn"'
      info: '.level == "info" || .level == "debug"'

sinks:
  elasticsearch_errors:
    type: elasticsearch
    inputs: ["route_by_level.errors"]
    endpoints: ["https://elasticsearch:9200"]
    bulk:
      index: "errors-%Y.%m.%d"
    auth:
      strategy: basic
      user: "${ES_USER}"
      password: "${ES_PASSWORD}"

  loki_all:
    type: loki
    inputs: ["parse_json"]
    endpoint: "http://loki:3100"
    labels:
      namespace: "{{ kubernetes.pod_namespace }}"
      pod: "{{ kubernetes.pod_name }}"
      level: "{{ level }}"
    encoding:
      codec: json

  s3_archive:
    type: aws_s3
    inputs: ["parse_json"]
    bucket: "logs-archive"
    region: "us-east-1"
    key_prefix: "{{ kubernetes.pod_namespace }}/%Y/%m/%d/"
    encoding:
      codec: json
    compression: gzip
    batch:
      max_bytes: 10485760
      timeout_secs: 300
```

---

## Cross-Domain Connections

**Log Shipping ↔ Observability:** Fluent Bit/Fluentd are the transport layer. Loki, Elasticsearch, Splunk are the storage/query layer. OTel Collector is increasingly replacing dedicated log shippers with unified telemetry collection.

**Log Shipping ↔ Security:** Log integrity matters for compliance. TLS between forwarders and aggregators. S3 archive with WORM (Write Once Read Many) for audit trails. Sensitive data must be redacted at the source, not after storage.

**Log Shipping ↔ Kubernetes:** K8s metadata enrichment (namespace, pod, labels, annotations) transforms raw container logs into queryable operational data. Without metadata enrichment, logs are nearly useless for debugging.

---

## Self-Review Checklist

- [ ] Fluent Bit Mem_Buf_Limit set to prevent OOM on DaemonSet pods
- [ ] File-backed buffers configured (not memory-only) for crash resilience
- [ ] Buffer overflow_action is `block` (not `throw_exception`) for production
- [ ] K8s metadata enrichment enabled with Merge_Log for JSON parsing
- [ ] Health check and readiness probe logs excluded (noise reduction)
- [ ] PII/secrets redacted in filter chain before output
- [ ] TLS configured between all log shipping components
- [ ] Storage total_limit_size set to prevent disk exhaustion
- [ ] Multiline parser configured for Java/Python stack traces
- [ ] Log rotation configured for local buffer files
- [ ] Monitoring: Fluent Bit exposes /api/v1/metrics for scraping
- [ ] Dead letter queue configured for unparseable logs
