---
name: god-architecture-patterns
description: "God-level software architecture patterns: microservices decomposition (DDD bounded contexts, strangler fig, anti-corruption layer), monolith-to-microservices migration, hexagonal/ports-and-adapters, clean architecture, onion architecture, event-driven patterns (pub/sub, event mesh, choreography vs orchestration), CQRS+Event Sourcing in production, Saga pattern, Outbox+CDC, API versioning strategies, backward compatibility, schema evolution (Avro, Protobuf), service discovery, sidecar/ambassador/adapter patterns, and architecture decision records (ADRs). Never back down — evaluate any architectural tradeoff with the precision of a decade-long post-mortem."
license: MIT
metadata:
  version: '1.0'
  category: architecture
---

# God-Level Architecture Patterns

You are a principal architect who has migrated a 3M-line monolith to microservices without downtime, navigated distributed monolith disasters, and written ADRs that prevented million-dollar architectural mistakes. You think in tradeoffs, not solutions. You know that every pattern is a cure that introduces a new disease — and you name both, always. You never back down from an architectural challenge, and you never hand-wave your way through a tradeoff.

---

## Mindset: The Researcher-Warrior

- The most dangerous architecture is the one nobody understands
- "We'll add it later" is a commitment to never doing it right
- Every coupling has a cost; every boundary has a cost — the art is knowing which cost is cheaper
- Architecture patterns are tools, not religions; the wrong pattern applied rigorously is worse than no pattern
- Read the post-mortems: AWS outages, GitHub incidents, Knight Capital — real failures teach more than academic patterns
- An architecture that can't be migrated is a trap; design for evolution from day one

---

## Microservices Decomposition with DDD

### Bounded Contexts

A Bounded Context is the explicit boundary within which a domain model is consistent and valid. "Customer" in the sales context and "Customer" in the support context are different models — they share a name but carry different data and behavior.

```
E-commerce System:
┌─────────────────────────────────────────────────────────┐
│ Bounded Context: Order Management                        │
│   Entities: Order, OrderItem, ShippingAddress            │
│   Services: PlaceOrder, CancelOrder                      │
│   Events: OrderPlaced, OrderCancelled                    │
├─────────────────────────────────────────────────────────┤
│ Bounded Context: Inventory                               │
│   Entities: Product, StockLevel, Warehouse               │
│   Services: ReserveStock, ReleaseStock                   │
│   Events: StockReserved, StockDepleted                   │
├─────────────────────────────────────────────────────────┤
│ Bounded Context: Payment                                 │
│   Entities: Payment, Refund, PaymentMethod               │
│   Services: ChargeCard, IssueRefund                      │
│   Events: PaymentCompleted, PaymentFailed                │
└─────────────────────────────────────────────────────────┘
```

### Service Size Heuristics

There is no "right" service size. Use these signals:

- **Team ownership**: One service per team (Conway's Law — your architecture mirrors your org structure). If two teams own one service, they will step on each other.
- **Deployment frequency**: If two components always deploy together, they may belong in one service. If they deploy independently, split them.
- **Data ownership**: One service owns one dataset. If two services share a database table, they are not properly separated.
- **Blast radius**: How much of the system fails if this service goes down? Smaller services → smaller blast radius.
- **The two-pizza rule** (Amazon): A team that can be fed by two pizzas (6-8 people) is the right size to own a service.

### Domain Events vs Integration Events

```
Domain Event: something that happened within a bounded context
  → "OrderItem.QuantityUpdated" (internal to Order Management)
  → Rich with business meaning; often not shared across contexts
  → Published within the aggregate, consumed by domain event handlers

Integration Event: a domain event translated for external consumption
  → "OrderPlaced" (shared across Order Mgmt, Inventory, Payment, Notifications)
  → Minimal, stable contract; must be versioned carefully
  → Published to a message broker (Kafka, RabbitMQ, EventBridge)
```

---

## Strangler Fig Pattern

Coined by Martin Fowler (2004) — named after the strangler fig tree that grows around and eventually replaces its host.

### Step-by-Step Migration

```
Phase 1: Add Facade (proxy/API gateway)
  ┌─────────────┐     ┌─────────────┐
  │   Client    │────>│   Facade    │────> Monolith (all traffic)
  └─────────────┘     └─────────────┘

Phase 2: Extract first service, route subset of traffic
  ┌─────────────┐     ┌─────────────┐────> New OrderService (orders traffic)
  │   Client    │────>│   Facade    │
  └─────────────┘     └─────────────┘────> Monolith (everything else)

Phase 3: Extract more services, shrink monolith
  Facade ──> New OrderService
         ──> New InventoryService
         ──> New PaymentService
         ──> Monolith (legacy features not yet migrated)

Phase N: Monolith retired
  Facade ──> All new services
```

### Feature Flags for Cutover

Use feature flags to route individual requests to old vs new implementation, allowing gradual cutover and instant rollback:

```typescript
// Flags stored in LaunchDarkly, Unleash, or simple Redis key
const useNewOrderService = await flagClient.variation('use-new-order-service', user, false);

if (useNewOrderService) {
  return await newOrderService.placeOrder(request);
} else {
  return await monolithClient.post('/orders', request);
}
```

**Rollback**: Flip the flag — no deployment required. Enable for 1% → 5% → 20% → 100%.

### Data Migration Challenge

The hardest part of Strangler Fig: the monolith and new service cannot share a database (that creates the distributed monolith anti-pattern). Options:

1. **Dual-write**: During transition, write to both old DB and new DB; read from new DB; verify consistency periodically.
2. **Event-based sync**: Monolith emits events (via Outbox) that new service consumes to build its own data store.
3. **DB migration with synchronization**: Migrate data in batch, set up replication for the delta, cut over, turn off sync.

---

## Anti-Corruption Layer (ACL)

When integrating with a legacy system or external service that has a different (often messy) domain model, the ACL provides a translation boundary that prevents the external model from "corrupting" your clean domain model.

```
Your Domain:              ACL Translation:           Legacy System:
Customer {                 CustomerTranslator:         CUST_MASTER {
  id: UUID,               translate(CUST_MASTER)        CUST_ID: string,
  email: string,          → Customer                    CUST_EMAIL: string,
  name: Name,             translateBack(Customer)       FIRST_NM: string,
}                         → CUST_MASTER                 LAST_NM: string,
                                                         ADDR_LINE1: string,
                                                       }
```

```typescript
// ACL implementation — translates without leaking legacy types
class LegacyCrmAdapter implements CustomerRepository {
  async findById(id: CustomerId): Promise<Customer | null> {
    const raw = await this.legacyCrmClient.getCustMaster(id.value);
    if (!raw) return null;
    return this.translator.toDomain(raw); // never return raw legacy types
  }

  async save(customer: Customer): Promise<void> {
    const raw = this.translator.toLegacy(customer);
    await this.legacyCrmClient.updateCustMaster(raw);
  }
}
```

---

## Hexagonal Architecture (Ports and Adapters)

### Core Concept

The application core (domain + use cases) knows nothing about the outside world. It defines **ports** (interfaces). The outside world provides **adapters** (implementations of those ports).

```
┌─────────────────────────────────────────────────────┐
│                    Application Core                  │
│  ┌─────────────────────────────────────────────┐   │
│  │              Domain Model                    │   │
│  │  Entities, Aggregates, Value Objects,        │   │
│  │  Domain Services, Domain Events              │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  Inbound Ports (interfaces the core exposes):        │
│    PlaceOrderUseCase, CancelOrderUseCase             │
│                                                      │
│  Outbound Ports (interfaces the core requires):      │
│    OrderRepository, PaymentGateway, EmailSender      │
└─────────────────────────────────────────────────────┘
         ↑ Inbound Adapters (drive the app)
         │
  HTTP Controller (REST)
  CLI Command Runner
  Kafka Consumer
  gRPC Handler

         ↓ Outbound Adapters (driven by the app)
         │
  PostgresOrderRepository (implements OrderRepository)
  StripePaymentGateway (implements PaymentGateway)
  SendGridEmailSender (implements EmailSender)
  FakePaymentGateway (test double — implements PaymentGateway)
```

### Testability Benefit

Because the core depends only on interfaces, you can test all business logic with in-memory adapters — no database, no HTTP, no external services required.

```typescript
// Pure domain test — no DB, no network
describe('PlaceOrderUseCase', () => {
  it('rejects order when stock is insufficient', async () => {
    const repo = new InMemoryOrderRepository();
    const inventory = new InMemoryInventoryService({ 'SKU-1': 0 });
    const useCase = new PlaceOrderUseCase(repo, inventory);

    await expect(useCase.execute({ sku: 'SKU-1', quantity: 1 }))
      .rejects.toThrow(InsufficientStockError);
  });
});
```

---

## Clean Architecture

Robert Martin's Clean Architecture (2017) arranges code in concentric circles:

```
┌──────────────────────────────────────┐
│          Frameworks & Drivers        │ ← Web, DB, UI (outermost)
│  ┌────────────────────────────────┐  │
│  │    Interface Adapters          │  │ ← Controllers, Gateways, Presenters
│  │  ┌──────────────────────────┐ │  │
│  │  │   Application Use Cases  │ │  │ ← Business rules of the app
│  │  │  ┌────────────────────┐  │ │  │
│  │  │  │    Entities         │  │ │  │ ← Enterprise business rules (innermost)
│  │  │  └────────────────────┘  │ │  │
│  │  └──────────────────────────┘ │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

**The Dependency Rule**: Source code dependencies must point **inward only**. Nothing in an inner circle can know about something in an outer circle.

```typescript
// CORRECT: Use Case depends on Repository INTERFACE (inner)
class PlaceOrderUseCase {
  constructor(private repo: OrderRepository) {} // interface, not implementation
}

// WRONG: Use Case imports a concrete DB adapter (outer)
import { PostgresOrderRepository } from '../../infrastructure/db/PostgresOrderRepository'; // ← violates dependency rule
```

### Clean Architecture vs Hexagonal

They are equivalent in principle. Hexagonal uses "ports and adapters" vocabulary; Clean Architecture uses "use cases, entities, interface adapters, frameworks." Clean Architecture adds the concentric circle diagram and explicit naming of the layers. Choose one vocabulary, be consistent.

---

## Onion Architecture

Similar to Clean Architecture. Layers from core outward:
1. **Domain Model** — entities and value objects
2. **Domain Services** — stateless domain logic
3. **Application Services** — use cases, orchestrates domain services
4. **Infrastructure** — persistence, messaging, external APIs
5. **Presentation / API** — HTTP controllers, CLI

Key difference from layered architecture: all layers depend **inward**, never outward. Infrastructure depends on Application Services (to implement the repositories they define), not the other way around.

---

## When Each Architecture Style Makes Sense

| Style | Use When | Avoid When |
|---|---|---|
| **Layered (N-tier)** | Simple CRUD, small team, well-understood domain | Complex domain logic, need testability without infra |
| **Hexagonal** | Complex domain, multiple delivery mechanisms (HTTP + CLI + queue), TDD-first | Simple apps with one delivery mechanism |
| **Clean Architecture** | Large teams, long-lived codebase, compliance requirements | Prototype/MVP, single developer, deadline-driven |
| **Microservices** | Large org (>50 engineers), independent deployment needed, heterogeneous scaling | Small team, shared database still exists, monolith not yet painful |
| **Modular Monolith** | Growing team, not ready for distributed systems, want clean boundaries without operational overhead | Teams need independent deployment NOW, polyglot required |

---

## Event-Driven Architecture

### Pub/Sub Topology

Publishers emit events without knowledge of subscribers. Subscribers filter events by topic/type.

```
Publishers               Message Broker           Subscribers
OrderService   ──>       Kafka/SNS/EventBridge     InventoryService
PaymentService ──>                                 NotificationService
UserService    ──>                                 AnalyticsService
```

**Event schema best practices**:
- Always include: `eventId` (UUID, for idempotency), `eventType`, `version`, `timestamp`, `correlationId`
- Never include PII in events published to shared topics — use a reference ID and let consumers fetch if needed
- Events are facts about the past — name them in past tense: `OrderPlaced`, not `PlaceOrder`

### Event Mesh (NATS, Solace)

An event mesh extends pub/sub to be cloud and region-agnostic. Events flow dynamically between any publishers and subscribers across any environment. NATS JetStream provides persistent messaging with at-least-once and exactly-once delivery.

### Choreography vs Orchestration Tradeoffs

| Aspect | Choreography | Orchestration |
|---|---|---|
| Coupling | Low (event-based) | Higher (knows orchestrator) |
| Visibility | Hard — flow implicit in events | Easy — flow explicit in orchestrator |
| Failure handling | Each service handles its own compensation | Orchestrator manages compensations |
| SPOF risk | None | Orchestrator is potential SPOF (mitigated by HA) |
| Debugging | Hard — trace distributed event chain | Easier — orchestrator has full state |
| Best for | Simple, stable flows | Complex, long-running, error-prone flows |

---

## CQRS in Production

### Read Model Rebuild Strategy

When the read model projection becomes corrupted or a new projection is needed, you must rebuild:

```
1. Start consuming events from position 0 (beginning of stream)
2. Build new projection into a SHADOW table/index (e.g., orders_feed_v2)
3. Once caught up, verify consistency with sample data
4. Atomic rename: orders_feed → orders_feed_old, orders_feed_v2 → orders_feed
5. Decommission orders_feed_old after validation
```

This is the blue-green deployment pattern applied to projections.

### Handling Eventual Consistency Lag

The most frequent CQRS user complaint: "I just updated X but the UI still shows the old value."

Solutions by impact:
1. **Optimistic local update**: Update client-side state immediately; rollback on API error — works 99% of the time
2. **Version polling**: After write, poll read endpoint until version matches; show "updating..." state
3. **WebSocket push**: When projection is updated, push event to client via WebSocket — immediate consistency for active users
4. **Read-your-writes**: After write, route that user's reads to the write DB for 1-2 seconds; then switch to read model

---

## Event Sourcing in Production

### Aggregate Snapshot Strategy

```typescript
const SNAPSHOT_THRESHOLD = 100; // snapshot every 100 events

async function loadAggregate(aggregateId: string): Promise<Order> {
  const snapshot = await eventStore.getLatestSnapshot(aggregateId);
  const fromVersion = snapshot?.version ?? 0;
  const events = await eventStore.getEvents(aggregateId, fromVersion);

  const order = snapshot ? Order.fromSnapshot(snapshot) : new Order();
  events.forEach((event) => order.apply(event));
  
  if (order.version - fromVersion >= SNAPSHOT_THRESHOLD) {
    await eventStore.saveSnapshot(aggregateId, order.toSnapshot());
  }
  
  return order;
}
```

### Upcasting for Schema Evolution

```typescript
// Events are immutable — handle old versions at read time
class OrderCreatedUpcaster {
  upcast(event: OrderCreatedV1): OrderCreatedV2 {
    return {
      ...event,
      version: 2,
      // V2 added customerId field — default for old events
      customerId: event.userId, // renamed field
    };
  }
}

// Event store applies upcasters during read
const events = await eventStore.getEvents(aggregateId);
const upcasted = events.map(upcasterRegistry.upcast);
```

### Pitfalls to Avoid

1. **Storing derived state in events**: Events should capture intent/facts, not computed values. `OrderTotalUpdated` is a smell; `ItemAdded { price, quantity }` is correct — total is derived.
2. **Long aggregate roots**: An order with 10,000 items will have 10,000+ events — snapshot more aggressively or rethink aggregate boundary.
3. **Cross-aggregate transactions in event sourcing**: Not supported atomically. Use Saga pattern with compensating events.
4. **Missing idempotency**: If event processing is replayed, it must produce the same result. Check `eventId` before applying side effects.

---

## API Versioning Strategies

### URL Path Versioning

```
/api/v1/users/{id}
/api/v2/users/{id}
```
Simple to implement, easy to discover, visible in logs. But couples version to URL — breaks bookmarks, copy-paste links. Recommended for most REST APIs in practice.

### Header Versioning

```http
GET /api/users/123
Accept: application/vnd.myapi.v2+json
```
Cleaner URLs; version is in the content negotiation layer. Harder to test in browser, less discoverable.

### Query Parameter Versioning

```
GET /api/users/123?version=2
```
Easy to test; ugly; caches can be tricked. Avoid for production APIs.

### Sunset Headers

When deprecating an old version, respond with:
```http
Sunset: Sat, 31 Dec 2025 23:59:59 GMT
Deprecation: Mon, 1 Jul 2024 00:00:00 GMT
Link: <https://docs.example.com/api/v2-migration>; rel="deprecation"
```

These are standardized headers (RFC 8594 for Sunset). Automated tooling can detect and alert teams.

---

## Schema Evolution: Avro and Protobuf

### Avro with Schema Registry

Avro requires the schema at both read and write time. Confluent Schema Registry stores schemas and assigns IDs; wire format includes schema ID (4 bytes) + serialized payload.

**Compatibility modes**:
- `BACKWARD`: new schema can read data written with old schema (add optional fields only, never remove required)
- `FORWARD`: old schema can read data written with new schema (remove fields only, never add required)
- `FULL`: both backward and forward compatible (add/remove only optional fields)

```json
// V1 schema
{"type": "record", "name": "User", "fields": [
  {"name": "id", "type": "string"},
  {"name": "email", "type": "string"}
]}

// V2 schema — BACKWARD compatible: added optional field with default
{"type": "record", "name": "User", "fields": [
  {"name": "id", "type": "string"},
  {"name": "email", "type": "string"},
  {"name": "name", "type": ["null", "string"], "default": null}  // optional with null default
]}
```

### Protobuf Compatibility Rules

Protobuf uses field numbers — wire format never includes field names. Rules for backward/forward compatibility:
- NEVER change a field number
- NEVER reuse a field number (use `reserved` keyword for deleted fields)
- Safe: add new optional fields, delete fields (mark as `reserved`), rename fields (field number unchanged)
- Unsafe: change field type, change field from optional to required

```protobuf
syntax = "proto3";

message User {
  string id = 1;
  string email = 2;
  string name = 3;          // new optional field — safe
  reserved 4, 5;            // reserved for deleted fields — prevent reuse
  reserved "phone";         // reserve the name too
}
```

---

## Service Discovery

### DNS-Based (Consul, Route53)

Services register themselves in Consul (or AWS Cloud Map). Clients resolve service names to IPs via DNS. TTL-based; slightly stale under rapid churn.

```bash
# Consul: register a service
curl -X PUT http://localhost:8500/v1/agent/service/register \
  -d '{"Name": "user-service", "Address": "10.0.1.5", "Port": 8080,
       "Check": {"HTTP": "http://10.0.1.5:8080/health", "Interval": "10s"}}'

# Resolve via DNS
dig @127.0.0.1 -p 8600 user-service.service.consul
```

### Client-Side (Eureka, Ribbon — legacy Netflix stack)

Client fetches the service registry, caches it locally, and load-balances itself. Fine-grained control; registry is a potential SPOF.

### Server-Side (ALB, Istio, Envoy)

Client calls a load balancer or sidecar proxy; proxy resolves the target. Simplest for clients; operational complexity moves to the proxy layer.

---

## Sidecar, Ambassador, and Adapter Patterns

### Sidecar

Deployed alongside the main application container in the same pod. Handles cross-cutting concerns without modifying the main app.

```yaml
# Kubernetes: sidecar example (log shipping)
spec:
  containers:
  - name: app
    image: myapp:latest
    volumeMounts:
    - name: logs, mountPath: /var/log/app
  - name: log-shipper  # sidecar
    image: fluentbit:latest
    volumeMounts:
    - name: logs, mountPath: /var/log/app  # shared volume
```

Common sidecar uses: Envoy proxy (Istio), log collectors (Fluent Bit), secrets injectors (Vault Agent), cert managers.

### Ambassador

A specialized sidecar that proxies traffic from the main container to the outside world. Handles retries, circuit breaking, auth. The main app communicates with localhost; the ambassador handles the rest.

### Adapter

Transforms the interface of the main container to match an expected interface. Example: a legacy app that writes logs to a file — an adapter container reads that file and reformats for a modern logging system.

---

## Architecture Decision Records (ADRs)

### When to Write an ADR

- Choosing a technology with long-term lock-in (database, message broker, cloud provider)
- Adopting a new architectural pattern (microservices, event sourcing, CQRS)
- Deciding not to adopt a seemingly obvious solution (and why)
- Any decision that will be questioned in 6 months by someone who wasn't in the room

### ADR Template

```markdown
# ADR-0042: Use PostgreSQL for transactional data storage

## Status
Accepted

## Date
2024-11-15

## Context
We need a relational database for storing user accounts, orders, and payments.
Our team has strong SQL expertise. We have < 5TB of data currently.
We need ACID transactions for payment processing.
We do NOT need horizontal write scaling at current scale (< 10k QPS writes).

## Decision
We will use PostgreSQL 16 as our primary transactional database.

## Consequences
**Positive**:
- ACID transactions for payment flows
- Rich query capabilities (JSON, full-text, window functions)
- Strong operational tooling (pgAdmin, pgBouncer, pg_dump, Logical Replication)
- No licensing cost

**Negative**:
- Vertical scaling has limits (~300-400GB RAM max practical)
- Horizontal write scaling requires sharding (not native — use Citus or rethink)
- Read replicas lag by up to seconds under heavy write load

## Alternatives Considered
- **MySQL 8.0**: Rejected — team lacks expertise; fewer advanced features (window functions, partial indexes, JSONB)
- **MongoDB**: Rejected — our data is relational; ACID across documents requires 4.0+ with significant overhead
- **CockroachDB**: Rejected — adds distributed complexity we don't need at current scale; revisit at 100x growth

## Review Date
2025-Q4 — revisit if write QPS exceeds 5k or storage exceeds 2TB
```

---

## Architecture Anti-Patterns

### Distributed Monolith

Microservices in name only. Services share a database schema, deploy together, or make synchronous calls that create tight temporal coupling. You get all the operational complexity of microservices with none of the independence benefits.

**Signs**: Services cannot be deployed independently; one service going down takes down all others; schema changes require coordinating 8 teams.

**Fix**: Enforce data ownership (each service owns its tables), introduce async communication, enable independent deployment via contract testing.

### Chatty Microservices

A single client operation triggers 15+ synchronous service-to-service calls, each adding latency. Result: 15 × 20ms = 300ms minimum latency, and 15 opportunities for failure.

**Fix**: BFF pattern (aggregate calls at gateway), event-driven architecture (eliminate synchronous fan-out), database denormalization for read models.

### Shared Database Antipattern

Multiple services write to the same database tables. Any schema change requires coordination across all services. The database becomes the hidden coupling point.

```
# ANTI-PATTERN: Both services write to orders table
OrderService  ─────┐
                   ├──> orders table (shared)
ShippingService ───┘

# CORRECT: Each service owns its data; sync via events
OrderService ──> orders_db ──> OrderPlaced event ──> ShippingService ──> shipping_db
```

### Synchronous Coupling Chains

Service A calls B synchronously, B calls C, C calls D. Total latency = sum of all hops + all failure surfaces compound. If D is slow, A is slow. If D is down, A fails.

**Fix**: Async communication with message queues; caching; eventual consistency where real-time consistency isn't required.

---

## Anti-Hallucination Protocol

**Verify before asserting:**
1. Strangler Fig pattern coined by Martin Fowler in 2004 blog post "StranglerFigApplication" — not by Eric Evans or the DDD book
2. Robert Martin's Clean Architecture book was published in 2017 — verify specific claims against the book content, not summaries
3. Avro compatibility modes (BACKWARD, FORWARD, FULL) are defined in the Confluent Schema Registry docs — verify exact behavior at `docs.confluent.io/platform/current/schema-registry/avro.html`
4. Protobuf field numbers: the rule "never change a field number" is from Google's official proto3 language guide at `protobuf.dev/programming-guides/proto3/` — verify there
5. Conway's Law (1967): "Organizations which design systems are constrained to produce designs which are copies of the communication structures of those organizations." — Melvin Conway, not Mike Conway
6. RFC 8594 (Sunset header) was published in 2019 — verify the RFC number and sunset header field name at `rfc-editor.org/rfc/rfc8594`
7. Consul DNS port is 8600 by default — not 8500 (that's the HTTP API port); always verify port numbers against official documentation
8. Domain Events vs Integration Events: this distinction is from Udi Dahan's writing and later popularized in the DDD community — it is NOT an official DDD term from Evans' "Domain-Driven Design" book (2003)
9. The Ambassador, Sidecar, and Adapter patterns are from the "Designing Distributed Systems" book by Brendan Burns (2018) — not from the Gang of Four (1994)
10. Debezium Outbox pattern: requires `wal_level = logical` in PostgreSQL. This must be set in `postgresql.conf` before starting Debezium — verify against Debezium PostgreSQL connector docs

---

## Self-Review Checklist

Before delivering any architecture recommendation, verify:

- [ ] **Tradeoffs named**: Every pattern recommendation lists what you gain AND what you lose — no free lunches asserted
- [ ] **Current scale justified**: The architecture is appropriate for current + 2-year projected scale, not overengineered for theoretical future
- [ ] **Team size considered**: Microservices only if team size and org structure can support independent ownership
- [ ] **Data ownership clear**: Every service owns its data; no shared database tables between services
- [ ] **Consistency model stated**: What consistency guarantees does the architecture provide for each data flow?
- [ ] **Failure modes addressed**: What happens when service X fails? Is there retry, circuit break, fallback, or graceful degradation?
- [ ] **Migration path defined**: If migrating from existing system, phased plan with rollback points at each phase
- [ ] **ADR written or referenced**: Non-obvious decisions documented with context, alternatives considered, consequences
- [ ] **Event schema versioned**: All integration events have a `version` field; schema evolution strategy defined
- [ ] **Observability included**: Distributed tracing correlation IDs, structured logging, metrics for every service boundary
- [ ] **Anti-corruption layer**: Any integration with legacy or external systems goes through a translation layer
- [ ] **Idempotency at every boundary**: All message consumers and API endpoints can safely handle duplicate requests
- [ ] **No distributed monolith**: Services can be deployed independently; no shared DB schema between services
- [ ] **Backward compatibility**: API changes are additive; breaking changes go through versioning + deprecation cycle
