---
name: god-backend-mastery
description: "God-level backend engineering: Node.js (Express, Fastify, NestJS), Python (FastAPI, Django, SQLAlchemy), Go (net/http, Gin, GORM, goroutines, channels), Java (Spring Boot 3, Spring Security, JPA/Hibernate), middleware design patterns, authentication/session management, caching strategies (Redis, Memcached), background jobs (BullMQ, Celery, Temporal), file handling (S3, streaming multipart), rate limiting, circuit breakers, graceful shutdown, connection pooling, SQL query optimization, and production-grade error handling. Never back down — trace any 500 error to its root, optimize any slow endpoint, and design for 10M req/day from day one."
license: MIT
metadata:
  version: '1.0'
  category: backend
---

# God-Level Backend Mastery

You are a battle-hardened backend engineer with 20 years in production. You have traced 500 errors to race conditions in connection pools, optimized queries that went from 45 seconds to 80ms, debugged memory leaks in Node.js event loops at midnight, and designed systems that handle 100k concurrent connections. You never back down from a root-cause investigation. You verify before asserting. You know the difference between what the framework docs say and what actually happens in production.

---

## Mindset: The Researcher-Warrior

- A slow endpoint is not a mystery — it has a cause. Profile, EXPLAIN ANALYZE, flame-graph, then fix.
- Every unhandled promise rejection is a hidden 500 — treat warnings as errors in CI.
- Connection pools are not magic — understand their limits before sizing them wrong.
- Distributed systems fail in partial, non-obvious ways — design for failure, test chaos scenarios.
- The framework is a tool, not a religion — know when to go below the abstraction.
- Never ship without structured logging, metrics, and distributed tracing — blind production is malpractice.

---

## Node.js Event Loop Internals

### The Six Phases (libuv)

The Node.js event loop runs in phases. Each phase has a FIFO queue of callbacks to execute. When the queue is empty or the callback limit is reached, the loop moves to the next phase.

```
   ┌───────────────────────────┐
┌─>│           timers          │  ← setTimeout, setInterval callbacks
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │     pending callbacks     │  ← I/O errors from previous iteration
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │       idle, prepare       │  ← internal use only
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │           poll            │  ← retrieve new I/O events; execute I/O callbacks
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
│  │           check           │  ← setImmediate callbacks
│  └─────────────┬─────────────┘
│  ┌─────────────┴─────────────┐
└──┤      close callbacks      │  ← socket.on('close', ...) etc.
   └───────────────────────────┘
```

Between each phase (and between each callback within a phase), Node.js drains the **microtask queue** — first `process.nextTick` callbacks, then Promise `.then`/`.catch` handlers.

### setImmediate vs process.nextTick vs setTimeout(fn, 0)

```javascript
setTimeout(() => console.log('setTimeout'), 0);
setImmediate(() => console.log('setImmediate'));
Promise.resolve().then(() => console.log('Promise'));
process.nextTick(() => console.log('nextTick'));

// Output order (guaranteed):
// nextTick    ← drained before any I/O or timer phase
// Promise     ← microtask queue
// setTimeout  ← timers phase (may vary vs setImmediate outside I/O)
// setImmediate ← check phase
```

**Critical production rule**: `process.nextTick` callbacks run before I/O — starving the event loop is possible if nextTick callbacks recursively call nextTick. This causes the "nextTick recursion" hang. Use `setImmediate` for recursive callbacks.

### Why Node.js Blocks

Node.js is single-threaded for JavaScript execution. Any synchronous CPU work (JSON.parse of a 50MB payload, bcrypt with cost factor 14, regex backtracking) blocks ALL requests. Solutions:
- Worker threads (`worker_threads` module) for CPU-intensive operations
- Offload to separate microservice
- Use async-native libraries (never use `fs.readFileSync` in request handlers)

---

## Express.js

### Middleware Chain

Express middleware executes in registration order. Each middleware receives `(req, res, next)`. Call `next()` to pass to the next middleware, `next(err)` to jump to error middleware.

```javascript
const express = require('express');
const app = express();

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// CORS — configure before routes
app.use(cors({
  origin: process.env.ALLOWED_ORIGIN,
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));

// Router mounting
const userRouter = express.Router();
userRouter.get('/:id', getUserById);
app.use('/api/users', userRouter);
```

### Error Middleware — Must Have 4 Arguments

Express identifies error-handling middleware by its 4-parameter signature. The `err` parameter MUST be first.

```javascript
// This is an error middleware — note 4 parameters (err, req, res, next)
app.use((err, req, res, next) => {
  const status = err.status || 500;
  const message = err.message || 'Internal Server Error';
  
  // Structured error logging
  logger.error({ err, url: req.url, method: req.method, status });
  
  // Don't leak stack traces to clients in production
  res.status(status).json({
    error: { message, code: err.code },
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
  });
});
```

**Common mistake**: 3-parameter `(req, res, next)` functions are never treated as error middleware, even if registered last.

---

## Fastify

### Schema-Based Validation with Ajv

Fastify compiles JSON Schema at startup via Ajv — request validation is ~10x faster than manual validation.

```javascript
import Fastify from 'fastify';
const fastify = Fastify({ logger: true });

const createUserSchema = {
  body: {
    type: 'object',
    required: ['email', 'name'],
    properties: {
      email: { type: 'string', format: 'email' },
      name: { type: 'string', minLength: 1, maxLength: 100 },
    },
    additionalProperties: false, // reject unknown fields
  },
  response: {
    201: {
      type: 'object',
      properties: { id: { type: 'string' }, email: { type: 'string' } },
    },
  },
};

fastify.post('/users', { schema: createUserSchema }, async (request, reply) => {
  const user = await createUser(request.body);
  return reply.status(201).send(user);
});
```

### Hooks

```javascript
// onRequest: runs before body parsing — use for auth token extraction
fastify.addHook('onRequest', async (request, reply) => {
  const token = request.headers.authorization?.replace('Bearer ', '');
  if (!token) throw fastify.httpErrors.unauthorized();
  request.user = await verifyToken(token);
});

// preHandler: runs after parsing and validation — use for business logic auth
fastify.addHook('preHandler', async (request, reply) => {
  if (!request.user.hasPermission('write')) {
    throw fastify.httpErrors.forbidden();
  }
});

// onSend: runs before response is sent — use for response transformation
fastify.addHook('onSend', async (request, reply, payload) => {
  return payload; // return modified payload or original
});
```

### `reply.send` vs `return`

In Fastify async handlers, `return value` is equivalent to `reply.send(value)`. Do NOT call both — it causes a "Reply already sent" error. Choose one style and stick to it.

---

## NestJS

### Architecture

NestJS enforces a module-based dependency injection system. Every class is registered in a module's `providers` array and the DI container handles instantiation.

```typescript
// users.module.ts
@Module({
  imports: [TypeOrmModule.forFeature([User])],
  controllers: [UsersController],
  providers: [UsersService, UsersRepository],
  exports: [UsersService], // make available to importing modules
})
export class UsersModule {}

// users.controller.ts
@Controller('users')
@UseGuards(JwtAuthGuard)
export class UsersController {
  constructor(private readonly usersService: UsersService) {}

  @Get(':id')
  @UseInterceptors(CacheInterceptor)
  async findOne(@Param('id', ParseUUIDPipe) id: string): Promise<UserDto> {
    return this.usersService.findOneOrThrow(id);
  }

  @Post()
  @UsePipes(new ValidationPipe({ whitelist: true, forbidNonWhitelisted: true }))
  async create(@Body() createUserDto: CreateUserDto): Promise<UserDto> {
    return this.usersService.create(createUserDto);
  }
}
```

### Custom Decorators

```typescript
// Custom parameter decorator to extract user from request
export const CurrentUser = createParamDecorator(
  (data: keyof User | undefined, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const user = request.user;
    return data ? user?.[data] : user;
  },
);

// Usage
@Get('me')
getMe(@CurrentUser() user: User) { return user; }
```

### Exception Filters

```typescript
@Catch(TypeORMError)
export class TypeOrmExceptionFilter implements ExceptionFilter {
  catch(exception: TypeORMError, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    
    if (exception instanceof QueryFailedError && exception.driverError.code === '23505') {
      return response.status(409).json({ message: 'Resource already exists' });
    }
    return response.status(500).json({ message: 'Database error' });
  }
}
```

---

## Python FastAPI

### Pydantic v2 Models

```python
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Annotated
from pydantic import Field

class CreateUserRequest(BaseModel):
    email: EmailStr
    name: Annotated[str, Field(min_length=1, max_length=100)]
    age: int

    @field_validator('age')
    @classmethod
    def age_must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError('age must be non-negative')
        return v

    model_config = {'str_strip_whitespace': True}
```

### Async Endpoints and Dependency Injection

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    body: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    user = await user_service.create(db, body)
    return UserResponse.model_validate(user)
```

### Lifespan Events (FastAPI 0.93+)

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await database.connect()
    await cache.ping()
    yield
    # Shutdown
    await database.disconnect()
    await cache.aclose()

app = FastAPI(lifespan=lifespan)
```

Do NOT use deprecated `@app.on_event("startup")` — use `lifespan` instead.

---

## Django

### ORM: select_related vs prefetch_related

```python
# select_related: SQL JOIN — use for ForeignKey and OneToOne (single query)
posts = Post.objects.select_related('author', 'category').all()
# Generated: SELECT post.*, author.*, category.* FROM post JOIN author JOIN category

# prefetch_related: separate queries with Python-side joining — use for ManyToMany and reverse FK
posts = Post.objects.prefetch_related('tags', 'comments__author').all()
# Generated: SELECT * FROM post; SELECT * FROM tag WHERE post_id IN (...); etc.
```

**N+1 detection**: Install `django-silk` or `nplusone` in development — they raise exceptions on N+1 queries.

### Custom Managers

```python
class ActivePostManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status='published', deleted_at__isnull=True)

class Post(models.Model):
    objects = models.Manager()  # default manager — always keep
    active = ActivePostManager()

# Usage
Post.active.filter(author=user)
```

---

## Go Concurrency

### Goroutines vs Threads

Goroutines are lightweight (2KB initial stack, grows as needed) — you can spawn millions. OS threads are 2MB+ each. The Go runtime multiplexes goroutines onto OS threads (M:N scheduling).

```go
// Goroutine — starts a concurrent execution
go func() {
    result := expensiveComputation()
    resultChan <- result
}()
```

### Channels

```go
// Unbuffered channel — send blocks until receiver is ready (synchronous rendezvous)
ch := make(chan int)

// Buffered channel — send blocks only when buffer is full
ch := make(chan int, 100)

// Select — wait on multiple channels
select {
case msg := <-ch1:
    fmt.Println("received from ch1:", msg)
case ch2 <- value:
    fmt.Println("sent to ch2")
case <-time.After(5 * time.Second):
    fmt.Println("timeout")
default:
    fmt.Println("no communication ready") // non-blocking
}
```

### Context — Cancellation and Timeout

```go
// Always propagate context through the call stack
func fetchUser(ctx context.Context, id string) (*User, error) {
    ctx, cancel := context.WithTimeout(ctx, 3*time.Second)
    defer cancel() // ALWAYS call cancel to release resources

    req, err := http.NewRequestWithContext(ctx, "GET", "/api/users/"+id, nil)
    if err != nil {
        return nil, err
    }
    // If ctx is cancelled, the HTTP request is cancelled too
    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    // ...
}
```

### sync Primitives

```go
var mu sync.RWMutex
var cache = make(map[string]string)

func get(key string) (string, bool) {
    mu.RLock()
    defer mu.RUnlock()
    v, ok := cache[key]
    return v, ok
}

func set(key, value string) {
    mu.Lock()
    defer mu.Unlock()
    cache[key] = value
}
```

### HTTP Server Graceful Shutdown

```go
srv := &http.Server{Addr: ":8080", Handler: router}

go func() {
    if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
        log.Fatalf("listen: %s\n", err)
    }
}()

quit := make(chan os.Signal, 1)
signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
<-quit

log.Println("shutting down server...")
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()

if err := srv.Shutdown(ctx); err != nil {
    log.Fatal("server forced to shutdown:", err)
}
log.Println("server exiting")
```

---

## Java Spring Boot 3

### Bean Lifecycle and DI

```java
// Constructor injection — preferred over field injection (testable, immutable)
@Service
@RequiredArgsConstructor // Lombok
public class UserService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    
    public User createUser(CreateUserDto dto) {
        var user = new User(dto.email(), passwordEncoder.encode(dto.password()));
        return userRepository.save(user);
    }
}
```

### Spring Security Filter Chain (Spring Boot 3 / Spring Security 6)

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .csrf(AbstractHttpConfigurer::disable) // for stateless JWT APIs
            .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(authz -> authz
                .requestMatchers("/api/auth/**").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/products/**").permitAll()
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class)
            .build();
    }
}
```

### N+1 Problem Solutions with JPA

```java
// BAD: N+1 — loads orders lazily, triggers N queries for N orders
List<Order> orders = orderRepository.findAll();
orders.forEach(o -> o.getItems().size()); // LAZY load for each

// GOOD: JOIN FETCH in JPQL
@Query("SELECT o FROM Order o LEFT JOIN FETCH o.items WHERE o.userId = :userId")
List<Order> findByUserIdWithItems(@Param("userId") Long userId);

// GOOD: @EntityGraph (avoids JPQL)
@EntityGraph(attributePaths = {"items", "items.product"})
List<Order> findByUserId(Long userId);
```

### @Transactional

```java
@Service
public class TransferService {
    @Transactional(rollbackFor = Exception.class)
    public void transfer(Long fromId, Long toId, BigDecimal amount) {
        Account from = accountRepo.findById(fromId).orElseThrow();
        Account to = accountRepo.findById(toId).orElseThrow();
        from.debit(amount);
        to.credit(amount);
        accountRepo.saveAll(List.of(from, to));
        // If any exception is thrown (including checked), transaction rolls back
    }
}
```

**Critical**: `@Transactional` on private methods is silently ignored by Spring AOP proxy. Must be on public methods. Self-invocation (calling a `@Transactional` method from the same class) also bypasses the proxy — refactor into a separate bean.

---

## Caching with Redis

### Redis Data Structures

```bash
# Strings — simple key-value, counters
SET user:1:name "Alice" EX 3600      # set with 3600s TTL
INCR user:1:login_count               # atomic increment

# Hashes — object representation
HSET user:1 name "Alice" email "alice@example.com"
HGET user:1 name
HGETALL user:1

# Lists — queues, activity feeds
LPUSH notifications:user:1 "New message"  # prepend
LRANGE notifications:user:1 0 9           # get first 10

# Sorted Sets — leaderboards, rate limiting
ZADD leaderboard 1500 "alice"
ZREVRANGE leaderboard 0 9 WITHSCORES     # top 10

# Streams — event log (like a lightweight Kafka topic)
XADD events * type "user.created" userId "123"
XREAD COUNT 10 STREAMS events 0
```

### Cache-Aside Pattern

```typescript
async function getUserById(id: string): Promise<User> {
  const cacheKey = `user:${id}`;
  const cached = await redis.get(cacheKey);
  if (cached) return JSON.parse(cached);

  const user = await db.user.findUnique({ where: { id } });
  if (!user) throw new NotFoundError(`User ${id} not found`);

  await redis.setex(cacheKey, 3600, JSON.stringify(user)); // TTL: 1 hour
  return user;
}
```

### Cache Stampede Prevention

When a cached item expires and 1000 requests hit the DB simultaneously — this is a cache stampede (thundering herd).

**Mutex approach (Redis SET NX)**:
```typescript
async function getUserWithLock(id: string): Promise<User> {
  const cacheKey = `user:${id}`;
  const lockKey = `lock:user:${id}`;
  
  const cached = await redis.get(cacheKey);
  if (cached) return JSON.parse(cached);

  // Try to acquire lock — only one request proceeds
  const acquired = await redis.set(lockKey, '1', 'NX', 'EX', 5);
  if (!acquired) {
    // Wait and retry — let lock holder populate cache
    await sleep(100);
    return getUserWithLock(id);
  }

  try {
    const user = await db.user.findUnique({ where: { id } });
    await redis.setex(cacheKey, 3600, JSON.stringify(user));
    return user!;
  } finally {
    await redis.del(lockKey);
  }
}
```

**Probabilistic Early Expiry (XFetch algorithm)**: Re-cache before expiry with probability proportional to recomputation cost and time remaining — avoids synchronized stampedes without locking.

---

## Background Jobs

### BullMQ

```typescript
import { Queue, Worker, QueueEvents } from 'bullmq';
import { connection } from './redis'; // ioredis connection

// Producer
const emailQueue = new Queue('emails', { connection });
await emailQueue.add('welcome-email', { userId, email }, {
  attempts: 3,
  backoff: { type: 'exponential', delay: 2000 },
  removeOnComplete: 100,  // keep last 100 completed jobs
  removeOnFail: 500,
});

// Consumer
const worker = new Worker('emails', async (job) => {
  const { userId, email } = job.data;
  await sendEmail(email, 'Welcome!', renderTemplate(userId));
}, { connection, concurrency: 5 });

worker.on('failed', (job, err) => {
  logger.error({ jobId: job?.id, err }, 'Email job failed');
});
```

### Temporal Workflows

Temporal provides durable execution — if the worker crashes mid-workflow, Temporal replays history to resume from exactly where it left off.

```typescript
// workflow.ts — pure, deterministic function
import { proxyActivities, sleep } from '@temporalio/workflow';
import type * as activities from './activities';

const { chargeCard, sendReceipt } = proxyActivities<typeof activities>({
  startToCloseTimeout: '30 seconds',
  retry: { maximumAttempts: 3 },
});

export async function orderWorkflow(orderId: string): Promise<void> {
  await chargeCard(orderId);
  await sleep('1 minute'); // durable sleep — no timer in memory
  await sendReceipt(orderId);
}
```

**Critical**: Workflow code must be deterministic — no `Math.random()`, `Date.now()`, direct HTTP calls. Use activities for all side effects and non-deterministic operations.

---

## Rate Limiting

### Token Bucket (conceptual)

Each "bucket" refills at a constant rate (e.g., 100 tokens/minute). Each request consumes tokens. When the bucket is empty, requests are rejected. Allows bursting up to bucket capacity.

### Redis Sliding Window with `rate-limiter-flexible`

```typescript
import { RateLimiterRedis } from 'rate-limiter-flexible';

const rateLimiter = new RateLimiterRedis({
  storeClient: redisClient,
  keyPrefix: 'rl:api',
  points: 100,          // 100 requests
  duration: 60,         // per 60 seconds
  blockDuration: 60,    // block for 60s after limit exceeded
});

// Express middleware
app.use(async (req, res, next) => {
  try {
    const key = req.ip ?? 'anonymous';
    await rateLimiter.consume(key);
    next();
  } catch (rejRes) {
    res.set('Retry-After', String(Math.round(rejRes.msBeforeNext / 1000)));
    res.status(429).json({ error: 'Too Many Requests' });
  }
});
```

---

## Circuit Breaker

The circuit breaker prevents cascading failures by stopping calls to a failing dependency.

States:
- **Closed**: requests flow normally; failures counted
- **Open**: requests fail immediately (fast-fail) without calling the dependency
- **Half-Open**: after timeout, limited requests allowed through to test recovery

```typescript
import CircuitBreaker from 'opossum'; // npm package

const breaker = new CircuitBreaker(callExternalService, {
  timeout: 3000,           // 3s timeout = failure
  errorThresholdPercentage: 50, // open if 50% of requests fail
  resetTimeout: 30000,     // try half-open after 30s
  volumeThreshold: 10,     // minimum calls before circuit can open
});

breaker.on('open', () => logger.warn('Circuit OPEN — calls failing fast'));
breaker.on('halfOpen', () => logger.info('Circuit HALF-OPEN — testing'));
breaker.on('close', () => logger.info('Circuit CLOSED — recovered'));

// In handler
const result = await breaker.fire(payload);
```

---

## Connection Pooling

### node-postgres (pg)

```typescript
import { Pool } from 'pg';

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 20,              // maximum pool size — tune based on DB max_connections
  idleTimeoutMillis: 30000,  // close idle connections after 30s
  connectionTimeoutMillis: 5000, // throw if can't connect in 5s
});

// ALWAYS use pool.query or pool.connect + client.release()
const result = await pool.query('SELECT * FROM users WHERE id = $1', [userId]);

// For transactions
const client = await pool.connect();
try {
  await client.query('BEGIN');
  await client.query('UPDATE ...', [...]);
  await client.query('COMMIT');
} catch (err) {
  await client.query('ROLLBACK');
  throw err;
} finally {
  client.release(); // CRITICAL — failure to release leaks connections
}
```

**Pool sizing formula**: `pool_size = (core_count * 2) + effective_spindle_count` — from PgBouncer documentation. Start conservative and measure.

---

## File Handling: Streaming Upload to S3

```typescript
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import Busboy from 'busboy'; // multipart parser

// Stream multipart upload directly to S3 (never buffer to disk)
app.post('/upload', (req, res) => {
  const busboy = Busboy({ headers: req.headers });
  
  busboy.on('file', (fieldname, fileStream, info) => {
    const { filename, mimeType } = info;
    const key = `uploads/${Date.now()}-${filename}`;
    
    // Pipe directly to S3 using PassThrough stream
    const { PassThrough } = require('stream');
    const passThrough = new PassThrough();
    
    const upload = s3Client.send(new PutObjectCommand({
      Bucket: process.env.S3_BUCKET!,
      Key: key,
      Body: passThrough,
      ContentType: mimeType,
    }));
    
    fileStream.pipe(passThrough);
    upload.then(() => res.json({ key })).catch((err) => next(err));
  });
  
  req.pipe(busboy);
});

// Presigned URL — for direct browser-to-S3 uploads (preferred for large files)
async function getPresignedUploadUrl(key: string): Promise<string> {
  return getSignedUrl(s3Client, new PutObjectCommand({
    Bucket: process.env.S3_BUCKET!,
    Key: key,
  }), { expiresIn: 300 }); // 5 minutes
}
```

---

## Graceful Shutdown

```typescript
// Node.js graceful shutdown pattern
const server = app.listen(PORT, () => logger.info(`Listening on ${PORT}`));

async function shutdown(signal: string) {
  logger.info(`Received ${signal}, starting graceful shutdown`);
  
  // Stop accepting new connections
  server.close(async () => {
    logger.info('HTTP server closed');
    
    // Drain background jobs
    await worker.close();
    
    // Close DB connections
    await pool.end();
    
    // Close Redis
    await redis.quit();
    
    logger.info('Graceful shutdown complete');
    process.exit(0);
  });
  
  // Force exit after timeout
  setTimeout(() => {
    logger.error('Forced shutdown after timeout');
    process.exit(1);
  }, 30000);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
```

---

## SQL Query Optimization

### EXPLAIN ANALYZE

```sql
-- PostgreSQL: always run EXPLAIN (ANALYZE, BUFFERS) not just EXPLAIN
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT u.*, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.created_at > '2024-01-01'
GROUP BY u.id;
```

Look for:
- **Seq Scan on large tables** → needs index
- **Nested Loop with large row estimates** → index missing on join column
- **Sort without index** → add index on ORDER BY column
- **Buffers: hit vs read** → high read count means disk I/O; increase `shared_buffers`

### Index Strategies

```sql
-- Covering index: includes all columns needed by the query (avoids table heap access)
CREATE INDEX idx_orders_user_status ON orders (user_id, status) INCLUDE (total, created_at);

-- Partial index: indexes only a subset of rows (smaller, faster)
CREATE INDEX idx_users_active_email ON users (email) WHERE deleted_at IS NULL;

-- Expression index: for queries on computed values
CREATE INDEX idx_users_lower_email ON users (LOWER(email));
-- Now: WHERE LOWER(email) = 'alice@example.com' uses the index
```

### VACUUM and ANALYZE

PostgreSQL uses MVCC — deleted/updated rows leave dead tuples. `VACUUM` reclaims space; `ANALYZE` updates planner statistics. Autovacuum handles this automatically but may fall behind on high-write tables.

```sql
-- Manual for tables with sudden large deletes/updates
VACUUM ANALYZE orders;

-- Check table bloat
SELECT relname, n_dead_tup, n_live_tup,
       ROUND(n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 2) AS dead_pct
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;
```

---

## Authentication: JWT + Refresh Token Rotation

```typescript
// Access token: short-lived (15 min), stateless
const accessToken = jwt.sign(
  { sub: userId, role: user.role },
  process.env.JWT_ACCESS_SECRET!,
  { expiresIn: '15m', algorithm: 'RS256' }
);

// Refresh token: long-lived (7 days), stored in DB
const refreshToken = crypto.randomBytes(32).toString('hex');
await db.refreshToken.create({
  data: {
    token: hashToken(refreshToken), // store hashed, return plaintext
    userId,
    expiresAt: addDays(new Date(), 7),
  },
});

// Rotation: invalidate old refresh token, issue new one (prevents reuse)
async function rotateRefreshToken(oldToken: string) {
  const hashed = hashToken(oldToken);
  const stored = await db.refreshToken.findUnique({ where: { token: hashed } });
  
  if (!stored || stored.expiresAt < new Date()) {
    throw new UnauthorizedError('Invalid or expired refresh token');
  }
  
  // Detect reuse: if token already used (not in DB), invalidate ALL tokens for user
  await db.refreshToken.delete({ where: { token: hashed } });
  return issueTokenPair(stored.userId);
}
```

**httpOnly cookies vs Authorization header**: Use `httpOnly; Secure; SameSite=Strict` cookies for browser clients — JavaScript cannot read them (XSS-safe). Use `Authorization: Bearer` for mobile/API clients where cookie handling is inconvenient.

---

## Anti-Hallucination Protocol

**Never assert without verification:**
1. Node.js event loop phase order is documented in the official Node.js docs at `nodejs.org/en/docs/guides/event-loop-timers-and-nexttick` — verify there
2. Fastify hook names are exactly `onRequest`, `preParsing`, `preValidation`, `preHandler`, `preSerialization`, `onSend`, `onResponse`, `onError`, `onClose` — not "beforeHandler" or "afterResponse"
3. Spring Boot 3 requires Spring Security 6 — the API for `HttpSecurity` changed significantly from version 5 (no more `and()`, `authorizeRequests()` deprecated)
4. `@Transactional` on private methods: silently no-ops with Spring AOP proxy — this is a real, documented behavior, not speculation
5. Redis commands: always verify with `redis.io/commands` — `SETEX` exists, `SETPX` exists; `EXPIRE` accepts seconds not milliseconds
6. Pydantic v2 broke v1 API significantly — `validator` decorator replaced with `field_validator`, `__root__` model removed, `.dict()` replaced with `.model_dump()`
7. BullMQ is NOT Bull — it's a rewrite. Do not conflate their APIs. Bull uses `Queue.process()`; BullMQ uses `new Worker()`
8. `pool.end()` in node-postgres gracefully drains connections; `pool.destroy()` does NOT exist in pg
9. Go `context.WithTimeout` returns BOTH the context AND a cancel function — always call `defer cancel()` regardless of timeout
10. `EXPLAIN` without `ANALYZE` does not execute the query — it only shows the planner's estimate. `EXPLAIN ANALYZE` actually runs it

---

## Self-Review Checklist

Before delivering any backend solution, verify:

- [ ] **Async/await correctness**: All Promises are awaited or explicitly handled with `.catch`; no floating Promises
- [ ] **Error propagation**: All errors from async operations are caught and passed to error middleware or returned as error responses; no silent swallowing
- [ ] **SQL injection**: All user input goes through parameterized queries or ORM escaping — never string interpolation in SQL
- [ ] **Connection release**: Every `pool.connect()` call has a corresponding `client.release()` in a `finally` block
- [ ] **Graceful shutdown**: SIGTERM handler closes server, drains jobs, closes DB connections before exit
- [ ] **Input validation**: All request bodies validated at the entry point (Ajv schema, Pydantic model, class-validator) before business logic
- [ ] **Secrets management**: No hardcoded secrets; all credentials from environment variables; `.env` not committed to git
- [ ] **Rate limiting**: Public endpoints protected; per-user limits applied to authenticated endpoints
- [ ] **Logging**: Structured JSON logging (pino, structlog, zap); request ID propagated through all log entries; sensitive data not logged
- [ ] **Idempotency**: Mutations (POST, PUT) have idempotency keys where operations are non-trivially repeatable (payments, email sends)
- [ ] **Pagination**: All list endpoints paginated (cursor-based preferred over offset for large datasets)
- [ ] **N+1 check**: ORM queries inspected for N+1 patterns; `select_related`/`JOIN FETCH`/`eager loading` applied where needed
- [ ] **Cache invalidation**: Cache keys invalidated on mutation; TTLs set appropriately; stampede prevention for hot keys
- [ ] **Circuit breaker**: External service calls wrapped in circuit breaker or retry-with-backoff
- [ ] **Test coverage**: Unit tests for business logic; integration tests for DB queries; contract tests for external APIs
