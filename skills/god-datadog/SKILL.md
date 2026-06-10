---
name: god-datadog
description: "God-level Datadog observability mastery. Covers Datadog Agent architecture and configuration, DogStatsD custom metrics, APM distributed tracing (ddtrace), log management and pipelines, monitors and alerting (metric, anomaly, forecast, composite, SLO), Synthetics (API and browser tests), RUM (Real User Monitoring), infrastructure monitoring, DDSQL, Notebooks, CI Visibility, Security Monitoring (Cloud SIEM), and Terraform provider for Datadog-as-code. Never fabricate Datadog API endpoints or monitor types — verify against docs.datadoghq.com."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Datadog Observability

## Anti-Hallucination Rules

- NEVER invent Datadog metric names — custom metrics follow `custom.metric.name` convention; built-in metrics have specific prefixes (`system.`, `docker.`, `kubernetes.`).
- NEVER fabricate monitor types — valid types: `metric alert`, `query alert`, `service check`, `event alert`, `composite`, `log alert`, `process alert`, `synthetics alert`, `slo alert`, `event-v2 alert`, `audit alert`.
- NEVER confuse Datadog plans — APM, Logs, Infrastructure have separate pricing and feature sets.
- ALWAYS note when features require specific Datadog Agent versions or plan tiers.

---

## 1. Datadog Agent Architecture

```
Datadog Agent (runs on every host / K8s DaemonSet):
  ├── Core Agent         — infrastructure metrics, host metadata
  ├── Trace Agent        — APM trace collection (port 8126)
  ├── Process Agent      — live process monitoring
  ├── Log Agent          — log collection and forwarding
  ├── DogStatsD          — custom metrics UDP receiver (port 8125)
  ├── Security Agent     — runtime security, compliance
  └── OTLP Receiver      — OpenTelemetry protocol ingestion (port 4317/4318)
```

### K8s DaemonSet Configuration

```yaml
# datadog-values.yaml (Helm chart: datadog/datadog)
datadog:
  apiKey: <DATADOG_API_KEY>       # or use existingSecret
  appKey: <DATADOG_APP_KEY>
  site: datadoghq.com             # or datadoghq.eu, us3.datadoghq.com
  clusterName: production-us-east-1
  
  logs:
    enabled: true
    containerCollectAll: true      # Collect all container logs
  
  apm:
    portEnabled: true              # Enable APM (port 8126)
    socketEnabled: true            # Unix domain socket (lower overhead)
  
  processAgent:
    enabled: true
    processCollection: true
  
  dogstatsd:
    useHostPort: true
    nonLocalTraffic: true
  
  networkMonitoring:
    enabled: true                  # Network Performance Monitoring
  
  securityAgent:
    runtime:
      enabled: true                # Cloud Workload Security
    compliance:
      enabled: true                # CSPM

  kubelet:
    tlsVerify: false               # Set true if kubelet has valid cert

agents:
  tolerations:
    - operator: Exists             # Run on all nodes including tainted

clusterAgent:
  enabled: true
  replicas: 2
  metricsProvider:
    enabled: true                  # Enable HPA with Datadog metrics
```

---

## 2. DogStatsD Custom Metrics

```python
# Python — datadog library (verified)
from datadog import DogStatsd

statsd = DogStatsd(host="localhost", port=8125)

# Counter — monotonically increasing
statsd.increment("my_app.page_views", tags=["page:home", "env:production"])

# Gauge — current value
statsd.gauge("my_app.queue_depth", 42, tags=["queue:orders"])

# Histogram — distribution of values
statsd.histogram("my_app.request_duration", 0.234, tags=["endpoint:/api/users"])

# Distribution — globally accurate percentiles (Datadog-specific)
statsd.distribution("my_app.request_latency", 0.456, tags=["service:api"])

# Set — count unique elements
statsd.set("my_app.unique_users", user_id, tags=["env:production"])

# Service check
statsd.service_check("my_app.database", DogStatsd.OK, 
                      message="Database is healthy")

# Event
statsd.event("Deployment Complete", 
             "Deployed v2.4.1 to production",
             alert_type="success",
             tags=["service:my-app"])
```

---

## 3. APM Distributed Tracing

```python
# ddtrace auto-instrumentation — Python
# pip install ddtrace
# ddtrace-run python app.py   (wraps the application)

# OR: manual instrumentation
from ddtrace import tracer, patch_all

patch_all()  # Auto-instrument supported libraries

@tracer.wrap(service="my-service", resource="process_order")
def process_order(order_id):
    with tracer.trace("validate_order") as span:
        span.set_tag("order.id", order_id)
        validate(order_id)
    
    with tracer.trace("charge_payment", service="payment-service") as span:
        span.set_tag("payment.method", "credit_card")
        charge(order_id)
```

### APM Environment Variables

```bash
DD_SERVICE=my-service
DD_ENV=production
DD_VERSION=2.4.1
DD_TRACE_AGENT_URL=http://localhost:8126    # or unix:///var/run/datadog/apm.socket
DD_TRACE_SAMPLE_RATE=1.0                    # 100% sampling (reduce in high-traffic)
DD_LOGS_INJECTION=true                       # Inject trace_id into logs
DD_PROFILING_ENABLED=true                    # Continuous profiling
DD_RUNTIME_METRICS_ENABLED=true              # Runtime metrics (GC, threads)
```

---

## 4. Log Management

### Log Pipeline Configuration

```yaml
# Log processing pipeline (configured in Datadog UI or API)
# Pipelines process logs in order: parse → enrich → route

# Grok Parser processor
- type: grok-parser
  name: "Parse nginx access log"
  source: message
  samples:
    - '172.16.0.1 - - [15/Jan/2024:14:02:33 +0000] "GET /api/users HTTP/1.1" 200 1234 0.045'
  grok:
    matchRules: |
      access.common %{_client_ip} %{_ident} %{_auth} \[%{_date_access}\] "%{_method} %{_url} HTTP/%{_version}" %{_status_code} %{_bytes_written} %{_duration}
    supportRules: |
      _client_ip %{ipOrHost:network.client.ip}
      _method %{word:http.method}
      _url %{notSpace:http.url}
      _status_code %{integer:http.status_code}
      _duration %{number:duration}

# Remapper — remap attributes
- type: attribute-remapper
  name: "Remap status_code to http.status_code"
  sources: ["status_code"]
  target: "http.status_code"
  target_type: "integer"

# Category processor — classify logs
- type: category-processor
  name: "Classify by status"
  target: "http.status_category"
  categories:
    - filter: "@http.status_code:[200 TO 299]"
      name: "Success"
    - filter: "@http.status_code:[400 TO 499]"
      name: "Client Error"
    - filter: "@http.status_code:[500 TO 599]"
      name: "Server Error"
```

### Log Exclusion Filters

```yaml
# Exclude noisy logs before indexing (saves cost)
exclusion_filters:
  - name: "Health checks"
    filter: "source:nginx @http.url:/health*"
  - name: "Debug logs in production"
    filter: "env:production status:debug"
```

---

## 5. Monitors and Alerting

### Monitor Types

```python
# Datadog API — Python (datadog-api-client)
from datadog_api_client.v1.api.monitors_api import MonitorsApi
from datadog_api_client.v1.model.monitor import Monitor

# Metric Alert
monitor = Monitor(
    name="High Error Rate",
    type="query alert",
    query="avg(last_5m):sum:http.requests.errors{env:production}.as_rate() / sum:http.requests{env:production}.as_rate() > 0.05",
    message="""
    Error rate is above 5% in production.
    
    @slack-platform-alerts @pagerduty-production
    
    {{#is_alert}}
    Current error rate: {{value}}%
    Affected service: {{service.name}}
    {{/is_alert}}
    
    {{#is_recovery}}
    Error rate recovered to {{value}}%
    {{/is_recovery}}
    """,
    tags=["team:backend", "service:api"],
    options={
        "thresholds": {"critical": 0.05, "warning": 0.02},
        "notify_no_data": True,
        "no_data_timeframe": 10,
        "renotify_interval": 60,
        "evaluation_delay": 60,
        "include_tags": True,
    }
)

# Anomaly Detection Monitor
anomaly_monitor = Monitor(
    name="Anomalous Latency",
    type="query alert",
    query="avg(last_4h):anomalies(avg:http.request.duration{env:production}, 'agile', 3, direction='above') >= 1",
    message="Latency is anomalously high. @slack-platform-alerts"
)

# Composite Monitor — alert only when multiple conditions are true
composite_monitor = Monitor(
    name="Degraded Service",
    type="composite",
    query="123 && 456",  # Monitor IDs
    message="Both high error rate AND high latency detected."
)
```

---

## 6. SLO Monitors

```python
# SLO — Service Level Objective
slo = {
    "name": "API Availability SLO",
    "type": "metric",
    "description": "99.9% of requests should succeed",
    "query": {
        "numerator": "sum:http.requests{env:production,!status:5xx}.as_count()",
        "denominator": "sum:http.requests{env:production}.as_count()"
    },
    "thresholds": [
        {"timeframe": "30d", "target": 99.9, "warning": 99.95}
    ],
    "tags": ["service:api", "team:backend"]
}
```

---

## 7. Synthetics

```python
# API Test
api_test = {
    "name": "API Health Check",
    "type": "api",
    "subtype": "http",
    "config": {
        "request": {
            "method": "GET",
            "url": "https://api.example.com/health",
            "timeout": 30
        },
        "assertions": [
            {"type": "statusCode", "operator": "is", "target": 200},
            {"type": "responseTime", "operator": "lessThan", "target": 2000},
            {"type": "body", "operator": "contains", "target": "\"status\":\"ok\""}
        ]
    },
    "locations": ["aws:us-east-1", "aws:eu-west-1", "aws:ap-southeast-1"],
    "options": {
        "tick_every": 60,  # Run every 60 seconds
        "min_failure_duration": 120,
        "min_location_failed": 2,
        "retry": {"count": 2, "interval": 500}
    }
}
```

---

## 8. Datadog as Code (Terraform)

```hcl
resource "datadog_monitor" "error_rate" {
  name    = "High Error Rate - ${var.service_name}"
  type    = "query alert"
  query   = "avg(last_5m):sum:http.requests{service:${var.service_name},status:error}.as_rate() / sum:http.requests{service:${var.service_name}}.as_rate() > 0.05"
  message = <<-EOT
    Error rate exceeded 5% for ${var.service_name}.
    @slack-${var.team}-alerts @pagerduty-${var.team}
  EOT

  monitor_thresholds {
    critical = 0.05
    warning  = 0.02
  }

  notify_no_data    = true
  no_data_timeframe = 10
  renotify_interval = 60
  tags              = ["team:${var.team}", "service:${var.service_name}", "env:${var.environment}"]
}

resource "datadog_dashboard_json" "service_dashboard" {
  dashboard = file("${path.module}/dashboards/${var.service_name}.json")
}

resource "datadog_synthetics_test" "api_health" {
  name      = "${var.service_name} Health Check"
  type      = "api"
  subtype   = "http"
  status    = "live"
  locations = ["aws:us-east-1", "aws:eu-west-1"]

  request_definition {
    method = "GET"
    url    = "https://${var.service_url}/health"
  }

  assertion {
    type     = "statusCode"
    operator = "is"
    target   = "200"
  }

  options_list {
    tick_every           = 60
    min_failure_duration = 120
    min_location_failed  = 2
  }
}
```

---

## Cross-Domain Connections

**Datadog ↔ Kubernetes:** Cluster Agent provides cluster-level metrics, HPA with custom Datadog metrics, and Admission Controller for auto-injecting APM libraries.

**Datadog ↔ CI/CD:** CI Visibility traces test execution, identifies flaky tests, and measures pipeline performance. Test Impact Analysis skips unchanged tests.

**Datadog ↔ Security:** Cloud SIEM correlates security signals from logs, Cloud Security Posture Management (CSPM) audits infrastructure compliance, Application Security Monitoring (ASM) detects runtime attacks.

---

## Self-Review Checklist

- [ ] DD_SERVICE, DD_ENV, DD_VERSION set as unified service tags on all services
- [ ] APM trace sampling rate appropriate for traffic volume
- [ ] DD_LOGS_INJECTION enabled for trace-log correlation
- [ ] Log exclusion filters configured to reduce indexing costs
- [ ] Monitors use `notify_no_data` to detect silent failures
- [ ] SLOs defined for all customer-facing services
- [ ] Synthetics tests cover critical user journeys from multiple locations
- [ ] Dashboard-as-code in Terraform (not manually created)
- [ ] Custom metrics use distributions (not histograms) for global percentiles
- [ ] Monitor notification includes `{{#is_alert}}` and `{{#is_recovery}}` blocks
- [ ] Tags follow consistent naming: `service:`, `env:`, `team:`, `version:`
