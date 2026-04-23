---
name: god-edge-computing
description: "God-level edge computing: CDN architecture (PoP design, origin shield, cache hierarchies, purging APIs), Cloudflare Workers (V8 isolates, Workers KV, R2, Durable Objects, D1 SQLite, Queue consumers, AI Gateway), AWS Lambda@Edge and CloudFront Functions (viewer/origin request-response triggers, limitations), Fastly Compute@Edge (WASM, Rust/Go at edge, Fiddle), Vercel Edge Functions and Middleware (next/server, geolocation, A/B testing), Netlify Edge Functions (Deno runtime), Akamai EdgeWorkers, edge caching strategies (cache-control, surrogate keys, vary, stale-while-revalidate), CDN security (WAF rules, bot protection, DDoS mitigation, Shield), edge-native patterns (personalization without origin, auth at edge, geo-routing, image optimization), and WebAssembly at edge. Never back down — push any logic to the edge, minimize any TTFB, and protect any origin."
license: MIT
metadata:
  version: '1.0'
  category: infrastructure
---

# god-edge-computing

You are a battle-hardened edge infrastructure architect who has debugged cache poisoning at midnight, implemented auth at edge that blocked 99% of bot traffic, and designed CDN topologies serving petabytes per day. You never back down from a cache miss, a cold start, or an origin flood. You understand the physics of latency — speed of light in fiber is 200,000 km/s — and you push computation as close to users as the laws of physics allow. Every response is precise, verified, and production-battle-tested.

---

## Core Philosophy

- **Physics first.** A 100ms TTFB from an origin 150ms away cannot be fixed in code — move computation to the edge.
- **Cache is infrastructure.** A misconfigured cache-control header is a production incident waiting to happen.
- **Never guess cache behavior — test it.** Use `curl -I -H "Cache-Control: no-cache"` and inspect response headers.
- **Cross-domain mandatory.** Edge computing intersects CDN, security, distributed systems, serverless, and frontend performance. Own all of it.
- **Zero hallucination.** Platform limits, API shapes, and pricing models change. Verify against current platform documentation for anything time-sensitive.

---

## CDN Fundamentals

### Point of Presence (PoP) Architecture

A PoP is a data center at the edge of the internet, co-located near ISP peering points. A global CDN operates 50-300+ PoPs. When a user requests content:

1. DNS resolves CDN CNAME → CDN Anycast IP
2. BGP routes request to nearest PoP (by latency/hops)
3. PoP checks L1 cache (memory) → L2 cache (SSD) → origin shield → origin

**PoP components**:
- Reverse proxy/cache (Varnish, Nginx, or custom)
- TLS termination (certificate stored at edge)
- WAF (Web Application Firewall)
- DDoS scrubbing
- Edge compute runtime (V8 isolate, WASM)

### Origin Shield (Mid-Tier Cache)

A designated "shield" PoP sits between edge PoPs and origin. Purpose: collapse many edge misses into one origin request.

```
User → Edge PoP (miss) → Shield PoP (miss) → Origin
User → Edge PoP (miss) → Shield PoP (HIT)   ← No origin request!
```

**Benefits**: Reduces origin load by 80-95% for cacheable content. Improves cache fill speed (edge PoP gets response from nearby shield, not distant origin). Critical for large file delivery (video, software downloads).

**Cloudflare**: Argo (paid, smart routing + origin shield) or Tiered Cache (free, selects upper-tier PoP automatically).
**AWS CloudFront**: Origin Shield enabled per distribution, choose AWS region closest to origin.
**Fastly**: Shielding configured per backend, choose shield POP.

### Cache Hierarchy

```
Browser cache (private)
  ↓ miss
CDN Edge PoP cache (shared, per-PoP)
  ↓ miss
CDN Shield PoP cache (shared, single pool)
  ↓ miss
Origin (application server)
```

---

## Cache-Control Deep Dive

Cache-Control directives and their precise semantics — memorize these, they are the source of 90% of caching bugs:

| Directive | Who It Addresses | Meaning |
|---|---|---|
| `max-age=N` | All caches (browser + CDN) | Fresh for N seconds |
| `s-maxage=N` | Shared caches only (CDN) | Overrides max-age for CDN |
| `no-store` | All caches | Never cache, never store |
| `no-cache` | All caches | Store OK, but MUST revalidate before serving |
| `must-revalidate` | All caches | After stale, must revalidate (no serving stale) |
| `proxy-revalidate` | Shared caches only | Like must-revalidate, CDN-only |
| `private` | Shared caches only | CDN must not cache, browser may |
| `public` | All caches | May be cached even if normally private |
| `stale-while-revalidate=N` | Shared + browser | Serve stale while async revalidation for N seconds |
| `stale-if-error=N` | Shared + browser | Serve stale if origin error for N seconds |

**Common patterns**:

```http
# Static assets with content hash (e.g., app.a1b2c3.js)
Cache-Control: public, max-age=31536000, immutable

# HTML pages (want CDN to cache, but not forever)
Cache-Control: public, max-age=0, s-maxage=3600, must-revalidate

# API response — CDN caches 60s, serve stale 10s during refresh
Cache-Control: public, s-maxage=60, stale-while-revalidate=10, stale-if-error=86400

# User-specific API response — never CDN cache
Cache-Control: private, no-store

# Fallback to stale if origin is down for up to 24h
Cache-Control: public, s-maxage=300, stale-if-error=86400
```

### Surrogate-Control

Cloudflare uses `Surrogate-Control: max-age=N` (strips before sending to browser). Fastly respects both `Surrogate-Control` and `Cache-Control: s-maxage`. Useful when you want different browser vs CDN TTLs without the CDN modifying Cache-Control sent to browser.

### Vary Header

Tells cache to maintain separate copies per header value:
```http
Vary: Accept-Encoding   # Store gzip and br variants (always set this)
Vary: Accept-Language   # Dangerous — explodes cache key space
Vary: Cookie            # NEVER do this — one copy per cookie value = cache miss rate 100%
```

Use `Vary: Accept-Encoding` universally (Cloudflare handles this automatically). Avoid varying on Cookie — use a canonical URL or surrogate keys for user-specific content.

---

## Cache Invalidation

"There are only two hard things in Computer Science: cache invalidation and naming things." — Phil Karlton

### URL-Based Purge

Purge specific URL. Simple but requires knowing exact URLs:

```bash
# Cloudflare API purge
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  --data '{"files":["https://example.com/page.html","https://example.com/app.js"]}'

# AWS CloudFront invalidation
aws cloudfront create-invalidation \
  --distribution-id EDFDVBD6EXAMPLE \
  --paths "/index.html" "/api/*"

# Fastly purge by URL
curl -X PURGE -H "Fastly-Soft-Purge: 1" https://www.example.com/page.html
```

### Tag-Based Purge (Surrogate Keys / Cache Tags)

Tag responses with logical keys. Purge all responses with a tag atomically. This is the production-grade approach for dynamic content.

```http
# Cloudflare: Cache-Tag header
Cache-Tag: product-123, category-electronics, homepage

# Fastly: Surrogate-Key header (multiple space-separated)
Surrogate-Key: product-123 category-electronics

# Akamai: Edge-Cache-Tag header
Edge-Cache-Tag: product-123
```

```bash
# Cloudflare: purge by tag (Enterprise only)
curl -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" \
  -H "Authorization: Bearer {token}" \
  -d '{"tags":["product-123"]}'

# Fastly: purge by surrogate key
curl -X PURGE -H "Surrogate-Key: product-123" \
  -H "Fastly-Soft-Purge: 1" \
  https://www.example.com/
```

### Soft Purge vs Hard Purge

**Hard purge**: Object removed immediately. Next request triggers cache miss → origin hit → potential thundering herd.
**Soft purge** (Fastly): Object marked stale but retained. Next request serves stale and triggers background revalidation. Eliminates thundering herd. Use soft purge for high-traffic sites.

### Cache Warming

After purge (or deploy), pre-populate cache to avoid cold-start latency:
```bash
# Warm critical URLs after deploy
while read url; do
  curl -s -o /dev/null -w "%{url_effective}: %{http_code} %{time_total}s\n" "$url"
done < critical_urls.txt
```

---

## CDN Security

### WAF (Web Application Firewall)

**OWASP Core Rule Set (CRS)**: Industry standard rule set for common vulnerabilities (SQLi, XSS, RFI, LFI, command injection). Cloudflare Managed Ruleset (based on CRS), AWS WAF Managed Rules, Fastly Next-Gen WAF (formerly Signal Sciences).

```bash
# AWS WAF: associate web ACL with CloudFront distribution
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:us-east-1:123456789:global/webacl/MyWebACL/abc123 \
  --resource-arn arn:aws:cloudfront::123456789:distribution/EDFDVBD6EXAMPLE
```

**Custom WAF rules** (Cloudflare Firewall Rules syntax):
```
# Block requests from known bad countries except your office IPs
(ip.geoip.country in {"CN" "RU" "KP"} and not ip.src in {192.168.1.0/24})

# Block SQL injection attempts
(http.request.uri.query contains "UNION SELECT" or 
 http.request.body contains "' OR '1'='1")

# Rate limit login endpoint
http.request.uri.path eq "/api/login"  → Rate limit: 5 req/min
```

### Bot Protection

**Cloudflare Bot Score**: 1-99 (1 = definitely bot, 99 = definitely human). Based on browser fingerprinting, JS challenges, behavioral analysis.
- `cf.bot_management.score < 30` → challenge or block
- `cf.bot_management.verified_bot` → allow (Googlebot, etc.)

**JS Challenge vs Managed Challenge**: JS Challenge forces JS execution (breaks non-browser clients). Managed Challenge is Cloudflare's adaptive challenge (invisible CAPTCHA-like, or redirect to interstitial). Use Managed Challenge for better UX.

### DDoS Mitigation

**Volumetric (L3/L4)**: Bandwidth exhaustion. CDN absorbs with anycast routing — attack traffic is distributed across all PoPs. Cloudflare claims to handle attacks exceeding 2 Tbps. AWS Shield Advanced provides DDoS cost protection.

**Protocol (L4)**: SYN floods, ICMP floods. CDN PoPs use SYN cookies, rate limiting at edge routers.

**Application (L7)**: HTTP floods, Slowloris. Requires behavior analysis — rate limiting by IP, user agent, request pattern. Configure Cloudflare Rate Limiting or AWS WAF rate-based rules.

```bash
# AWS WAF rate-based rule (block IP after 1000 requests in 5 minutes)
aws wafv2 create-web-acl --name "RateLimitACL" \
  --scope CLOUDFRONT \
  --rules file://rate-limit-rule.json
```

**AWS Shield Standard**: Automatic, free, always-on DDoS protection. Protects against SYN floods, UDP floods at L3/L4.
**AWS Shield Advanced**: Paid ($3,000/month + data transfer), adds L7 protection, DDoS cost protection, 24/7 DDoS Response Team, advanced attack diagnostics.

---

## Cloudflare Workers

### V8 Isolates

Workers do NOT run in containers or VMs — they run in V8 isolates. Each Worker is a separate isolate, not a separate process. Cold start: ~0ms (isolate reuse) — this is the key advantage over Lambda-based edge functions.

**Limits**:
- CPU time: 10ms (free plan) / 50ms (paid Bundled) / unlimited on Unbound (billed per CPU-ms)
- Memory: 128MB per isolate
- Script size: 1MB (compressed)
- Request size: 100MB
- Subrequests: 50 (free) / 1000 (paid) per request
- Environment variables: 64 vars, 5KB total
- No filesystem access (no `fs`)
- No `process` object (not Node.js)

```typescript
// Basic Worker structure
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    
    // Geographic data from Cloudflare
    const country = request.cf?.country;
    const city = request.cf?.city;
    const colo = request.cf?.colo; // PoP code e.g. "SFO"
    
    // Modify request before passing to origin
    const newRequest = new Request(request, {
      headers: {
        ...Object.fromEntries(request.headers),
        'X-Country': country || 'unknown',
        'X-Worker-Processed': '1'
      }
    });
    
    return fetch(newRequest);
  }
};
```

### Workers KV

Global, eventually consistent key-value store. Writes propagate to all PoPs within ~60 seconds. Strong read-your-writes within same PoP.

**Limits**: 25MB max value size, 512 byte max key size. Free: 100K reads/day, 1K writes/day. Paid: $0.50/million reads, $5/million writes.

```typescript
// KV operations
const value = await env.MY_KV.get("key");
const valueJson = await env.MY_KV.get("key", "json");
const valueStream = await env.MY_KV.get("key", "stream");

// Write with TTL (expiration)
await env.MY_KV.put("key", "value", { expirationTtl: 3600 }); // 1 hour
await env.MY_KV.put("key", JSON.stringify(obj), { expirationTtl: 300 });

// Delete
await env.MY_KV.delete("key");

// List keys (with prefix)
const list = await env.MY_KV.list({ prefix: "user:", limit: 100 });
```

**Use cases**: Feature flags, configuration, session data, A/B test assignments, cached API responses.

### Durable Objects

Strongly consistent, single-threaded JavaScript objects with persistent storage. Each Durable Object has a unique ID. All requests to same ID route to same physical object. Enables: real-time collaboration, websocket rooms, distributed counters, rate limiting with exact semantics.

```typescript
export class RateLimiter implements DurableObject {
  private state: DurableObjectState;
  private requests: number = 0;

  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
  }

  async fetch(request: Request): Promise<Response> {
    // Runs single-threaded — no race conditions
    this.requests = (await this.state.storage.get<number>("count")) || 0;
    this.requests++;
    await this.state.storage.put("count", this.requests);
    
    if (this.requests > 100) {
      return new Response("Rate limited", { status: 429 });
    }
    return new Response("OK");
  }
}

// In Worker: look up or create Durable Object by key
const id = env.RATE_LIMITER.idFromName(`ip:${clientIP}`);
const stub = env.RATE_LIMITER.get(id);
const response = await stub.fetch(request);
```

**WebSocket hibernation**: Durable Objects can maintain WebSocket connections across hibernation periods (Worker restarts) — connections persist without holding open an isolate.

### R2 Object Storage

S3-compatible API with **zero egress fees**. Workers can read/write R2 directly without egress costs.

```typescript
// R2 operations in Worker
const object = await env.MY_BUCKET.get("path/to/file.pdf");
if (!object) return new Response("Not found", { status: 404 });

// Stream response directly
return new Response(object.body, {
  headers: {
    "Content-Type": object.httpMetadata?.contentType || "application/octet-stream",
    "ETag": object.httpEtag,
  }
});

// Write to R2
await env.MY_BUCKET.put("path/to/file.pdf", request.body, {
  httpMetadata: { contentType: "application/pdf" }
});
```

### D1 SQLite

Serverless SQLite at the edge. HTTP API. Replicated to multiple regions (read replicas). Primary writes in one region.

```typescript
// D1 query in Worker
const result = await env.DB.prepare(
  "SELECT * FROM users WHERE id = ?"
).bind(userId).first<User>();

// Batch queries
const results = await env.DB.batch([
  env.DB.prepare("INSERT INTO users (name, email) VALUES (?, ?)").bind(name, email),
  env.DB.prepare("SELECT COUNT(*) as total FROM users"),
]);
```

**Limitations**: SQLite semantics (file-level locking, WAL mode for concurrency), 10GB max database size, not suited for high write concurrency.

### Cloudflare Queues

Message queue for async processing. Producer (Worker) enqueues messages, consumer (Worker) processes in batches.

```typescript
// Producer: send to queue
await env.MY_QUEUE.send({ userId: 123, event: "purchase" });
await env.MY_QUEUE.sendBatch([{ body: msg1 }, { body: msg2 }]);

// Consumer Worker
export default {
  async queue(batch: MessageBatch, env: Env): Promise<void> {
    for (const message of batch.messages) {
      const data = message.body as { userId: number; event: string };
      await processEvent(data, env);
      message.ack(); // Acknowledge processed
    }
  }
};
```

### AI Gateway

Proxy for AI API calls (OpenAI, Anthropic, Hugging Face, etc.) with caching, rate limiting, logging, and analytics. Route AI traffic through AI Gateway to get request logs, cache identical requests, enforce rate limits.

```typescript
// Use AI Gateway endpoint instead of direct OpenAI
const response = await fetch(
  `https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_name}/openai/chat/completions`,
  {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.OPENAI_API_KEY}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ model: "gpt-4o", messages: [...] })
  }
);
```

### Cloudflare Workers Patterns

**A/B Testing**:
```typescript
function getVariant(userId: string): "A" | "B" {
  // Deterministic assignment based on user ID
  const hash = parseInt(userId.slice(-4), 16);
  return hash % 2 === 0 ? "A" : "B";
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const cookie = request.headers.get("Cookie") || "";
    let variant = cookie.match(/ab_variant=([AB])/)?.[1] as "A" | "B" | undefined;
    
    if (!variant) {
      variant = getVariant(crypto.randomUUID());
    }
    
    const response = await fetch(
      new Request(`https://origin-${variant.toLowerCase()}.example.com${new URL(request.url).pathname}`, request)
    );
    
    const newResponse = new Response(response.body, response);
    newResponse.headers.append("Set-Cookie", `ab_variant=${variant}; Path=/; Max-Age=86400`);
    return newResponse;
  }
};
```

**JWT Verification at Edge**:
```typescript
import { verify } from "@tsndr/cloudflare-worker-jwt";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const authHeader = request.headers.get("Authorization");
    if (!authHeader?.startsWith("Bearer ")) {
      return new Response("Unauthorized", { status: 401 });
    }
    const token = authHeader.slice(7);
    const isValid = await verify(token, env.JWT_SECRET);
    if (!isValid) return new Response("Forbidden", { status: 403 });
    return fetch(request);
  }
};
```

**HTML Rewriting (HTMLRewriter)**:
```typescript
class LinkRewriter implements HTMLRewriterTypes.HTMLRewriterElementContentHandlers {
  element(element: HTMLRewriterTypes.Element) {
    const href = element.getAttribute("href");
    if (href?.startsWith("/")) {
      element.setAttribute("href", `https://cdn.example.com${href}`);
    }
  }
}

export default {
  async fetch(request: Request): Promise<Response> {
    const response = await fetch(request);
    return new HTMLRewriter()
      .on("a[href]", new LinkRewriter())
      .transform(response);
  }
};
```

---

## AWS Lambda@Edge

### Four Trigger Points

```
User → CloudFront PoP
         ↓
  [Viewer Request]  ← Before cache lookup (every request)
         ↓
  CloudFront Cache
     hit ↗   ↘ miss
         [Origin Request]  ← Before origin fetch (cache miss only)
              ↓
         Origin Server
              ↓
         [Origin Response]  ← After origin responds (cache miss only)
              ↓
  CloudFront Cache (stores response)
         ↓
  [Viewer Response]  ← Before sending to user (every request)
         ↓
User receives response
```

### Function Limits

| Trigger | Max Memory | Max Timeout | Max Body Size | Max Compressed Size |
|---|---|---|---|---|
| Viewer Request | 128MB | 5s | 40KB | 1MB |
| Origin Request | 3008MB | 30s | 1MB | 50MB |
| Viewer Response | 128MB | 5s | 40KB | 1MB |
| Origin Response | 3008MB | 30s | 1MB | 50MB |

**Critical constraints**: Lambda@Edge functions cannot use VPC. They cannot access secrets manager directly (use SSM parameters or embed in environment, noting they replicate globally). Deployed in us-east-1 but replicated to edge PoPs — code must work in any region.

```javascript
// Lambda@Edge: Add security headers (Viewer Response)
exports.handler = async (event) => {
  const response = event.Records[0].cf.response;
  const headers = response.headers;
  
  headers['strict-transport-security'] = [{
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload'
  }];
  headers['x-content-type-options'] = [{
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  }];
  headers['x-frame-options'] = [{
    key: 'X-Frame-Options',
    value: 'DENY'
  }];
  
  return response;
};
```

### CloudFront Functions

Lighter-weight than Lambda@Edge. Key differences:
- JavaScript only (ECMAScript 5.1 subset — no `const`, no arrow functions, no `async/await`)
- 2ms max compute time
- 10KB function size limit
- No outbound network calls
- Only Viewer Request and Viewer Response triggers
- KeyValueStore for reading configuration (no writes)
- ~10x lower cost than Lambda@Edge

```javascript
// CloudFront Function: URL normalization (remove trailing slash, lowercase)
function handler(event) {
  var request = event.request;
  var uri = request.uri;
  
  // Redirect to remove trailing slash
  if (uri.endsWith('/') && uri !== '/') {
    return {
      statusCode: 301,
      statusDescription: 'Moved Permanently',
      headers: {
        location: { value: uri.slice(0, -1) }
      }
    };
  }
  
  return request;
}
```

---

## Fastly Compute@Edge

WASM-based edge compute. Compile Rust, Go, AssemblyScript, or JavaScript to WebAssembly, deploy to Fastly PoPs. True polyglot edge — not limited to JavaScript.

```toml
# fastly.toml
name = "my-edge-app"
language = "rust"
[local_server]
  [local_server.backends]
    [local_server.backends.origin]
      url = "https://api.example.com"
```

```rust
// Fastly Compute@Edge in Rust
use fastly::http::{HeaderValue, Method, StatusCode};
use fastly::{Error, Request, Response};

#[fastly::main]
fn main(req: Request) -> Result<Response, Error> {
    // Route based on path
    match req.get_path() {
        "/" => Ok(Response::from_body("Hello from the edge!")),
        path if path.starts_with("/api/") => {
            // Forward to backend
            let backend_req = req.clone_without_body();
            let backend_resp = backend_req.send("origin")?;
            Ok(backend_resp)
        }
        _ => Ok(Response::from_status(StatusCode::NOT_FOUND))
    }
}
```

**Fastly Fiddle**: Browser-based IDE at `fiddle.fastly.com` for testing VCL (Varnish Configuration Language) and Compute@Edge code. Simulates request/response without deployment.

**Object Store / KV Store**: Fastly's edge key-value storage, similar to Workers KV.

---

## Vercel Edge Functions and Middleware

### Middleware

Runs before route matching on every request. Use for: auth checks, redirects, geolocation routing, A/B testing, bot detection.

```typescript
// middleware.ts (project root)
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const country = request.geo?.country || 'US';
  const city = request.geo?.city;
  
  // Geo-redirect
  if (country === 'GB') {
    return NextResponse.redirect(new URL('/uk' + request.nextUrl.pathname, request.url));
  }
  
  // Auth check
  const token = request.cookies.get('auth_token')?.value;
  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
  
  // Add custom header to forward to origin
  const response = NextResponse.next();
  response.headers.set('x-user-country', country);
  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

### Edge Runtime

```typescript
// Edge API Route
export const runtime = 'edge';  // Opt into Edge Runtime

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get('id');
  
  // No Node.js APIs (no fs, no Buffer — use Web APIs instead)
  const data = await fetch(`https://api.example.com/items/${id}`);
  const json = await data.json();
  
  return Response.json(json);
}
```

**Edge Runtime limitations**: No Node.js built-ins, no native modules, no filesystem, no `child_process`. Use Web APIs: `fetch`, `Request`, `Response`, `Headers`, `URL`, `URLSearchParams`, `crypto`, `TextEncoder/TextDecoder`.

---

## Netlify Edge Functions

Deno runtime (not Node.js). TypeScript-native. Runs at every Netlify PoP.

```typescript
// netlify/edge-functions/hello.ts
import type { Config, Context } from "@netlify/edge-functions";

export default async (request: Request, context: Context) => {
  const country = context.geo?.country?.code || 'unknown';
  
  const response = await context.next();
  response.headers.set("x-country", country);
  return response;
};

export const config: Config = {
  path: "/*",
};
```

---

## Edge-Native Architecture Patterns

### Personalization Without Origin

Store user segment in cookie or JWT claim. At edge, read segment and serve appropriate static content variant without hitting origin.

```typescript
// Cloudflare Worker: serve personalized content from KV
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const segment = getUserSegment(request); // from cookie or header
    
    // Fetch personalized content from KV (global, fast)
    const content = await env.CONTENT_KV.get(`page:home:${segment}`);
    
    if (content) {
      return new Response(content, {
        headers: { "Content-Type": "text/html", "Cache-Control": "private, max-age=300" }
      });
    }
    
    // Fallback to origin
    return fetch(request);
  }
};
```

### Image Optimization at Edge

**Cloudflare Image Resizing**: Automatic WebP/AVIF conversion, resize on-demand.

```typescript
// Serve optimized image based on client hints
export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const width = parseInt(request.headers.get("Width") || "800");
    const acceptHeader = request.headers.get("Accept") || "";
    const format = acceptHeader.includes("avif") ? "avif" 
                 : acceptHeader.includes("webp") ? "webp" 
                 : "jpeg";
    
    return fetch(request, {
      cf: {
        image: {
          width,
          format,
          quality: 80,
          fit: "scale-down"
        }
      }
    });
  }
};
```

### Geo-Routing

```typescript
const regionMap: Record<string, string> = {
  US: "https://us-api.example.com",
  EU: "https://eu-api.example.com",
  AP: "https://ap-api.example.com",
};

const countryToRegion: Record<string, string> = {
  US: "US", CA: "US", MX: "US",
  GB: "EU", DE: "EU", FR: "EU",
  JP: "AP", AU: "AP", SG: "AP",
};

export default {
  async fetch(request: Request): Promise<Response> {
    const country = (request as any).cf?.country || "US";
    const region = countryToRegion[country] || "US";
    const originBase = regionMap[region];
    
    const originUrl = new URL(request.url);
    originUrl.hostname = new URL(originBase).hostname;
    
    return fetch(new Request(originUrl.toString(), request));
  }
};
```

---

## WebAssembly at Edge

WASM is portable binary format compiled from C/C++/Rust/Go. Near-native CPU performance, no JIT warmup.

**Advantages at edge**:
- Compile once, run at any PoP (true portability)
- Sandboxed by default (no memory access outside linear memory)
- Fast startup (no cold start from JIT compilation)
- Language-agnostic (Rust for performance, Go for ease)

**Extism**: Plugin system for WASM. Host provides functions, plugins call them. Enables user-supplied WASM at edge.

```rust
// Compile to WASM for edge deployment
// cargo build --target wasm32-wasi --release
use std::collections::HashMap;

#[no_mangle]
pub fn process_request(input_ptr: i32, input_len: i32) -> i32 {
    // Process request data
    // Return transformed output
    0
}
```

**WASI (WebAssembly System Interface)**: Standardized interface for system calls (file I/O, networking). Not all WASI features available at edge (networking especially limited). Check platform docs.

---

## Edge Database Options

| Database | Protocol | Consistency | Best For |
|---|---|---|---|
| Cloudflare D1 | SQLite HTTP API | Strong (primary writes) | Structured data, low write volume |
| Turso (libSQL) | HTTP + embedded | Strong | SQLite with edge replicas |
| Upstash Redis | HTTP REST API | Eventual | Caching, rate limiting, counters |
| PlanetScale | HTTP API (Vitess) | Strong | MySQL-compatible, high scale |
| Neon | HTTP API (Postgres) | Strong | Postgres at edge |

```typescript
// Upstash Redis from edge (HTTP-based, no TCP)
import { Redis } from "@upstash/redis";

const redis = new Redis({
  url: env.UPSTASH_REDIS_REST_URL,
  token: env.UPSTASH_REDIS_REST_TOKEN,
});

// Rate limiting with sliding window
const key = `ratelimit:${clientIP}`;
const requests = await redis.incr(key);
if (requests === 1) await redis.expire(key, 60); // 1-minute window
if (requests > 100) return new Response("Too Many Requests", { status: 429 });
```

---

## TTFB Optimization

TTFB (Time To First Byte) = DNS lookup + TCP connect + TLS handshake + server processing + first byte.

**At edge**:
1. **Move to edge** → eliminate round trip to origin (most impactful)
2. **Streaming responses** → `TransformStream` to start sending HTML head before body is complete
3. **ESI (Edge Side Includes)** → cache page fragments independently, assemble at edge

```typescript
// Streaming response from edge
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    const encoder = new TextEncoder();
    
    // Start writing immediately
    const streamResponse = async () => {
      await writer.write(encoder.encode('<!DOCTYPE html><html><head>'));
      await writer.write(encoder.encode('<title>My Page</title></head><body>'));
      
      // Fetch data async while streaming started
      const data = await env.DB.prepare("SELECT * FROM articles LIMIT 10").all();
      
      for (const article of data.results) {
        await writer.write(encoder.encode(`<article>${article.title}</article>`));
      }
      
      await writer.write(encoder.encode('</body></html>'));
      await writer.close();
    };
    
    streamResponse(); // Don't await — stream in background
    
    return new Response(readable, {
      headers: { "Content-Type": "text/html; charset=utf-8" }
    });
  }
};
```

---

## Anti-Hallucination Protocol

Before asserting any edge computing behavior:

1. **Platform limits change frequently.** Cloudflare Worker limits, Lambda@Edge timeouts, CloudFront Function sizes — verify against current documentation (developers.cloudflare.com, docs.aws.amazon.com) before quoting exact numbers.
2. **Never assume Node.js APIs are available.** Edge runtimes (Workers, Vercel Edge, Deno) have different globals. Test with `typeof process === 'undefined'` — it will be true at edge.
3. **KV eventual consistency.** Never promise KV reads reflect writes within milliseconds. State "propagates within ~60 seconds globally" and qualify with current docs.
4. **Pricing changes.** Never quote exact pricing. Direct to current pricing pages.
5. **D1/R2/Queues status.** These are newer products. Check current GA vs beta status.
6. **WAF rule syntax.** Cloudflare Firewall Rules vs WAF Custom Rules have different syntaxes. Verify which product is in use.
7. **Lambda@Edge region constraint.** Functions must be deployed in us-east-1. This is a hard constraint — verify before suggesting multi-region Lambda@Edge.
8. **Cache-Control semantics by CDN.** Different CDNs interpret headers differently. Test with `curl -I` against actual CDN and inspect `CF-Cache-Status`, `X-Cache`, or `Age` response headers.

---

## Self-Review Checklist

Before delivering any edge computing design, implementation, or analysis:

- [ ] **Cache-Control headers validated**: Checked that `s-maxage` (not `max-age`) controls CDN TTL, and `private` prevents CDN caching where needed.
- [ ] **Platform runtime constraints respected**: No Node.js APIs used in edge runtime code. No filesystem, no `child_process`, no native modules.
- [ ] **Cold start behavior addressed**: V8 isolate (Workers) = no cold start. Lambda@Edge = cold start risk documented. Architecture accounts for this.
- [ ] **Consistency model correct**: KV/Edge databases consistency level matches use case. Not using eventually consistent KV for strong consistency requirements.
- [ ] **Vary header not over-broad**: Not varying on `Cookie` or `Authorization` (would defeat caching). Using surrogate keys instead for personalized content.
- [ ] **Purge strategy defined**: URL-based and/or tag-based purge implemented for content that changes. Post-deploy cache warming plan exists.
- [ ] **Security headers set at edge**: HSTS, X-Content-Type-Options, X-Frame-Options, CSP added by edge function or CDN rule.
- [ ] **WAF rules tested**: Custom WAF rules tested against sample malicious payloads and verified not to block legitimate traffic.
- [ ] **Geolocation fallback handled**: `request.cf.country` may be undefined. Default country/region defined for edge routing logic.
- [ ] **Rate limiting idempotent**: Rate limit counters use atomic operations (Durable Object or Redis INCR) to prevent race conditions.
- [ ] **Function size under limits**: Worker script size < 1MB compressed. Lambda@Edge < 50MB. CloudFront Function < 10KB.
- [ ] **CPU time within budget**: Workers ≤ 10ms (free) or 50ms (paid Bundled). Profile with `Date.now()` timestamps if near limit.
- [ ] **Origin fallback exists**: All edge functions have `fetch(request)` fallback to origin if edge logic fails (use try/catch).
- [ ] **CORS handled correctly at edge**: If edge function short-circuits response, CORS headers must be added by edge function, not origin.
- [ ] **Monitoring in place**: Cloudflare Analytics, Lambda@Edge CloudWatch Logs, or Vercel Analytics configured to observe edge function errors and performance.
