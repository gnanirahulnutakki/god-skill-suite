---
name: god-prometheus-grafana
description: "God-level Prometheus and Grafana mastery. Deep dive into Prometheus architecture (TSDB, WAL, compaction), PromQL advanced patterns (subqueries, label_replace, absent/absent_over_time), Alertmanager routing and inhibition, recording rules, remote_write, federation and long-term storage (Thanos, Cortex, Mimir), Grafana dashboard-as-code (Grafonnet, Terraform provider), Grafana Alerting v2, provisioning, Loki LogQL, Tempo TraceQL, Mimir metrics, and the full LGTM stack (Loki, Grafana, Tempo, Mimir). Never fabricate PromQL functions or Grafana panel types — verify against official docs."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Prometheus & Grafana

## Anti-Hallucination Rules

- NEVER invent PromQL functions — `rate()`, `irate()`, `increase()`, `histogram_quantile()`, `absent()`, `label_replace()`, `label_join()`, `clamp_min()`, `clamp_max()`, `vector()`, `scalar()` exist. Verify any others.
- NEVER fabricate Prometheus metric names — verify exact names against the exporter documentation.
- NEVER confuse Thanos, Cortex, and Mimir — they are different projects with different architectures.
- NEVER invent Grafana panel types — `timeseries`, `stat`, `gauge`, `table`, `heatmap`, `bargauge`, `text`, `logs`, `traces`, `news`, `geomap`, `canvas`, `histogram` are real types.
- ALWAYS specify Grafana version when discussing features — Alerting v2 is Grafana 8+, Unified Alerting is Grafana 9+.

---

## 1. Prometheus Architecture Deep Dive

### TSDB (Time Series Database)

```
Prometheus TSDB Storage Layout:
data/
├── 01BKGV7JBM69T2G1BGBGM6KB12/   # Block (2h default)
│   ├── chunks/                     # Compressed time series chunks
│   │   └── 000001
│   ├── index                       # Inverted index (label → series)
│   ├── meta.json                   # Block metadata
│   └── tombstones                  # Deletion marks
├── 01BKGTZQ1SYQJTR4PB43C8PD98/
├── chunks_head/                    # In-memory WAL chunks
├── wal/                            # Write-Ahead Log (crash recovery)
│   ├── 00000001
│   └── 00000002
└── lock
```

**Key metrics for TSDB health:**
```promql
# Active time series count
prometheus_tsdb_head_series

# Samples ingested per second
rate(prometheus_tsdb_head_samples_appended_total[5m])

# TSDB compaction duration
prometheus_tsdb_compaction_duration_seconds

# WAL corruption count
prometheus_tsdb_wal_corruptions_total

# Memory used by head block
prometheus_tsdb_head_chunks_storage_size_bytes
```

### Scrape Configuration Advanced

```yaml
global:
  scrape_interval: 15s
  scrape_timeout: 10s
  evaluation_interval: 15s
  external_labels:
    cluster: production-us-east-1
    environment: production

scrape_configs:
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      # Only scrape pods with prometheus.io/scrape annotation
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: 'true'
      # Use custom metrics path if annotated
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      # Use custom port if annotated
      - source_labels: [__address__, __meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
        target_label: __address__
      # Map pod labels to Prometheus labels
      - action: labelmap
        regex: __meta_kubernetes_pod_label_(.+)
      # Add namespace and pod name labels
      - source_labels: [__meta_kubernetes_namespace]
        action: replace
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        action: replace
        target_label: pod

  - job_name: 'kubernetes-service-endpoints'
    kubernetes_sd_configs:
      - role: endpoints
    relabel_configs:
      - source_labels: [__meta_kubernetes_service_annotation_prometheus_io_scrape]
        action: keep
        regex: 'true'
```

---

## 2. PromQL Advanced Patterns

### Subqueries (Prometheus 2.7+)

```promql
# Subquery: compute max of 5-minute rate over 1 hour
max_over_time(rate(http_requests_total[5m])[1h:1m])
#                                          ^^^  ^^^
#                                          range step

# p99 latency trend over 24 hours
max_over_time(
  histogram_quantile(0.99, 
    sum by (le) (rate(http_request_duration_seconds_bucket[5m]))
  )[24h:5m]
)
```

### absent() — Alert on Missing Metrics

```promql
# Alert if a target stops reporting
absent(up{job="my-service"})

# Alert if a metric hasn't been seen in 15 minutes
absent_over_time(http_requests_total{job="my-service"}[15m])
```

### label_replace() and label_join()

```promql
# Extract region from instance label
label_replace(
  up{job="my-service"},
  "region",                    # New label name
  "$1",                        # Replacement (capture group)
  "instance",                  # Source label
  "(.+)-\\d+\\.example\\.com" # Regex
)

# Join labels into a new label
label_join(
  up{job="my-service"},
  "instance_info",      # New label
  "/",                  # Separator
  "namespace", "pod"    # Source labels
)
```

### Multi-Window Multi-Burn-Rate SLO Alerts

```yaml
# Recording rules for SLO calculation (99.9% availability SLO)
groups:
  - name: slo-recording-rules
    interval: 30s
    rules:
      # Error ratio (5m window)
      - record: job:slo_errors:ratio_rate5m
        expr: |
          sum by (job) (rate(http_requests_total{status=~"5.."}[5m]))
          / sum by (job) (rate(http_requests_total[5m]))

      # Error ratio (30m window)
      - record: job:slo_errors:ratio_rate30m
        expr: |
          sum by (job) (rate(http_requests_total{status=~"5.."}[30m]))
          / sum by (job) (rate(http_requests_total[30m]))

      # Error ratio (1h window)
      - record: job:slo_errors:ratio_rate1h
        expr: |
          sum by (job) (rate(http_requests_total{status=~"5.."}[1h]))
          / sum by (job) (rate(http_requests_total[1h]))

      # Error ratio (6h window)
      - record: job:slo_errors:ratio_rate6h
        expr: |
          sum by (job) (rate(http_requests_total{status=~"5.."}[6h]))
          / sum by (job) (rate(http_requests_total[6h]))

  - name: slo-alerts
    rules:
      # Critical: 14.4x burn rate over 1h AND 5m (2% of monthly budget)
      - alert: SLOBurnRateCritical
        expr: |
          job:slo_errors:ratio_rate1h > (14.4 * 0.001)
          and
          job:slo_errors:ratio_rate5m > (14.4 * 0.001)
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "{{ $labels.job }} is burning error budget at 14.4x rate"

      # Warning: 6x burn rate over 6h AND 30m (5% of monthly budget)
      - alert: SLOBurnRateWarning
        expr: |
          job:slo_errors:ratio_rate6h > (6 * 0.001)
          and
          job:slo_errors:ratio_rate30m > (6 * 0.001)
        for: 5m
        labels:
          severity: warning
```

---

## 3. Alertmanager Configuration

```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m
  slack_api_url: 'https://hooks.slack.com/services/T00/B00/XXX'
  pagerduty_url: 'https://events.pagerduty.com/v2/enqueue'

route:
  receiver: 'default-slack'
  group_by: ['alertname', 'cluster', 'namespace']
  group_wait: 30s           # Wait before first notification
  group_interval: 5m        # Wait between notifications for same group
  repeat_interval: 4h       # Resend unresolved alerts
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty-critical'
      continue: true         # Also send to subsequent matching routes
    - match:
        severity: critical
      receiver: 'slack-critical'
    - match:
        severity: warning
      receiver: 'slack-warnings'
      group_wait: 10m
    - match_re:
        namespace: 'kube-.*'
      receiver: 'platform-team'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'cluster', 'namespace']

receivers:
  - name: 'default-slack'
    slack_configs:
      - channel: '#monitoring'
        send_resolved: true
        title: '{{ .GroupLabels.alertname }}'
        text: >-
          {{ range .Alerts }}
          *{{ .Labels.severity | toUpper }}* {{ .Annotations.summary }}
          {{ end }}

  - name: 'pagerduty-critical'
    pagerduty_configs:
      - service_key: '<PD_SERVICE_KEY>'
        severity: '{{ if eq .GroupLabels.severity "critical" }}critical{{ else }}warning{{ end }}'

  - name: 'slack-critical'
    slack_configs:
      - channel: '#critical-alerts'
        color: '{{ if eq .Status "firing" }}danger{{ else }}good{{ end }}'
        send_resolved: true

  - name: 'slack-warnings'
    slack_configs:
      - channel: '#warnings'
        send_resolved: true

  - name: 'platform-team'
    slack_configs:
      - channel: '#platform-alerts'
```

---

## 4. Long-Term Storage: Thanos vs Mimir

### Thanos Architecture

```
Sidecar Model:
  Prometheus → Thanos Sidecar → Object Storage (S3/GCS)
                     ↓
              Thanos Store Gateway ← reads from object storage
                     ↓
              Thanos Querier ← unified query across all stores
                     ↓
              Grafana

Components:
  Sidecar:        Runs alongside Prometheus, uploads TSDB blocks
  Store Gateway:  Serves historical data from object storage
  Querier:        Deduplicates and merges data from multiple sources
  Compactor:      Downsamples and compacts blocks in object storage
  Ruler:          Evaluates recording/alerting rules against Querier
  Receiver:       Alternative to Sidecar — receives remote_write
```

### Mimir (Grafana)

```
Prometheus → remote_write → Mimir
                              ├── Distributor (receives, validates, shards)
                              ├── Ingester (writes to WAL, builds TSDB blocks)
                              ├── Store Gateway (serves historical blocks)
                              ├── Querier (queries ingesters + store)
                              ├── Query Frontend (caching, splitting)
                              ├── Compactor (block compaction)
                              └── Object Storage (S3/GCS)

Key difference from Thanos:
  - Mimir is a single binary (monolithic or microservices mode)
  - No sidecar needed — uses remote_write from Prometheus
  - Native multi-tenancy (X-Scope-OrgID header)
  - Designed for massive scale (10B+ active series)
```

### remote_write Configuration

```yaml
# prometheus.yml — send metrics to Mimir/Thanos Receiver
remote_write:
  - url: "http://mimir:9009/api/v1/push"
    headers:
      X-Scope-OrgID: "my-tenant"
    queue_config:
      max_samples_per_send: 1000
      batch_send_deadline: 5s
      max_shards: 200
    write_relabel_configs:
      - source_labels: [__name__]
        regex: 'go_.*'
        action: drop           # Don't send Go runtime metrics
```

---

## 5. Grafana Dashboard-as-Code

### Grafonnet (Jsonnet)

```jsonnet
// dashboard.jsonnet
local grafana = import 'github.com/grafana/grafonnet/gen/grafonnet-latest/main.libsonnet';

local dashboard = grafana.dashboard;
local panel = grafana.panel;
local query = grafana.query;

dashboard.new('My Service Dashboard')
+ dashboard.withUid('my-service-dashboard')
+ dashboard.withTags(['my-service', 'production'])
+ dashboard.withTimepicker(
    dashboard.timepicker.withRefreshIntervals(['5s', '10s', '30s', '1m'])
)
+ dashboard.withPanels([
    panel.timeSeries.new('Request Rate')
    + panel.timeSeries.queryOptions.withTargets([
        query.prometheus.new('A',
            'sum(rate(http_requests_total{job="my-service"}[5m])) by (status_code)')
        + query.prometheus.withLegendFormat('{{status_code}}'),
    ])
    + panel.timeSeries.standardOptions.withUnit('reqps')
    + panel.timeSeries.gridPos.withW(12)
    + panel.timeSeries.gridPos.withH(8),

    panel.timeSeries.new('p99 Latency')
    + panel.timeSeries.queryOptions.withTargets([
        query.prometheus.new('B',
            'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job="my-service"}[5m])) by (le))')
    ])
    + panel.timeSeries.standardOptions.withUnit('s')
    + panel.timeSeries.gridPos.withW(12)
    + panel.timeSeries.gridPos.withH(8)
    + panel.timeSeries.gridPos.withX(12),
])
```

### Grafana Terraform Provider

```hcl
resource "grafana_dashboard" "my_service" {
  config_json = file("dashboards/my-service.json")
  folder      = grafana_folder.team.id
  overwrite   = true
}

resource "grafana_folder" "team" {
  title = "Backend Team"
}

resource "grafana_data_source" "prometheus" {
  type = "prometheus"
  name = "Prometheus"
  url  = "http://prometheus:9090"
  
  json_data_encoded = jsonencode({
    httpMethod   = "POST"
    exemplarTraceIdDestinations = [{
      name          = "traceID"
      datasourceUid = grafana_data_source.tempo.uid
    }]
  })
}

resource "grafana_contact_point" "slack" {
  name = "Slack Critical"
  slack {
    url     = var.slack_webhook_url
    channel = "#critical-alerts"
  }
}

resource "grafana_notification_policy" "default" {
  contact_point = grafana_contact_point.slack.name
  group_by      = ["alertname", "namespace"]
}
```

### Provisioning (YAML-based)

```yaml
# /etc/grafana/provisioning/datasources/default.yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    jsonData:
      exemplarTraceIdDestinations:
        - name: traceID
          datasourceUid: tempo
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200

# /etc/grafana/provisioning/dashboards/default.yaml
apiVersion: 1
providers:
  - name: 'default'
    folder: 'Provisioned'
    type: file
    disableDeletion: true
    updateIntervalSeconds: 30
    options:
      path: /var/lib/grafana/dashboards
      foldersFromFilesStructure: true
```

---

## 6. LGTM Stack Integration

```
Loki   — Logs    (LogQL)
Grafana — Visualization
Tempo  — Traces  (TraceQL)
Mimir  — Metrics (PromQL)

Correlation:
  Log line → extract trace_id → link to Tempo trace
  Metric exemplar → trace_id → link to Tempo trace
  Trace span → service name → link to Loki logs
```

### TraceQL (Tempo)

```
# Find traces with HTTP errors taking > 500ms
{span.http.status_code >= 500 && duration > 500ms}

# Find traces for a specific service
{resource.service.name = "my-service"}

# Find traces with specific attributes
{span.db.system = "postgresql" && duration > 1s}

# Structural queries — find traces where a parent span calls a child
{span.http.method = "POST"} >> {span.db.statement =~ "INSERT.*"}
```

---

## Cross-Domain Connections

**Prometheus ↔ Kubernetes:** ServiceMonitor and PodMonitor CRDs (Prometheus Operator) auto-discover scrape targets. PrometheusRule CRD manages alerting/recording rules declaratively.

**Grafana ↔ GitOps:** Dashboard JSON/Jsonnet in Git, provisioned via Terraform or Grafana provisioning. ArgoCD syncs dashboards as ConfigMaps.

**Mimir ↔ Multi-Cluster:** Each cluster runs Prometheus with remote_write to centralized Mimir. X-Scope-OrgID provides tenant isolation. Querier federates across all ingesters and store gateways.

---

## Self-Review Checklist

- [ ] Counters always queried with `rate()` or `increase()`, never raw
- [ ] Recording rules exist for expensive dashboard queries
- [ ] Alertmanager routing has inhibition rules (critical inhibits warning)
- [ ] SLO alerts use multi-window multi-burn-rate pattern
- [ ] `absent()` alerts detect missing targets
- [ ] Cardinality reviewed — no user_id/request_id in labels
- [ ] remote_write configured with write_relabel_configs to drop unnecessary metrics
- [ ] Grafana dashboards use consistent units on all axes
- [ ] Dashboard-as-code in Git (Grafonnet or Terraform), not manually created
- [ ] Grafana provisioning configured for data sources and dashboards
- [ ] Long-term storage (Thanos/Mimir) configured for production retention
- [ ] Exemplars enabled for linking metrics to traces
