---
name: god-api-design
description: "God-level API design skill covering REST (Richardson Maturity Model, HTTP semantics, status codes, versioning, pagination, filtering, HATEOAS), GraphQL (schema design, resolvers, N+1 problem, DataLoader, subscriptions, federation), gRPC (Protocol Buffers, service definitions, streaming types, deadlines, interceptors), AsyncAPI and event-driven API design, API security (OAuth 2.0, OIDC, JWT, API keys, mTLS), API contracts (OpenAPI 3.1, Protobuf), API testing (contract testing with Pact, integration testing, fuzz testing), API gateway patterns, rate limiting, idempotency, and API versioning strategies. A bad API is a permanent scar on an organization — it cannot be unshipped."
metadata:
  version: "1.0.0"
---

# God-Level API Design

> A bad API is a permanent scar on an organization. It cannot be unshipped. Every decision you make at design time will be paid for in maintenance costs, client rewrites, and support tickets for years. Design like it matters — because it does.

## Researcher-Warrior Mindset

You are not here to make something that "works." You are here to make something that is correct, durable, and comprehensible to every engineer who will ever interact with it. Before you write a single endpoint, you read the spec. You read the RFC. You look at what Stripe, Twilio, and GitHub did and why. Then you make deliberate decisions, not cargo-culted ones.

**Anti-hallucination rules for this domain:**
- Never invent HTTP status codes. Only use codes defined in RFC 7231, RFC 6585, RFC 4918, and RFC 8470.
- Never invent OAuth 2.0 flows. The four canonical flows are defined in RFC 6749. PKCE is in RFC 7636.
- Never describe JWT validation without listing ALL required checks (algorithm, expiry, issuer, audience, signature).
- When citing a spec (OpenAPI, JSON:API, RFC 7807), cite the actual spec version number.
- If you are unsure whether a behavior is defined or implementation-specific, say so explicitly.

---

## 1. Richardson Maturity Model

The Richardson Maturity Model (RMM) describes four levels of REST API maturity. Most APIs call themselves REST but live at Level 1 or Level 2. True REST (Level 3 with HATEOAS) is rarely implemented but worth understanding.

### Level 0 — The Swamp of POX (Plain Old XML / JSON)
One URI, one HTTP method (always POST), all operations encoded in the body. This is SOAP. This is XML-RPC. This is wrong.

```http
POST /api HTTP/1.1
Content-Type: application/json

{"action": "getUser", "id": "123"}
```

Problem: no HTTP semantics, no caching, no idempotency, no discoverability.

### Level 1 — Resources
Multiple URIs, but still only POST. Resources exist as concepts but HTTP verbs carry no meaning.

```http
POST /users/123 HTTP/1.1
{"action": "update", "name": "Alice"}
```

Better: resources are named. Worse: still ignoring the entire HTTP protocol.

### Level 2 — HTTP Verbs + Status Codes (Where most "REST" APIs live)
Correct use of GET/POST/PUT/PATCH/DELETE. Correct status codes. This is the minimum acceptable level for production APIs.

```http
GET /users/123 HTTP/1.1
→ 200 OK

PATCH /users/123 HTTP/1.1
{"name": "Alice"}
→ 200 OK

DELETE /users/123 HTTP/1.1
→ 204 No Content
```

### Level 3 — HATEOAS (Hypermedia As The Engine Of Application State)
Responses include links to valid next actions. Clients navigate the API by following links, not by hardcoding URLs. Used by GitHub's v3 API (`Link` headers for pagination), HAL, and JSON:API.

```json
{
  "id": "123",
  "name": "Alice",
  "_links": {
    "self": {"href": "/users/123"},
    "orders": {"href": "/users/123/orders"},
    "deactivate": {"href": "/users/123/deactivate", "method": "POST"}
  }
}
```

Real-world verdict: Level 3 is theoretically correct but operationally rare. Most mature APIs (Stripe, Twilio) live at Level 2 with excellent documentation. Don't let perfect be the enemy of good — but understand what you are trading away.

---

## 2. HTTP Semantics — Correct Method Use

| Method  | Safe | Idempotent | Body Allowed | Common Use |
|---------|------|------------|--------------|------------|
| GET     | Yes  | Yes        | No (technically allowed, discouraged) | Retrieve resource |
| HEAD    | Yes  | Yes        | No           | Check existence/metadata without body |
| OPTIONS | Yes  | Yes        | No           | CORS preflight, capability discovery |
| POST    | No   | No         | Yes          | Create resource, trigger action |
| PUT     | No   | Yes        | Yes          | Replace resource entirely |
| PATCH   | No   | No*        | Yes          | Partial update |
| DELETE  | No   | Yes        | No (allowed, discouraged) | Delete resource |

*PATCH idempotency depends on the patch document format. JSON Patch (RFC 6902) operations like `add` may not be idempotent. JSON Merge Patch (RFC 7396) typically is.

**Safe** means the request has no intended side effects. Clients and intermediaries (proxies, CDNs) can cache and prefetch safe requests.

**Idempotent** means calling it N times produces the same result as calling it once. Critical for retry logic. PUT /users/123 with the same body is safe to retry. POST /orders creates a new order each time — use idempotency keys.

**Misuse patterns to eliminate:**
- `GET /users/delete/123` — never encode actions in GET URLs
- `POST /users/123/update` — PATCH exists for a reason
- `POST /getUser` — you have GET, use it
- Using PUT when you mean PATCH (PUT replaces the entire resource; PATCH modifies fields)

---

## 3. HTTP Status Codes — Full Production Reference

### 2xx Success

| Code | Name | When to Use |
|------|------|-------------|
| 200 | OK | Successful GET, PATCH, PUT with response body |
| 201 | Created | Successful POST that created a resource. Include `Location` header pointing to the new resource. |
| 202 | Accepted | Request received and will be processed asynchronously. Return a job/task resource URL. |
| 204 | No Content | Successful DELETE or action with no response body. Do NOT return 200 with empty body. |
| 206 | Partial Content | Range request fulfilled (file downloads, chunked responses) |
| 207 | Multi-Status | Batch operation where individual items have different statuses. Body contains per-item status. |

**202 pattern** (async operations):
```json
HTTP/1.1 202 Accepted
Location: /jobs/abc123

{
  "job_id": "abc123",
  "status": "pending",
  "status_url": "/jobs/abc123"
}
```

**207 pattern** (batch imports):
```json
HTTP/1.1 207 Multi-Status
{
  "results": [
    {"id": "1", "status": 200, "data": {...}},
    {"id": "2", "status": 422, "error": {"code": "invalid_email"}}
  ]
}
```

### 3xx Redirection

| Code | Name | When to Use |
|------|------|-------------|
| 301 | Moved Permanently | Resource has moved. Clients SHOULD update bookmarks. Method MAY change to GET. |
| 302 | Found | Temporary redirect. Method MAY change to GET. Prefer 307 or 308 for APIs. |
| 304 | Not Modified | Conditional GET — resource unchanged since `If-Modified-Since` / `If-None-Match`. |
| 307 | Temporary Redirect | Redirect preserving the original HTTP method. Use for API temporary redirects. |
| 308 | Permanent Redirect | Redirect preserving method, permanently. Use for API moves that preserve POST/PUT semantics. |

### 4xx Client Errors

| Code | Name | When to Use |
|------|------|-------------|
| 400 | Bad Request | Malformed request syntax, invalid JSON. Generic catch-all for bad input. |
| 401 | Unauthorized | Missing or invalid authentication credentials. Include `WWW-Authenticate` header. |
| 403 | Forbidden | Authenticated but not authorized. Don't return 404 to hide resource existence unless privacy requires it. |
| 404 | Not Found | Resource does not exist. Also used to hide forbidden resources when privacy is required. |
| 405 | Method Not Allowed | HTTP method not supported on this endpoint. Include `Allow` header with supported methods. |
| 409 | Conflict | State conflict — optimistic locking failure, duplicate resource creation, constraint violation. |
| 410 | Gone | Resource existed but is permanently deleted. Use over 404 when the deletion is intentional and permanent. |
| 415 | Unsupported Media Type | Client sent Content-Type the server can't process. |
| 422 | Unprocessable Entity | Request is well-formed but semantically invalid (validation errors, business rule violations). |
| 429 | Too Many Requests | Rate limit exceeded. MUST include `Retry-After` header. |

**409 vs 422:**
- 409: The request is valid but conflicts with current state ("user with this email already exists")
- 422: The request itself has semantic errors ("email field is not a valid email format")

### 5xx Server Errors

| Code | Name | When to Use |
|------|------|-------------|
| 500 | Internal Server Error | Unhandled exception. Never leak stack traces in production. |
| 502 | Bad Gateway | Upstream service returned invalid response. |
| 503 | Service Unavailable | Server is overloaded or down for maintenance. Include `Retry-After`. |
| 504 | Gateway Timeout | Upstream service timed out. |

**503 pattern** (maintenance/overload):
```http
HTTP/1.1 503 Service Unavailable
Retry-After: 120
Content-Type: application/problem+json

{
  "type": "https://api.example.com/errors/service-unavailable",
  "title": "Service Unavailable",
  "detail": "The service is temporarily unavailable. Please retry after 120 seconds."
}
```

---

## 4. Error Response Format — RFC 7807 Problem Details

Never invent your own error format. RFC 7807 (Problem Details for HTTP APIs) is the standard. Use it.

```json
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/problem+json

{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "The request body contains invalid fields.",
  "instance": "/requests/abc123",
  "errors": [
    {
      "field": "email",
      "message": "Must be a valid email address",
      "code": "invalid_format"
    },
    {
      "field": "age",
      "message": "Must be at least 18",
      "code": "below_minimum"
    }
  ]
}
```

Required fields: `type` (URI identifying the error type), `title` (human-readable), `status` (HTTP status code as integer).

Optional but recommended: `detail` (specific instance detail), `instance` (URI of the specific occurrence), domain-specific extension members.

The `type` URI SHOULD be a real URL that resolves to documentation about the error. This forces you to document your errors.

---

## 5. REST Resource Design

### Naming Rules
- **Nouns, not verbs**: `/users`, not `/getUsers`
- **Plural**: `/users`, not `/user`
- **Lowercase with hyphens**: `/user-profiles`, not `/userProfiles`
- **Hierarchy for containment**: `/users/123/orders/456`
- **Avoid deep nesting beyond 2 levels**: `/users/123/orders` is fine. `/users/123/orders/456/items/789/details` is a design smell — create a flat resource with filtering instead.

### Filtering, Sorting, Pagination

**Filtering:**
```
GET /orders?status=shipped&created_after=2024-01-01
GET /orders?filter[status]=shipped&filter[user_id]=123   ← JSON:API style
```

Pick a consistent convention and document it. JSON:API's `filter[field]` is self-documenting.

**Sorting:**
```
GET /users?sort=created_at          ← ascending
GET /users?sort=-created_at         ← descending (prefix minus)
GET /users?sort=-created_at,name    ← multiple fields
```

**Pagination — Cursor vs Offset:**

Offset pagination (`?page=3&per_page=20`):
- Simple to implement
- Breaks when records are inserted/deleted during pagination (items skip or duplicate)
- O(N) database query cost as page number increases (OFFSET 10000 scans 10000 rows)
- Never use for large, frequently-changing datasets

Cursor pagination (`?after=eyJpZCI6MTIzfQ==`):
- Cursor is an opaque encoded pointer to the last item seen (typically base64-encoded JSON)
- Stable — insertions/deletions don't corrupt the page
- O(1) with proper index — WHERE id > cursor_id LIMIT 20
- No random access (can't jump to page 50) — acceptable for most use cases
- **Use cursor pagination for any dataset over ~10,000 rows or any real-time feed**

Cursor response pattern:
```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTIzfQ==",
    "prev_cursor": "eyJpZCI6MTAwfQ==",
    "has_next": true,
    "has_prev": true
  }
}
```

**Partial Response (Field Selection):**
```
GET /users/123?fields=id,name,email
```
Reduces payload size. Important for mobile clients. GraphQL solves this more elegantly — one reason to reach for GraphQL when field-selection is a first-class requirement.

---

## 6. API Versioning Strategies

### URI Versioning (`/v1/`)
```
https://api.example.com/v1/users
https://api.example.com/v2/users
```
Pros: visible in logs and URLs, easy to route, easy to document.
Cons: version is not really a resource property — purists object. URL bookmarks break on version change.
**Verdict: Industry standard. Use this. Stripe, Twilio, GitHub all use it.**

### Header Versioning (`API-Version: 2024-01-01`)
```http
GET /users HTTP/1.1
API-Version: 2024-01-01
```
Stripe uses date-based versioning for granular rollout. Clean URLs. Harder to test in browser.

### Content-Type Versioning (`application/vnd.example.v2+json`)
```http
Accept: application/vnd.example.v2+json
```
RFC-compliant. Elegant. Nobody does it in practice because it's painful to test and implement.

### Strategy Decision
- **New public API**: Use URI versioning (`/v1/`). Simple, visible, debuggable.
- **Mature API with many clients**: Consider date-based header versioning (Stripe model) for granular compatibility.
- **Never use query parameter versioning** (`?version=2`) — version parameters pollute the query namespace and are hard to enforce at the gateway level.

---

## 7. OpenAPI 3.1 — Contract-First Design

Write the OpenAPI spec before writing code. The spec is the contract. Code implements the contract. Never generate the spec from code — generated specs are implementation documentation, not API contracts.

```yaml
openapi: "3.1.0"
info:
  title: Orders API
  version: "1.0.0"
paths:
  /orders:
    post:
      operationId: createOrder
      summary: Create a new order
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateOrderRequest'
            examples:
              standard:
                value:
                  user_id: "usr_123"
                  items: [{product_id: "prod_456", quantity: 2}]
      responses:
        "201":
          description: Order created
          headers:
            Location:
              schema:
                type: string
                format: uri
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Order'
        "422":
          $ref: '#/components/responses/ValidationError'
        "429":
          $ref: '#/components/responses/RateLimitError'
      security:
        - BearerAuth: []
components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
  schemas:
    CreateOrderRequest:
      type: object
      required: [user_id, items]
      properties:
        user_id:
          type: string
          pattern: "^usr_[a-zA-Z0-9]+$"
        items:
          type: array
          minItems: 1
          items:
            $ref: '#/components/schemas/OrderItem'
```

**Discriminator for polymorphism:**
```yaml
PaymentMethod:
  oneOf:
    - $ref: '#/components/schemas/CardPayment'
    - $ref: '#/components/schemas/BankTransfer'
  discriminator:
    propertyName: type
    mapping:
      card: '#/components/schemas/CardPayment'
      bank_transfer: '#/components/schemas/BankTransfer'
```

---

## 8. GraphQL — Schema-First Design

### The N+1 Problem and DataLoader

The N+1 problem: fetching a list of N users, then making N separate database queries to fetch each user's orders.

```javascript
// BAD — N+1 queries
const resolvers = {
  Query: {
    users: () => db.users.findAll(),          // 1 query
  },
  User: {
    orders: (user) => db.orders.findByUserId(user.id)  // N queries, one per user
  }
};
```

DataLoader solution (Facebook's open-source library):
```javascript
// GOOD — batched queries
const orderLoader = new DataLoader(async (userIds) => {
  const orders = await db.orders.findByUserIds(userIds);  // 1 query for all
  return userIds.map(id => orders.filter(o => o.userId === id));
});

const resolvers = {
  User: {
    orders: (user) => orderLoader.load(user.id)  // batched automatically
  }
};
```

DataLoader batches all calls within a single event loop tick, then issues one query. This reduces N+1 to 2 queries total.

### Schema Design Principles
- Design for the client's data needs, not for the database schema
- Use connections for paginated lists (Relay Cursor Connections Specification)
- Mutations: name them as actions (`createUser`, `updateUserEmail`, `deleteOrder`)
- Never expose database IDs directly — use opaque global IDs

### Schema Stitching vs Federation
- **Schema Stitching**: manually combining multiple GraphQL schemas in a gateway. Complex, fragile, largely superseded.
- **Apollo Federation**: each service owns its subgraph schema, a router composes them. Services can extend each other's types. This is the correct architecture for multi-service GraphQL.

### Subscriptions
Use WebSocket transport (graphql-ws protocol). Design subscriptions to be additive (new events only, not full state replacement). Authentication in subscriptions goes in the connection init payload, not in HTTP headers.

### Persisted Queries
Store queries server-side by hash. Client sends hash instead of full query string. Reduces payload size and prevents query injection attacks. Required for production GraphQL APIs at scale.

---

## 9. gRPC — Protocol Buffers and Service Design

### Proto File Design
```protobuf
syntax = "proto3";
package orders.v1;
option go_package = "github.com/example/orders/v1;ordersv1";

service OrderService {
  // Unary — one request, one response
  rpc GetOrder(GetOrderRequest) returns (Order);
  
  // Server streaming — one request, stream of responses
  rpc ListOrders(ListOrdersRequest) returns (stream Order);
  
  // Client streaming — stream of requests, one response
  rpc CreateBulkOrders(stream CreateOrderRequest) returns (BulkCreateResponse);
  
  // Bidirectional streaming — stream both ways
  rpc ProcessOrders(stream OrderEvent) returns (stream OrderResult);
}

message GetOrderRequest {
  string order_id = 1;  // field numbers are permanent — never reuse
}
```

**Field number rules**: Field numbers 1-15 use 1 byte in varint encoding. Use them for frequently occurring fields. Never reuse field numbers after a field is deleted — mark with `reserved`.

### Deadlines vs Timeouts
gRPC uses deadlines (absolute time), not timeouts (relative duration). Always set deadlines on every RPC call. No deadline = potentially infinite wait.

```go
ctx, cancel := context.WithDeadline(context.Background(), time.Now().Add(5*time.Second))
defer cancel()
resp, err := client.GetOrder(ctx, req)
```

### Error Codes
gRPC uses `google.rpc.Status` with canonical error codes. Map these to HTTP correctly:
- `NOT_FOUND` → 404
- `ALREADY_EXISTS` → 409
- `INVALID_ARGUMENT` → 400
- `UNAUTHENTICATED` → 401
- `PERMISSION_DENIED` → 403
- `RESOURCE_EXHAUSTED` → 429
- `UNAVAILABLE` → 503
- `INTERNAL` → 500

### Interceptors
Use interceptors (middleware) for cross-cutting concerns — never put them in handler logic:
- Authentication: validate JWT/mTLS in interceptor, inject user into context
- Logging: log request/response with trace_id
- Metrics: record RPC latency, error rate per method
- Retry: implement retry with exponential backoff in client interceptor

### Reflection
Enable gRPC reflection in non-production environments. Tools like `grpcurl` and `grpc-ui` use reflection for debugging without needing .proto files.

---

## 10. API Security

### OAuth 2.0 Flows — Use the Right One
| Flow | Use Case | PKCE Required |
|------|----------|---------------|
| Authorization Code + PKCE | Web apps, mobile apps, SPAs | Yes (RFC 7636) |
| Client Credentials | Machine-to-machine (M2M) | No |
| Device Code | CLI tools, smart TVs | No |

Authorization Code Flow was always designed with PKCE for mobile. The "implicit flow" is deprecated. Never use it.

Client Credentials: the service authenticates with `client_id` + `client_secret`. Token goes in `Authorization: Bearer <token>`. Rotate secrets regularly. Store secrets in a vault (HashiCorp Vault, AWS Secrets Manager), never in code.

### JWT Validation — All Checks Required
When validating a JWT, ALL of the following checks are mandatory. Missing any one is a security vulnerability:

1. **Algorithm**: Verify `alg` header matches expected algorithm. Reject `none`. Reject RS256 tokens when you expect HS256 (algorithm confusion attack).
2. **Signature**: Verify signature against the correct key (public key for RS256, shared secret for HS256).
3. **Expiry (`exp`)**: Reject tokens past expiry. Allow small clock skew (≤ 5 minutes).
4. **Not Before (`nbf`)**: Reject tokens before their valid time.
5. **Issuer (`iss`)**: Verify matches expected issuer URL.
6. **Audience (`aud`)**: Verify your service's identifier is in the audience claim.
7. **JWKS refresh**: If using JWKS endpoint, cache keys but refresh on unknown `kid`.

### API Key Anti-patterns
- Never accept API keys in URL query parameters — they appear in server logs and browser history
- API keys go in `Authorization: ApiKey <key>` or `X-API-Key: <key>` headers
- Hash stored API keys (show the key only once at creation; store SHA-256 hash)
- Scope API keys to minimum required permissions

### mTLS for Service-to-Service
Mutual TLS (mTLS): both client and server present certificates. Correct for internal service-to-service APIs. Certify with a private CA (cert-manager in Kubernetes, AWS ACM Private CA). Each service gets its own certificate with its service name as the CN or SAN.

---

## 11. Rate Limiting

### Algorithms
**Token Bucket**: bucket fills at a fixed rate up to a maximum. Each request costs tokens. Allows bursts up to bucket size. Redis implementation: store `{tokens, last_refill_time}`.

**Leaky Bucket**: requests enter a queue (the "bucket"), processed at a fixed rate. Smooths traffic absolutely. No burst allowed. Harder to implement correctly.

**Sliding Window Log**: store timestamp of each request. Count requests in the window. Accurate but high memory use.

**Sliding Window Counter**: approximate sliding window using two adjacent fixed windows, weighted by time fraction. Efficient. Acceptable approximation for most use cases.

### Rate Limit Response Headers
Always return these headers on every response, not just on 429:
```http
RateLimit-Limit: 1000
RateLimit-Remaining: 487
RateLimit-Reset: 1704067200
Retry-After: 3600          ← only on 429
```

(IETF draft `draft-ietf-httpapi-ratelimit-headers` standardizes these headers. Use this naming.)

### Strategy
- Rate limit per authenticated user, not per IP (IPs are shared behind NAT)
- Different limits per endpoint (read vs write, cheap vs expensive)
- Rate limit at the API gateway, not in application code
- Provide a way for clients to check their rate limit status without consuming quota

---

## 12. Idempotency Keys

POST endpoints are not idempotent by default. For any POST that creates a resource or triggers a side effect (payment, email send, order creation), implement idempotency keys.

Pattern (from Stripe):
1. Client generates a unique key (UUID v4) and sends it in `Idempotency-Key: <uuid>` header.
2. Server checks Redis/DB for this key. If found and request completed, return cached response.
3. If key exists but request is in-flight, return 409 with "request in progress."
4. If key not found, process request, store key+response in Redis with TTL (e.g., 24 hours).
5. Return response with `Idempotency-Key` echoed back.

```http
POST /payments HTTP/1.1
Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{"amount": 5000, "currency": "usd", "card": "tok_visa"}
```

Storage key: `idempotency:{endpoint}:{key}` to scope keys per operation type.

---

## 13. Contract Testing with Pact

Integration tests verify that your service works. Contract tests verify that your service works **with a specific consumer**. These are different things.

**Consumer-Driven Contracts (CDC)**: The consumer defines what it expects from the provider. The provider verifies it can satisfy those expectations. On every build.

Pact workflow:
1. Consumer team writes Pact tests defining expected interactions (request → response pairs).
2. Pact generates a JSON "pact file" (the contract).
3. Contract is published to PactFlow (or a pact broker).
4. Provider runs pact verification against the contract.
5. If verification fails, the provider cannot deploy.

Why integration tests alone are insufficient: integration tests verify that services work together **right now**, in **your** test environment. Contract tests verify that the consumer's **assumptions** about the provider are met — catching breaking changes before deployment.

---

## 14. API Gateway Patterns

**What API gateways do:**
- TLS termination
- Authentication (JWT validation, API key verification)
- Rate limiting
- Request routing
- Load balancing
- Request/response transformation (with caution)
- Logging and metrics

**What API gateways do NOT do:**
- Business logic — the moment you put if-else business logic in the gateway, you have made the gateway unmaintainable
- Complex data aggregation — that belongs in a BFF (Backend for Frontend) service
- Authorization beyond coarse-grained role checks — fine-grained authz belongs in the service

**Gateway products:**
- **Kong**: OSS, plugin-based, highly extensible, DB-less mode for GitOps deployment
- **AWS API Gateway**: fully managed, native Lambda integration, can be expensive at scale, limited custom plugin support
- **Apigee** (Google): enterprise feature set, strong analytics, complex to operate
- **nginx/Envoy**: raw power, full control, you write the config

**Don't put business logic in the gateway.** Repeat this. Tattoo it somewhere.

---

## 15. Backward Compatibility

A production API is a promise to every client that exists today and every client that will be written tomorrow. Breaking changes are a contract violation.

### Additive Changes (Safe)
- New optional request fields
- New response fields (clients must ignore unknown fields)
- New enum values (warn clients to handle unknown enums)
- New endpoints
- New optional headers

### Breaking Changes (Never in an existing version)
- Removing fields from responses
- Renaming fields
- Changing field types
- Changing semantics of existing fields (even with the same type)
- Removing enum values
- Changing required fields to required with different validation

### Deprecation Cycle
1. Announce deprecation with timeline (minimum 6 months for public APIs)
2. Return `Deprecation` header and `Sunset` header on deprecated endpoints
3. Monitor usage — don't sunset until traffic drops to zero or deadline arrives
4. Send direct notification to affected clients before removal

```http
Deprecation: Sun, 01 Jan 2025 00:00:00 GMT
Sunset: Sun, 01 Jul 2025 00:00:00 GMT
Link: <https://developer.example.com/migration-guide>; rel="successor-version"
```

---

## Cross-Domain Connections

- **API design + Security**: Every public API endpoint is an attack surface. Rate limiting, authentication, and input validation are not afterthoughts — they are load-bearing walls.
- **API design + Distributed systems**: Idempotency keys, async patterns (202 + polling), and pagination choices are distributed systems problems wearing API clothes.
- **gRPC + Kubernetes**: gRPC's HTTP/2 multiplexing doesn't work well with traditional Kubernetes L4 load balancers. Use a service mesh (Istio, Linkerd) or gRPC-aware L7 load balancer.
- **GraphQL + Performance**: GraphQL's flexibility (arbitrary queries) is also its security risk. Always implement query depth limiting, query complexity analysis, and rate limiting on query complexity, not just request count.
- **Contract testing + CI/CD**: Contract tests in CI are a forcing function for honest API evolution. Pact verification failures catch breaking changes before they reach production.

---

## Self-Review Checklist (20 Items)

Before shipping any API design:

- [ ] 1. Every endpoint uses the correct HTTP method (no verbs in URLs, no GET for mutations)
- [ ] 2. Status codes are correct and consistent (not just 200/400/500)
- [ ] 3. Error responses follow RFC 7807 Problem Details format
- [ ] 4. Resource naming uses nouns, plural, lowercase, hyphenated
- [ ] 5. Pagination is cursor-based for any collection over ~1,000 items
- [ ] 6. Filtering uses a consistent convention documented in the spec
- [ ] 7. OpenAPI 3.1 spec is written contract-first, not generated from code
- [ ] 8. All schemas have required fields, types, formats, and examples
- [ ] 9. Authentication scheme is specified on every endpoint
- [ ] 10. Rate limiting is implemented with correct headers (RateLimit-Limit, RateLimit-Remaining, RateLimit-Reset)
- [ ] 11. POST endpoints that create resources or trigger side effects have idempotency key support
- [ ] 12. All 4xx errors have actionable error messages (not just "bad request")
- [ ] 13. Breaking changes are not present in existing versions — only additive changes
- [ ] 14. Deprecated endpoints return Deprecation and Sunset headers
- [ ] 15. JWT validation enforces algorithm, signature, expiry, issuer, and audience
- [ ] 16. API keys are accepted only in headers, never in query parameters
- [ ] 17. GraphQL schemas have query depth limiting and complexity analysis configured
- [ ] 18. gRPC methods have deadlines documented in the proto comments
- [ ] 19. Contract tests exist for all consumer-provider relationships
- [ ] 20. The API can evolve without breaking existing clients — verified by listing what breaking changes would look like and confirming none are present
---
