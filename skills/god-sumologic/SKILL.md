---
name: god-sumologic
description: "God-level Sumo Logic mastery. Covers Sumo Logic architecture (collectors, sources, partitions), log search operators (parse, count, timeslice, transaction, outlier), Field Extraction Rules (FER), dashboards and scheduled searches, metrics with Prometheus compatibility, Cloud SIEM (Cloud Security Event Management), Terraform provider, and production operational patterns for enterprise log analytics. Never fabricate Sumo Logic search operators — verify against help.sumologic.com."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Sumo Logic

## Anti-Hallucination Rules

- NEVER invent Sumo Logic search operators — `parse`, `count`, `timeslice`, `where`, `transaction`, `outlier`, `predict`, `logreduce`, `logcompare` are real operators. Verify others.
- NEVER confuse Sumo Logic query syntax with Splunk SPL or Elasticsearch Query DSL — they are different languages.
- NEVER fabricate collector types — valid types are `Installed Collector` and `Hosted Collector`.
- ALWAYS note Sumo Logic plan tier when discussing features (Free, Essentials, Enterprise, Enterprise Security).

---

## 1. Architecture

```
Data Sources → Collectors → Sumo Logic Cloud
  ├── Installed Collector (on-prem agent, JVM-based)
  │   └── Sources: Local File, Remote File, Windows Event Log, Syslog
  ├── Hosted Collector (cloud-native, no agent)
  │   └── Sources: HTTP, AWS S3, CloudWatch, Kinesis, GCP, Azure
  └── OpenTelemetry Collector (OTLP → Sumo Logic)
```

### Hosted Collector with HTTP Source

```bash
# Send logs via HTTP
curl -X POST https://endpoint.sumologic.com/receiver/v1/http/<TOKEN> \
  -H "Content-Type: application/json" \
  -H "X-Sumo-Category: production/my-service" \
  -H "X-Sumo-Name: my-service-logs" \
  -d '{"timestamp":"2024-01-15T14:02:33Z","level":"error","service":"my-service","message":"Connection refused"}'
```

---

## 2. Log Search Operators

### Core Search Patterns

```
# Basic search with metadata filters
_sourceCategory=production/my-service AND "error"
| where status_code >= 500

# Parse structured and unstructured logs
_sourceCategory=production/nginx
| parse "* - - [*] \"* * *\" * * *" as client_ip, timestamp, method, url, protocol, status, bytes, duration

# JSON auto-parse
_sourceCategory=production/my-service
| json field=_raw "level", "service", "message", "duration_ms", "trace_id"
| where level = "error"

# Aggregation
_sourceCategory=production/my-service
| json "level", "service", "endpoint"
| where level = "error"
| count by service, endpoint
| sort by _count desc
| limit 20

# Time-series
_sourceCategory=production/my-service
| json "level"
| where level = "error"
| timeslice 5m
| count by _timeslice
| sort by _timeslice

# Transaction — correlate events across a session
_sourceCategory=production/checkout
| json "session_id", "step", "timestamp"
| transaction on session_id
    with states "cart_view" -> "checkout_start" -> "payment" -> "confirmation"
    results by flow

# LogReduce — automatic pattern detection
_sourceCategory=production/my-service
| logreduce

# LogCompare — compare time periods
_sourceCategory=production/my-service
| logcompare timeshift -24h

# Outlier detection
_sourceCategory=production/my-service
| json "duration_ms"
| timeslice 5m
| avg(duration_ms) as avg_duration by _timeslice
| outlier avg_duration window=10 threshold=3 consecutive=2 direction=+
```

---

## 3. Field Extraction Rules (FER)

```
# FER — extract fields at ingest time (reduces query-time parsing cost)
# Applied to all matching logs automatically

# Rule: Extract JSON fields from application logs
Scope: _sourceCategory=production/*
Parse Expression: 
  json "level", "service", "message", "duration_ms", "status_code", "trace_id"

# Rule: Extract from nginx access logs
Scope: _sourceCategory=production/nginx
Parse Expression:
  parse "* - - [*] \"* * *\" * *" as src_ip, timestamp, method, url, protocol, status_code, bytes
```

---

## 4. Metrics

```
# Sumo Logic supports Prometheus-format metrics
# Send via Prometheus remote_write or OTLP

# Metrics query
metric=http_requests_total service=my-service env=production
| rate
| sum by service, status_code

# Percentile calculation
metric=http_request_duration_seconds service=my-service
| quantize using p99
| avg by service

# Combine logs and metrics in dashboard
# Panel 1: Metrics — request rate
# Panel 2: Logs — error count over time
# Linked by: service name and time range
```

---

## 5. Cloud SIEM

```
# Security signal rules
_index=sec_record_*
| json "action", "srcDevice_ip", "dstDevice_ip", "user_username"
| where action = "LOGIN_FAILED"
| count by srcDevice_ip, user_username
| where _count > 10
# → Creates security signal: "Brute force attempt detected"

# Threat intelligence correlation
_sourceCategory=firewall/logs
| lookup type, malicious from threat_intel on src_ip = threat_ip
| where malicious = "true"
```

---

## 6. Terraform Provider

```hcl
resource "sumologic_collector" "hosted" {
  name        = "production-collector"
  description = "Hosted collector for production services"
  category    = "production"
}

resource "sumologic_http_source" "app_logs" {
  name         = "application-logs"
  collector_id = sumologic_collector.hosted.id
  category     = "production/my-service"
  content_type = "application/json"
}

resource "sumologic_field_extraction_rule" "json_parse" {
  name             = "Parse JSON application logs"
  scope            = "_sourceCategory=production/*"
  parse_expression = "json \"level\", \"service\", \"message\", \"duration_ms\""
  enabled          = true
}

resource "sumologic_scheduled_view" "error_summary" {
  index_name   = "error_summary"
  query        = "_sourceCategory=production/* | json \"level\" | where level=\"error\" | count by service | sort by _count"
  start_time   = "2024-01-01T00:00:00Z"
  retention_period = 30
}
```

---

## Cross-Domain Connections

**Sumo Logic ↔ AWS:** Native integrations with CloudWatch Logs, S3, CloudTrail, GuardDuty, and VPC Flow Logs via Hosted Collectors with AWS sources.

**Sumo Logic ↔ Kubernetes:** Sumo Logic Kubernetes Collection uses Helm chart with Fluent Bit (logs), Prometheus (metrics), and Falco (security events).

**Sumo Logic ↔ CI/CD:** Software Development Optimization (SDO) correlates deployments, builds, and incidents for DORA metric tracking.

---

## Self-Review Checklist

- [ ] Field Extraction Rules (FER) configured for high-volume log sources (reduces query cost)
- [ ] Partitions configured for frequently queried data (improves search performance)
- [ ] Scheduled searches configured for recurring reports
- [ ] Data forwarding to S3 configured for compliance/archive
- [ ] Collector health monitored via `_sourceCategory=collector*` searches
- [ ] Role-based access control (RBAC) configured per team
- [ ] Log ingest budget alerts configured to prevent cost overruns
- [ ] Cloud SIEM rules tuned to reduce false positives
- [ ] Dashboards linked to specific time-boxed investigations
- [ ] Terraform manages collectors, sources, and FERs as code
