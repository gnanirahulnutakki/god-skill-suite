---
name: god-dev-builder
description: "God-level product and system builder skill. Use when designing and building software products, systems, or services end-to-end. Covers: product thinking, requirements engineering, system design, API design, database design, scalability, reliability engineering, observability, DevOps/CI-CD, documentation, and launch readiness. Ensures no shortcut is taken from idea to production. Prevents the most common catastrophic engineering mistakes. Treats every architectural decision as a research question first."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Product Builder

## Prime Directive

A great product is not a collection of features. It is a system that solves a real problem reliably, securely, efficiently, and maintainably — at the scale it needs to operate today and in the foreseeable future. No part of that definition is optional.

You do not start building until you understand the problem completely. You do not ship until you have verified correctness, security, performance, and observability. You do not call something "done" until it can be operated, debugged, and improved by someone who didn't write it.

---

## Phase 0: Problem Validation (Before Any Architecture)

### 0.1 Problem Statement Crystallization
Write a precise problem statement in this format:
> "When [user/system] tries to [do X], they face [specific pain/friction/failure] which causes [measurable negative outcome]. This happens because [root cause]."

If you cannot fill in all blanks with specifics, you don't understand the problem yet.

### 0.2 User & Stakeholder Mapping
- Who are the primary users? (who uses this every day)
- Who are the secondary users? (who uses outputs or is affected)
- Who are the decision stakeholders? (who owns success/failure)
- What are the non-negotiable constraints from each stakeholder group?

### 0.3 Problem Verification
- Has this problem been solved before? Why wasn't that solution adopted?
- What is the cost of NOT solving it? (quantify if possible)
- What is the minimum viable version that proves the solution works?
- What would make this solution a failure even if it technically works?

---

## Phase 1: Requirements Engineering

### 1.1 Functional Requirements
Write user stories in strict format:
> "As a [specific user type], I want to [perform action] so that [business value]."

For each story:
- Acceptance criteria (Given/When/Then)
- Priority (Must-have / Should-have / Could-have / Won't-have this version)
- Definition of done (exactly what makes this complete)

### 1.2 Non-Functional Requirements (NFRs)

**Never skip any of these. Ask explicitly if unknown.**

| Category | Specific Questions |
|----------|-------------------|
| **Performance** | P50/P95/P99 latency targets? Throughput (RPS/QPS/TPS)? |
| **Scalability** | Current load? 6-month projection? 2-year projection? |
| **Availability** | SLA? (99% = 87h/year downtime; 99.9% = 8.7h; 99.99% = 52min) |
| **Durability** | What data loss is acceptable? RPO and RTO? |
| **Security** | Compliance requirements? (SOC2, HIPAA, PCI, GDPR) Threat model? |
| **Consistency** | Strong vs eventual consistency? Which operations require which? |
| **Maintainability** | Team size? On-call rotation? Deployment frequency target? |
| **Cost** | Compute budget? Per-request cost ceiling? |
| **Observability** | Logging requirements? Audit trail requirements? |

### 1.3 Constraints
- Language/runtime mandated? Why? Is that constraint still valid?
- Cloud provider mandated?
- Existing systems that must be integrated?
- Regulatory / geographic data residency requirements?
- Timeline constraints? (and their impact on scope)

---

## Phase 2: System Design

### 2.1 Design Research
Before drawing any architecture:
1. Search for: `"<your system type> system design"` on GitHub, arXiv, engineering blogs
2. Read how similar systems were designed at scale: Dynamo, Spanner, Kafka, Cassandra, Zookeeper, Redis, Nginx, Envoy
3. Identify the core technical challenge(s) — the parts where the design can fail
4. Find academic papers on those challenges

### 2.2 High-Level Architecture

**Choose your architecture pattern and justify the choice**:

| Pattern | Use when |
|---------|---------|
| Monolith | Team < 5, domain poorly understood, startup pace, simple deployment |
| Modular monolith | Monolith but with clear domain boundaries, easier to extract later |
| Microservices | Team > 20, domains clearly separated, independent scaling needs, polyglot |
| Event-driven | High throughput, async workflows, audit trail needed, temporal decoupling |
| Lambda/Serverless | Spiky/unpredictable traffic, stateless operations, cost-sensitivity |
| CQRS | Read/write load asymmetric, complex query requirements, audit trail |
| Hexagonal (Ports & Adapters) | Domain logic must be isolated from infrastructure, testability critical |

**Never choose microservices by default. Distributed systems are hard. The overhead is real.**

### 2.3 Data Architecture

#### Storage Selection Criteria
Ask for every dataset:
- What is the access pattern? (read-heavy, write-heavy, mixed)
- What are the query patterns? (point lookups, range scans, full-text search, graph traversal)
- What is the consistency requirement? (strong, eventual, causal)
- What is the scale? (rows, bytes, operations per second)
- What is the schema evolution story?

| Need | Solution |
|------|---------|
| Relational, ACID, complex queries | PostgreSQL (prefer over MySQL for new projects) |
| Time-series data | TimescaleDB, InfluxDB, Prometheus |
| Document store | MongoDB, Firestore (for flexible schema) |
| Key-value cache | Redis (also: Pub/Sub, queues, rate limiting, sessions) |
| Wide-column / high write throughput | Cassandra, ScyllaDB |
| Graph data | Neo4j, Amazon Neptune, DGraph |
| Full-text search | Elasticsearch, OpenSearch, Typesense |
| Blob/object storage | S3, GCS, MinIO |
| Message queue | Kafka (high throughput), RabbitMQ (complex routing), SQS (managed simplicity) |
| OLAP / Analytics | ClickHouse, BigQuery, Redshift, DuckDB |

#### Schema Design Rules
- Normalize to 3NF by default; denormalize only when profiling shows it's necessary and justified
- Every table needs: primary key, created_at, updated_at
- Soft delete (deleted_at column) unless you have strong reasons for hard delete
- Add indexes for every foreign key and every column in a WHERE clause
- Plan for schema migrations from day one (use migration tools: Flyway, Alembic, golang-migrate)
- Partition large tables by time or high-cardinality dimension from the start

### 2.4 API Design

#### REST API Standards
- Use nouns for resources, not verbs: `/users/{id}` not `/getUser`
- Use HTTP methods correctly: GET (idempotent read), POST (create), PUT (full replace), PATCH (partial update), DELETE (delete)
- Use correct status codes: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable Entity, 429 Too Many Requests, 500 Internal Server Error
- Version from day one: `/v1/users` not `/users`
- Paginate all list endpoints: cursor-based pagination for high-volume, offset for simple cases
- Use consistent error response format: `{ "error": { "code": "RESOURCE_NOT_FOUND", "message": "...", "details": {...} } }`

#### API Quality Checklist
- [ ] OpenAPI/Swagger spec written before or alongside implementation
- [ ] All inputs validated (type, length, format, allowed values)
- [ ] All endpoints authenticated (explicitly note which are public)
- [ ] Rate limiting defined per endpoint per user/IP
- [ ] Idempotency keys supported for mutating operations
- [ ] Long-running operations use async pattern (return 202, provide status endpoint)
- [ ] Webhooks designed with retry, signing, and event schema versioning
- [ ] Breaking change policy documented

### 2.5 Scalability Design

**Scale dimensions**: User count, data volume, request rate, geographic distribution, feature complexity

**Scaling strategies** (apply in order, not all at once):
1. Optimize the code and queries first (free)
2. Vertical scaling (bigger machine) — simplest, has limits
3. Caching: in-process cache → shared cache (Redis) → CDN → HTTP caching headers
4. Read replicas for read-heavy databases
5. CQRS for asymmetric read/write patterns
6. Horizontal scaling: stateless services + load balancer
7. Database sharding: consistent hashing, range-based
8. Event streaming for decoupling and buffering load spikes
9. Geographic distribution: multi-region, data residency

**CAP Theorem**: For any distributed data store, choose two: Consistency, Availability, Partition Tolerance. Know which you chose and why.

### 2.6 Reliability Design

**Failure Mode Analysis**: For every external dependency and critical path:
- What happens if it is slow? (timeout + circuit breaker)
- What happens if it fails? (retry with exponential backoff + jitter, fallback)
- What happens if it returns wrong data? (validation, dead letter queue)
- What is the cascade failure risk? (bulkhead pattern)

**Resilience patterns**:
- **Timeout**: Every external call has an explicit timeout. No infinite waits.
- **Retry**: Retry transient errors. Never retry non-idempotent operations without idempotency keys.
- **Circuit Breaker**: Open circuit after N failures; half-open to test recovery
- **Bulkhead**: Isolate resources per dependency (separate thread pools, connection pools)
- **Fallback**: Degrade gracefully — serve stale data, return empty rather than error, use local computation
- **Health checks**: Every service exposes `/health` (liveness) and `/ready` (readiness)
- **Graceful shutdown**: Drain in-flight requests before terminating

---

## Phase 3: Implementation Standards

### 3.1 Project Setup Non-Negotiables
Before writing business logic:
- [ ] Version control initialized with `.gitignore` for secrets, binaries, dependencies
- [ ] Pre-commit hooks: linting, formatting, secret scanning (use `pre-commit` framework)
- [ ] Dependency management file committed with locked versions
- [ ] Environment configuration via environment variables (never hardcoded)
- [ ] Logging framework configured (structured JSON logging)
- [ ] Metrics collection setup (Prometheus, StatsD, or cloud-native)
- [ ] Distributed tracing setup (OpenTelemetry)
- [ ] Error tracking setup (Sentry or equivalent)
- [ ] Local development environment documented and scripted (docker-compose or devcontainer)
- [ ] Makefile or task runner with: `build`, `test`, `lint`, `run-local`, `clean`

### 3.2 Twelve-Factor App Compliance
Verify each factor for every service:
1. **Codebase**: One repo per service; no shared code via file system
2. **Dependencies**: Explicit declaration; no system-level dependencies assumed
3. **Config**: All config in environment variables; no config files in repo
4. **Backing services**: Treat databases, queues, etc. as attached resources
5. **Build/Release/Run**: Strictly separate build, release (config injection), and run stages
6. **Processes**: Stateless processes; persist nothing in memory across requests
7. **Port binding**: Service exports itself via a port; no runtime web server injection
8. **Concurrency**: Scale out via process model
9. **Disposability**: Fast startup; graceful shutdown on SIGTERM
10. **Dev/prod parity**: Keep dev, staging, and production as similar as possible
11. **Logs**: Treat logs as event streams; write to stdout only
12. **Admin processes**: Run admin/management tasks as one-off processes

### 3.3 Security-by-Default Implementation
- Secrets: use a secrets manager (AWS Secrets Manager, Vault, Doppler) — never `.env` files in production
- TLS: all inter-service communication over mTLS in production
- Authorization: implement RBAC or ABAC from day one — add permissions before you add features
- Input sanitization: validate at every system boundary using a schema validation library
- Output encoding: never trust data leaving the system to be safe — HTML encode, JSON escape, etc.
- Dependency updates: automate with Dependabot or Renovate from day one

---

## Phase 4: Observability (The Production Safety Net)

A service that cannot be observed cannot be operated. Observability is not optional.

### 4.1 The Three Pillars

**Metrics** (what is happening):
- RED method per service: Request rate, Error rate, Duration (latency distribution)
- USE method per resource: Utilization, Saturation, Errors (CPU, memory, disk, network)
- Business metrics: active users, conversion rate, revenue events
- Define SLIs (Service Level Indicators) and SLOs (Service Level Objectives) from day one

**Logs** (why it happened):
- Structured JSON: `{"level": "error", "service": "payment", "trace_id": "...", "user_id": "...", "error": "..."}`
- Log at boundaries, not inside functions
- Include: trace_id, span_id, user_id, request_id, operation, duration_ms
- Log levels: DEBUG (development only), INFO (business events), WARN (degraded but functional), ERROR (failure requiring action)
- Never log passwords, tokens, PII, or credit card data

**Traces** (how it happened):
- Instrument every service call, DB query, and external API call
- Use OpenTelemetry — vendor-neutral, works with Jaeger, Zipkin, Honeycomb, Datadog
- Propagate trace context across all service boundaries (headers: `traceparent`, `tracestate`)

### 4.2 Alerting Design
- Alert on symptoms, not causes (high error rate, high latency — not "CPU > 80%")
- Every alert must be actionable — if you can't describe what to do when it fires, don't create it
- Alert on SLO burn rate, not just threshold crossings
- Create runbooks for every alert: "When X fires, do A, B, C. If that doesn't resolve, escalate to Y."

### 4.3 Dashboards
At minimum, every service needs a dashboard showing:
- Request rate (total, per endpoint)
- Error rate (total, per error type)
- Latency (P50, P95, P99)
- Active instances / pod count
- Memory and CPU utilization
- Database connection pool utilization
- Queue depth (if applicable)
- Downstream service health

---

## Phase 5: CI/CD Pipeline

### 5.1 Pipeline Stages (Non-Negotiable Order)
```
[Commit] → [Build] → [Lint & Format Check] → [Unit Tests] → [Security Scan]
         → [Integration Tests] → [Build Container] → [Container Scan]
         → [Deploy to Staging] → [E2E Tests] → [Deploy to Production]
         → [Smoke Tests] → [Done]
```

No stage may be skipped. Failed stage blocks progression.

### 5.2 Deployment Strategies
- **Blue/Green**: Two identical environments; switch traffic atomically. Zero downtime. Easy rollback.
- **Canary**: Gradually shift traffic to new version (1% → 10% → 50% → 100%). Catch issues with limited blast radius.
- **Rolling**: Replace instances one at a time. Simple but slower rollback.
- **Feature flags**: Deploy code dark; enable feature selectively per user/group. Best for risky features.

**Default recommendation**: Canary + feature flags for most production services.

### 5.3 Container & Kubernetes Standards
```dockerfile
# Dockerfile non-negotiables
FROM <official-base>:<specific-version>    # Pin version exactly
USER nonroot                               # Never run as root
COPY --chown=nonroot:nonroot . .           # Don't run as root
RUN <build-steps>                          # Separate RUN layers minimally
HEALTHCHECK --interval=30s CMD <check>     # Always define health check
```

Kubernetes checklist:
- [ ] Resource requests and limits set for every container
- [ ] Liveness and readiness probes configured
- [ ] Pod disruption budgets defined for critical services
- [ ] HorizontalPodAutoscaler configured
- [ ] NetworkPolicy restricting ingress/egress
- [ ] RBAC for service accounts (principle of least privilege)
- [ ] Secrets from secrets store, not Kubernetes Secrets (or use Sealed Secrets / External Secrets)
- [ ] Pod security standards enforced

---

## Phase 6: Documentation Standards

### 6.1 Required Documentation (Non-Negotiable)
- **README.md**: What does this do? Why does it exist? How do I run it locally in 5 commands?
- **Architecture Decision Records (ADRs)**: One file per significant architectural decision. Format: Context → Decision → Consequences. Stored in `/docs/adr/`.
- **Runbook**: How to operate this in production. How to restart. How to debug. Common failure modes and fixes.
- **API Reference**: OpenAPI spec + human-readable usage examples
- **Data Dictionary**: Every significant data model documented (fields, types, constraints, relationships, business meaning)

### 6.2 ADR Template
```markdown
# ADR-001: [Short Title]

**Date**: YYYY-MM-DD
**Status**: Proposed | Accepted | Deprecated | Superseded by ADR-XXX

## Context
What is the situation requiring a decision? What forces are at play?

## Decision
What was decided?

## Consequences
What are the positive, negative, and neutral outcomes of this decision?
What is now easier? What is now harder?

## Alternatives Considered
What else was considered and why was it not chosen?
```

---

## Phase 7: Pre-Launch Checklist

Before any production launch, verify all of the following:

### Functionality
- [ ] All acceptance criteria from requirements verified
- [ ] All edge cases tested
- [ ] Load tested to 2x expected peak traffic
- [ ] Chaos testing: what happens when a dependency dies mid-operation?

### Security
- [ ] Penetration test performed (at minimum: automated scan with OWASP ZAP or Burp Suite)
- [ ] Secret rotation process documented and tested
- [ ] All dependencies up to date with no critical CVEs
- [ ] Data encryption verified at rest and in transit
- [ ] Access control reviewed by a second person

### Operations
- [ ] On-call rotation defined and runbook published
- [ ] Alerting configured and tested (fire a test alert)
- [ ] Rollback procedure documented and tested
- [ ] Backup and restore procedure tested (not just set up — tested)
- [ ] Incident response process defined

### Compliance
- [ ] Data retention policy implemented
- [ ] GDPR/CCPA deletion mechanism implemented if applicable
- [ ] Audit log implemented for all privileged operations
- [ ] Privacy policy and terms of service updated

---

## Self-Improvement Loop for Builders

After every system is built and deployed:
1. Run a post-launch review: what failed, what was harder than expected, what would you change?
2. Read the post-mortems of similar systems that failed (Google SRE Book, Jepsen analyses, AWS post-mortems)
3. Read the architecture papers of systems that scaled (Dynamo paper, Bigtable paper, Kafka paper)
4. Update your mental model. The next system will be better.
