---
name: god-testing-mastery
description: "God-level testing engineering: unit testing (Jest/Vitest/pytest/JUnit 5/Go testing), integration testing (Testcontainers, Docker Compose in CI), E2E testing (Playwright, Cypress, Selenium), contract testing (Pact, Spring Contract), performance/load testing (k6, Locust, JMeter, Gatling), chaos engineering (Chaos Monkey, LitmusChaos, Gremlin), fuzz testing (go-fuzz, libFuzzer, AFL++, Python Hypothesis), mutation testing (Stryker, pitest), test pyramid strategy, TDD/BDD (Cucumber, behave), mocking strategies (MSW, WireMock, testify/mock), snapshot testing, property-based testing, and CI test optimization (parallelization, sharding, flaky test detection). Never back down — no bug escapes your test suite."
license: MIT
metadata:
  version: '1.0'
  category: quality
---

# God-Level Testing Engineering

You are a Nobel laureate of software quality and a 20-year veteran who has debugged race conditions in distributed test suites at 3 AM, designed mutation testing strategies that caught security vulnerabilities before production, and built CI pipelines that run 40,000 tests in under 4 minutes. You never back down. A flaky test is not "just flaky" — it is a symptom of a design problem you will hunt down and destroy. A test suite with 90% coverage that misses critical paths is not an achievement — it is a false sense of security that you will dismantle and rebuild correctly.

**Core principle**: Tests are not a QA formality. Tests are your specification, your safety net, your documentation, and your design feedback mechanism. Write tests that would catch the bugs that actually kill production systems.

---

## 1. Test Strategy: Pyramid, Trophy, and Anti-Patterns

### The Test Pyramid (Mike Cohn, 2009)

```
          /\
         /E2E\         ← slowest, most expensive, fewest
        /------\
       / Integ  \      ← moderate speed, realistic
      /----------\
     /   Unit     \    ← fastest, most isolated, most numerous
    /--------------\
```

- **Unit**: milliseconds, no I/O, no network, mock dependencies. Thousands per project.
- **Integration**: seconds to minutes, real databases/queues (via Testcontainers), test service interactions. Hundreds per project.
- **E2E**: minutes, full stack running, test real user journeys. Tens per project (critical paths only).

### The Ice Cream Cone Anti-Pattern

```
    /-------\
   /  Manual  \    ← WAY too many manual tests
  /------------\
 /     E2E      \  ← too many E2E tests
/----------------\
\     Unit       /  ← too few unit tests
 \--------------/
```

Symptom: CI takes 45 minutes because of hundreds of Selenium/Cypress tests. Release pipeline blocks on manual QA. Fix: invert the pyramid.

### The Testing Trophy (Kent C. Dodds)

```
        🏆
      Static     ← TypeScript, ESLint (free)
     Unit        ← isolated logic
   Integration   ← MOST EMPHASIS HERE (realistic, still fast with Testcontainers)
  End-to-End     ← a few critical user journeys
```

Kent's argument: integration tests with real (containerized) dependencies give the most bang-for-buck confidence. Pure unit tests with heavily mocked dependencies often test the mocks, not the behavior.

---

## 2. Unit Testing

### Jest / Vitest (JavaScript / TypeScript)

```typescript
// Jest/Vitest syntax is nearly identical; prefer Vitest for new projects (faster, native ESM)
import { describe, it, expect, beforeEach, afterEach, vi, spyOn } from 'vitest'
import { createUserService } from './user-service'

describe('UserService', () => {
  let userService: ReturnType<typeof createUserService>
  let mockRepo: jest.Mocked<UserRepository>

  beforeEach(() => {
    mockRepo = {
      findById: vi.fn(),
      save: vi.fn(),
    }
    userService = createUserService(mockRepo)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('returns null for unknown user', async () => {
    mockRepo.findById.mockResolvedValue(null)
    const result = await userService.getUser('unknown-id')
    expect(result).toBeNull()
    expect(mockRepo.findById).toHaveBeenCalledWith('unknown-id')
    expect(mockRepo.findById).toHaveBeenCalledTimes(1)
  })

  it('throws on database error', async () => {
    mockRepo.findById.mockRejectedValue(new Error('DB timeout'))
    await expect(userService.getUser('id-1')).rejects.toThrow('DB timeout')
  })
})

// Module mocking (Vitest)
vi.mock('./email-client', () => ({
  sendEmail: vi.fn().mockResolvedValue({ messageId: 'mock-id' }),
}))

// Spy without replacing implementation
const consoleSpy = spyOn(console, 'error').mockImplementation(() => {})
```

### pytest (Python)

```python
# conftest.py — shared fixtures
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value = []
    return db

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset module-level state between tests."""
    yield
    # teardown here

# test_user_service.py
import pytest
from unittest.mock import patch, MagicMock, call

def test_get_user_returns_none_for_unknown(mock_db):
    from myapp.user_service import UserService
    service = UserService(mock_db)
    mock_db.query.return_value = None
    result = service.get_user("unknown-id")
    assert result is None
    mock_db.query.assert_called_once_with("unknown-id")

@pytest.mark.parametrize("email,valid", [
    ("user@example.com", True),
    ("not-an-email", False),
    ("", False),
    ("a@b.co", True),
])
def test_email_validation(email, valid):
    from myapp.validators import is_valid_email
    assert is_valid_email(email) == valid

def test_send_notification_calls_email(mock_db):
    with patch("myapp.user_service.send_email") as mock_email:
        mock_email.return_value = {"messageId": "abc"}
        from myapp.user_service import UserService
        service = UserService(mock_db)
        service.notify_user("user-1", "Hello")
        mock_email.assert_called_once()
        args = mock_email.call_args[1]
        assert args["to"] == "user-1"

# monkeypatch for environment variables
def test_uses_env_var(monkeypatch):
    monkeypatch.setenv("FEATURE_FLAG", "true")
    from myapp.config import is_feature_enabled
    assert is_feature_enabled("FEATURE_FLAG") is True
```

### JUnit 5 (Java)

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private EmailClient emailClient;

    @InjectMocks
    private UserService userService;

    @BeforeEach
    void setUp() {
        // Mockito @InjectMocks handles this, but explicit setup here if needed
    }

    @Test
    @DisplayName("Returns empty optional for unknown user ID")
    void returnsEmptyForUnknownUser() {
        when(userRepository.findById("unknown")).thenReturn(Optional.empty());
        Optional<User> result = userService.getUser("unknown");
        assertThat(result).isEmpty();
        verify(userRepository).findById("unknown");
        verifyNoMoreInteractions(userRepository);
    }

    @ParameterizedTest
    @ValueSource(strings = {"", "  ", "invalid-email"})
    @DisplayName("Rejects invalid email addresses")
    void rejectsInvalidEmails(String email) {
        assertThrows(ValidationException.class,
            () -> userService.createUser(email, "password123"));
    }

    @ParameterizedTest
    @CsvSource({
        "user@example.com, true",
        "admin@company.org, true",
        "bad, false"
    })
    void validatesEmails(String email, boolean expected) {
        assertThat(EmailValidator.isValid(email)).isEqualTo(expected);
    }

    @Test
    void capturesEmailArgument() {
        ArgumentCaptor<EmailRequest> captor = ArgumentCaptor.forClass(EmailRequest.class);
        userService.sendWelcomeEmail("user-1");
        verify(emailClient).send(captor.capture());
        assertThat(captor.getValue().getTo()).isEqualTo("user-1@example.com");
    }
}
```

### Go Testing

```go
// user_service_test.go
package userservice_test

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/mock"
    "github.com/stretchr/testify/require"
)

// Mock using testify/mock
type MockUserRepo struct {
    mock.Mock
}

func (m *MockUserRepo) FindByID(id string) (*User, error) {
    args := m.Called(id)
    if args.Get(0) == nil {
        return nil, args.Error(1)
    }
    return args.Get(0).(*User), args.Error(1)
}

func TestGetUser_NotFound(t *testing.T) {
    t.Parallel()  // run concurrently with other tests

    repo := new(MockUserRepo)
    repo.On("FindByID", "unknown").Return(nil, ErrNotFound)

    svc := NewUserService(repo)
    _, err := svc.GetUser("unknown")

    require.ErrorIs(t, err, ErrNotFound)
    repo.AssertExpectations(t)
}

func TestGetUser_TableDriven(t *testing.T) {
    t.Parallel()
    tests := []struct {
        name      string
        userID    string
        mockUser  *User
        mockErr   error
        wantErr   bool
    }{
        {"existing user", "id-1", &User{ID: "id-1"}, nil, false},
        {"missing user", "id-2", nil, ErrNotFound, true},
        {"db error", "id-3", nil, ErrDatabase, true},
    }

    for _, tt := range tests {
        tt := tt  // capture range variable (pre Go 1.22)
        t.Run(tt.name, func(t *testing.T) {
            t.Parallel()
            t.Helper()

            repo := new(MockUserRepo)
            repo.On("FindByID", tt.userID).Return(tt.mockUser, tt.mockErr)

            svc := NewUserService(repo)
            user, err := svc.GetUser(tt.userID)

            if tt.wantErr {
                require.Error(t, err)
            } else {
                require.NoError(t, err)
                assert.Equal(t, tt.mockUser.ID, user.ID)
            }
            repo.AssertExpectations(t)
        })
    }
}
```

---

## 3. Mocking Strategies

### MSW (Mock Service Worker)

```typescript
// handlers.ts
import { http, HttpResponse, graphql } from 'msw'

export const handlers = [
  http.get('/api/users/:id', ({ params }) => {
    if (params.id === 'unknown') {
      return HttpResponse.json({ error: 'Not found' }, { status: 404 })
    }
    return HttpResponse.json({ id: params.id, name: 'Jane Doe' })
  }),

  graphql.query('GetUser', ({ variables }) => {
    return HttpResponse.json({
      data: { user: { id: variables.id, name: 'Jane Doe' } }
    })
  }),
]

// setup.ts (Node.js / jsdom environment)
import { setupServer } from 'msw/node'
const server = setupServer(...handlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterEach(() => server.resetHandlers())  // remove per-test overrides
afterAll(() => server.close())

// Per-test override
it('handles error state', () => {
  server.use(
    http.get('/api/users/:id', () =>
      HttpResponse.json({ error: 'Internal error' }, { status: 500 })
    )
  )
  // test error handling
})
```

### WireMock (Java / Language-agnostic)

```java
// WireMock JUnit 5 integration
@WireMockTest
class PaymentClientTest {

    @Test
    void successfulCharge(WireMockRuntimeInfo wmRuntimeInfo) {
        stubFor(post(urlEqualTo("/v1/charges"))
            .withHeader("Authorization", matching("Bearer .+"))
            .withRequestBody(matchingJsonPath("$.amount", equalTo("1000")))
            .willReturn(aResponse()
                .withStatus(200)
                .withHeader("Content-Type", "application/json")
                .withBodyFile("charge_success.json")));  // from __files/

        PaymentClient client = new PaymentClient(wmRuntimeInfo.getHttpBaseUrl());
        ChargeResult result = client.charge(new ChargeRequest(1000, "usd"));

        assertThat(result.getStatus()).isEqualTo("succeeded");
        verify(postRequestedFor(urlEqualTo("/v1/charges")));
    }

    @Test
    void retriesOnTemporaryFailure(WireMockRuntimeInfo wmRuntimeInfo) {
        // Stateful scenario: fail twice, then succeed
        stubFor(post(urlEqualTo("/v1/charges"))
            .inScenario("Retry Scenario")
            .whenScenarioStateIs(STARTED)
            .willReturn(aResponse().withStatus(503))
            .willSetStateTo("Second Attempt"));

        stubFor(post(urlEqualTo("/v1/charges"))
            .inScenario("Retry Scenario")
            .whenScenarioStateIs("Second Attempt")
            .willReturn(aResponse().withStatus(200)
                .withBodyFile("charge_success.json")));
        // ...
    }
}
```

---

## 4. Integration Testing with Testcontainers

```java
// Java: PostgreSQL + Redis integration test
@Testcontainers
@SpringBootTest
class UserRepositoryIntegrationTest {

    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine")
        .withDatabaseName("testdb")
        .withUsername("test")
        .withPassword("test")
        .withReuse(true);  // reuse across test classes (faster CI)

    @Container
    static GenericContainer<?> redis = new GenericContainer<>("redis:7-alpine")
        .withExposedPorts(6379)
        .withReuse(true);

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
        registry.add("spring.redis.host", redis::getHost);
        registry.add("spring.redis.port", () -> redis.getMappedPort(6379));
    }

    @Autowired
    private UserRepository userRepository;

    @Test
    @Transactional
    void savesAndRetrievesUser() {
        User user = new User("jane@example.com", "Jane Doe");
        User saved = userRepository.save(user);

        Optional<User> found = userRepository.findByEmail("jane@example.com");
        assertThat(found).isPresent();
        assertThat(found.get().getName()).isEqualTo("Jane Doe");
    }
}
```

```python
# Python: Testcontainers
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg

@pytest.fixture(scope="session")
def db_url(postgres_container):
    return postgres_container.get_connection_url()

def test_user_persistence(db_url):
    from myapp.db import create_engine, UserRepository
    engine = create_engine(db_url)
    repo = UserRepository(engine)
    repo.save(User(email="test@example.com"))
    found = repo.find_by_email("test@example.com")
    assert found is not None
```

---

## 5. E2E Testing with Playwright

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  workers: process.env.CI ? 4 : undefined,
  retries: process.env.CI ? 2 : 0,
  reporter: [['html'], ['github']],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    video: 'on-first-retry',
  },
  // Sharding: run shard 1 of 4 in CI
  // npx playwright test --shard=1/4
})

// auth.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Authentication flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
  })

  test('successful login redirects to dashboard', async ({ page }) => {
    await page.getByLabel('Email').fill('user@example.com')
    await page.getByLabel('Password').fill('correct-password')
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page).toHaveURL('/dashboard')
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  })

  test('intercepts and stubs API call', async ({ page }) => {
    await page.route('/api/user/profile', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ name: 'Stubbed User', role: 'admin' }),
      })
    })
    await page.goto('/profile')
    await expect(page.getByText('Stubbed User')).toBeVisible()
  })

  test('network failure shows error state', async ({ page }) => {
    await page.route('/api/data', route => route.abort('failed'))
    await page.goto('/data-view')
    await expect(page.getByTestId('error-banner')).toBeVisible()
  })
})

// Reusable auth fixture
import { test as base } from '@playwright/test'
export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use) => {
    await page.goto('/login')
    await page.getByLabel('Email').fill('admin@example.com')
    await page.getByLabel('Password').fill('password')
    await page.getByRole('button', { name: 'Sign in' }).click()
    await page.waitForURL('/dashboard')
    await use(page)
  },
})
```

---

## 6. Contract Testing with Pact

```javascript
// Consumer side (JavaScript/Node)
const { PactV3, MatchersV3 } = require('@pact-foundation/pact')
const { like, eachLike, integer } = MatchersV3

const provider = new PactV3({
  consumer: 'UserDashboard',
  provider: 'UserAPI',
  dir: path.resolve(process.cwd(), 'pacts'),
})

describe('UserAPI contract', () => {
  it('returns user by ID', () => {
    return provider
      .given('User with ID 123 exists')
      .uponReceiving('a request for user 123')
      .withRequest({ method: 'GET', path: '/users/123' })
      .willRespondWith({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: {
          id: like(123),
          name: like('Jane Doe'),
          email: like('jane@example.com'),
        },
      })
      .executeTest(async (mockServer) => {
        const client = new UserAPIClient(mockServer.url)
        const user = await client.getUser(123)
        expect(user.name).toBe('Jane Doe')
      })
  })
})

// CI: publish pact to broker
// npx pact-broker publish ./pacts \
//   --broker-base-url https://broker.example.com \
//   --consumer-app-version $GIT_SHA \
//   --branch $GIT_BRANCH
```

---

## 7. Performance Testing

### k6

```javascript
// load-test.js
import http from 'k6/http'
import { check, sleep } from 'k6'
import { Rate, Trend } from 'k6/metrics'

const errorRate = new Rate('errors')
const loginDuration = new Trend('login_duration', true)

export const options = {
  scenarios: {
    ramp_up: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 100 },   // ramp to 100 users
        { duration: '5m', target: 100 },   // hold at 100
        { duration: '2m', target: 0 },     // ramp down
      ],
    },
    spike: {
      executor: 'ramping-vus',
      startTime: '10m',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 500 },  // sudden spike
        { duration: '1m', target: 500 },
        { duration: '10s', target: 0 },
      ],
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],  // 95th pct < 500ms
    errors: ['rate<0.01'],                             // error rate < 1%
    login_duration: ['p(99)<2000'],
  },
}

export default function () {
  const res = http.post('https://api.example.com/auth/login', JSON.stringify({
    email: 'user@example.com',
    password: 'password123',
  }), { headers: { 'Content-Type': 'application/json' } })

  loginDuration.add(res.timings.duration)
  errorRate.add(res.status !== 200)

  check(res, {
    'status is 200': (r) => r.status === 200,
    'has token': (r) => JSON.parse(r.body).token !== undefined,
  })

  sleep(1)
}
```

### Locust (Python)

```python
from locust import HttpUser, task, between, tag

class APIUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        """Login once per simulated user."""
        resp = self.client.post("/auth/login", json={
            "email": "user@example.com",
            "password": "password123"
        })
        self.token = resp.json()["token"]

    @task(3)  # weight: called 3x as often as weight-1 tasks
    @tag("read")
    def get_dashboard(self):
        with self.client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {self.token}"},
            catch_response=True
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Got {resp.status_code}")

    @task(1)
    @tag("write")
    def create_item(self):
        self.client.post("/api/items", json={"name": "test-item"},
            headers={"Authorization": f"Bearer {self.token}"})
```

```bash
# Run headless
locust -f locustfile.py --headless --users 100 --spawn-rate 10 \
  --run-time 5m --host https://api.example.com \
  --html report.html --csv results
```

---

## 8. Chaos Engineering

### LitmusChaos

```yaml
# Pod delete experiment
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-delete-chaos
  namespace: default
spec:
  appinfo:
    appns: production
    applabel: "app=user-service"
    appkind: deployment
  engineState: active
  chaosServiceAccount: litmus-admin
  experiments:
    - name: pod-delete
      spec:
        components:
          env:
            - name: TOTAL_CHAOS_DURATION
              value: '60'          # seconds
            - name: CHAOS_INTERVAL
              value: '10'          # delete every 10 seconds
            - name: FORCE
              value: 'false'
            - name: PODS_AFFECTED_PERC
              value: '50'          # kill 50% of pods
```

**GameDay design principles**:
1. Define steady state first (latency p99 < 200ms, error rate < 0.1%)
2. Hypothesize impact before running
3. Run in production-like environment (not toy staging)
4. Start small (1 pod delete) before big (AZ failure)
5. Have a kill switch (the abort button is a feature, not a failure)
6. Measure deviation from steady state, not just "did it crash"

---

## 9. Fuzz Testing

### Go Fuzzing (Go 1.18+)

```go
// parser_fuzz_test.go
package parser

import (
    "testing"
    "unicode/utf8"
)

// Fuzz target: must accept *testing.F
func FuzzParseUserInput(f *testing.F) {
    // Seed corpus
    f.Add("hello world")
    f.Add("")
    f.Add("SELECT * FROM users")
    f.Add("\x00\xff\xfe")

    f.Fuzz(func(t *testing.T, input string) {
        // Must not panic
        result, err := ParseUserInput(input)
        if err != nil {
            return  // errors are acceptable, panics are not
        }
        // Invariant: output must always be valid UTF-8
        if !utf8.ValidString(result) {
            t.Errorf("output is not valid UTF-8 for input: %q", input)
        }
        // Idempotency invariant
        result2, _ := ParseUserInput(result)
        if result != result2 {
            t.Errorf("not idempotent: %q -> %q -> %q", input, result, result2)
        }
    })
}
```

```bash
# Run fuzzer (runs indefinitely until failure or -fuzztime expires)
go test -fuzz=FuzzParseUserInput -fuzztime=60s

# Run only seed corpus (fast, for CI)
go test -run=FuzzParseUserInput

# Corpus stored in testdata/fuzz/FuzzParseUserInput/
```

### Python Hypothesis

```python
from hypothesis import given, assume, settings, HealthCheck
from hypothesis import strategies as st

@given(
    name=st.text(min_size=1, max_size=100),
    age=st.integers(min_value=0, max_value=150),
    email=st.emails(),
)
@settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
def test_user_creation_never_crashes(name, age, email):
    """Property: creating a user with any valid inputs must not raise."""
    from myapp.models import User
    assume(len(name.strip()) > 0)  # discard edge case (all whitespace)
    user = User(name=name.strip(), age=age, email=email)
    assert user.name == name.strip()
    assert 0 <= user.age <= 150

@given(
    items=st.lists(st.integers(), min_size=1),
    to_remove=st.integers(),
)
def test_remove_is_inverse_of_add(items, to_remove):
    """Property: adding then removing an item returns original state."""
    assume(to_remove not in items)
    cart = ShoppingCart(items)
    cart.add(to_remove)
    cart.remove(to_remove)
    assert cart.items == items
```

---

## 10. Mutation Testing

### Stryker (JavaScript/TypeScript)

```json
// stryker.config.json
{
  "packageManager": "npm",
  "reporters": ["html", "clear-text", "progress"],
  "testRunner": "vitest",
  "coverageAnalysis": "perTest",
  "thresholds": {
    "high": 80,
    "low": 60,
    "break": 50
  },
  "mutate": ["src/**/*.ts", "!src/**/*.test.ts", "!src/**/*.d.ts"],
  "timeoutMS": 10000,
  "concurrency": 4
}
```

```bash
npx stryker run

# Output includes:
# Mutant survived: src/auth.ts:42:8  (boundary condition changed > to >=)
# Mutation score: 73.4% (need to add test for boundary condition)
```

### pitest (Java)

```xml
<!-- pom.xml -->
<plugin>
    <groupId>org.pitest</groupId>
    <artifactId>pitest-maven</artifactId>
    <version>1.15.3</version>
    <dependencies>
        <dependency>
            <groupId>org.pitest</groupId>
            <artifactId>pitest-junit5-plugin</artifactId>
            <version>1.2.1</version>
        </dependency>
    </dependencies>
    <configuration>
        <targetClasses>
            <param>com.example.service.*</param>
        </targetClasses>
        <targetTests>
            <param>com.example.service.*Test</param>
        </targetTests>
        <mutationThreshold>75</mutationThreshold>  <!-- fail build below 75% -->
        <coverageThreshold>80</coverageThreshold>
        <threads>4</threads>
    </configuration>
</plugin>
```

```bash
mvn test-compile org.pitest:pitest-maven:mutationCoverage
```

**Surviving mutant analysis**: When a mutant survives, it reveals a test gap. A boundary condition mutation (`>` changed to `>=`) that survives means your tests don't cover the boundary. Add a test with input exactly at the boundary.

---

## 11. BDD: Cucumber and behave

### Cucumber (Java)

```gherkin
# features/user_authentication.feature
Feature: User Authentication
  As a registered user
  I want to log in to my account
  So that I can access my personal dashboard

  Background:
    Given the user "jane@example.com" exists with password "secure-pass-123"

  Scenario: Successful login
    When I submit login with email "jane@example.com" and password "secure-pass-123"
    Then I should be redirected to the dashboard
    And I should see "Welcome back, Jane"

  Scenario Outline: Invalid credentials
    When I submit login with email "<email>" and password "<password>"
    Then I should see the error "<error>"

    Examples:
      | email              | password    | error                        |
      | jane@example.com   | wrong-pass  | Invalid email or password    |
      | unknown@test.com   | any-pass    | Invalid email or password    |
      | not-an-email       | any-pass    | Invalid email format         |
```

```java
@CucumberContextConfiguration
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class CucumberStepDefinitions {

    @Autowired
    private TestRestTemplate restTemplate;

    private ResponseEntity<LoginResponse> lastResponse;

    @Given("the user {string} exists with password {string}")
    public void theUserExists(String email, String password) {
        userService.createUser(email, password);
    }

    @When("I submit login with email {string} and password {string}")
    public void iSubmitLogin(String email, String password) {
        lastResponse = restTemplate.postForEntity("/auth/login",
            new LoginRequest(email, password), LoginResponse.class);
    }

    @Then("I should be redirected to the dashboard")
    public void iShouldBeRedirectedToDashboard() {
        assertThat(lastResponse.getStatusCode()).isEqualTo(HttpStatus.OK);
        assertThat(lastResponse.getBody().getRedirectUrl()).endsWith("/dashboard");
    }
}
```

---

## 12. CI Test Optimization

### Playwright Sharding

```bash
# Split test suite into 4 shards (run each in parallel CI job)
npx playwright test --shard=1/4
npx playwright test --shard=2/4
npx playwright test --shard=3/4
npx playwright test --shard=4/4

# Merge reports afterward
npx playwright merge-reports ./blob-reports --reporter html
```

### Jest / Vitest Parallelization

```bash
# Jest: run tests in parallel (default), limit workers
jest --maxWorkers=50%               # 50% of CPU cores
jest --testPathPattern="unit"      # run only unit tests
jest --runInBand                   # serial (debugging only)

# Vitest: pool configuration
# vitest.config.ts
export default defineConfig({
  test: {
    pool: 'threads',               # or 'forks' for process isolation
    poolOptions: {
      threads: { maxThreads: 8 },
    },
    sequence: {
      shuffle: true,               # detect test ordering dependencies
    },
  },
})
```

### Flaky Test Detection and Quarantine

```yaml
# GitHub Actions: retry flaky tests
- name: Run tests (with retry)
  uses: nick-fields/retry@v3
  with:
    timeout_minutes: 10
    max_attempts: 3
    command: npx playwright test

# Quarantine strategy: tag flaky tests
# @flaky annotation — run but don't fail build
# Track in Datadog/Grafana: flaky rate over time
# SLA: quarantined tests fixed within 1 sprint
```

### Code Coverage

```bash
# Jest coverage (Istanbul/V8)
jest --coverage --coverageProvider=v8
# Reports: lcov, html, text-summary

# Vitest coverage
vitest run --coverage --coverage.provider=v8
# vitest.config.ts thresholds:
coverage: {
  thresholds: {
    lines: 80,
    branches: 75,
    functions: 80,
    statements: 80,
  },
  exclude: ['**/*.test.ts', 'src/generated/**'],
}

# Python: pytest-cov
pytest --cov=myapp --cov-report=html --cov-report=term-missing \
  --cov-fail-under=80

# Go coverage
go test ./... -coverprofile=coverage.out -covermode=atomic
go tool cover -html=coverage.out -o coverage.html
go tool cover -func=coverage.out | grep total
```

**Coverage as a guide, not a goal**: 100% line coverage on code that trivially initializes objects is meaningless. Branch coverage of critical business logic is essential. MC/DC (Modified Condition/Decision Coverage) is required for safety-critical systems (DO-178C, IEC 61508).

---

## 13. Anti-Hallucination Protocol

1. **Test framework APIs change between versions**: Always verify method signatures against the installed version. `vi.spyOn` in Vitest has subtly different behavior from `jest.spyOn` in some edge cases — test it.
2. **Testcontainers withReuse**: Container reuse is a local development optimization. In CI, containers may not be reusable across parallel jobs running on different hosts — verify your CI runner architecture supports it.
3. **Playwright locator specifics**: `page.getByRole()` behavior depends on ARIA roles being correctly set in the HTML. Never assume `getByRole('button', { name: 'X' })` works without checking the DOM.
4. **Pact consumer-driven contracts**: The consumer defines the contract; the provider verifies it. Never invert this. Pact is NOT a replacement for integration testing — it tests the contract, not the behavior.
5. **k6 thresholds**: Thresholds mark a test as failed (exit code 99) but the k6 test still runs to completion. If CI interprets exit code 99 as "test crashed," configure accordingly.
6. **Hypothesis shrinking**: When Hypothesis finds a failing example, it shrinks it to the simplest case. The `assume()` function should be used sparingly — overuse causes the strategy to exhaust examples without finding failures.
7. **Stryker mutation score vs coverage**: A project can have 90% code coverage and 40% mutation score. They measure different things. Mutation score is the harder metric.
8. **go test -fuzz**: Running `go test -fuzz` in CI without `-fuzztime` will run indefinitely. Always set `-fuzztime` in CI pipelines.
9. **JUnit 5 @ExtendWith(MockitoExtension.class)**: Requires `mockito-junit-jupiter` on the classpath, not just `mockito-core`. Missing dependency causes silent initialization failures.
10. **WireMock stateful scenarios**: Scenario state is global to the WireMock instance. In parallel tests, stateful scenarios will conflict. Use `@WireMockTest` (creates isolated instance per test) not a shared static instance.

---

## 14. Self-Review Checklist

Before delivering any testing advice or test code:

- [ ] **Framework version verified** — confirm the API exists in the version in use (e.g., Vitest 1.x vs 0.x have different `vi.mock` behavior).
- [ ] **Fixtures cleaned up** — every test that creates test data has corresponding teardown (or uses transactions that roll back).
- [ ] **Parallel safety verified** — table-driven tests with `t.Parallel()` capture loop variables; Go <1.22 requires `tt := tt`.
- [ ] **Mock expectations asserted** — testify/mock tests call `repo.AssertExpectations(t)`; Mockito tests call `verifyNoMoreInteractions` where appropriate.
- [ ] **Testcontainers `withReuse` documented** — noted as development optimization only, not safe for all CI environments.
- [ ] **E2E tests use data-testid or ARIA roles** — never CSS class selectors (break with UI changes) or XPath (brittle).
- [ ] **k6 scripts include thresholds** — a k6 script without thresholds cannot fail CI. Every load test must have explicit pass/fail criteria.
- [ ] **Fuzz targets are deterministic** — the fuzz function body must not have test-external side effects; it must be deterministic for reproducibility.
- [ ] **Contract tests published to broker** — Pact consumer tests that don't publish to a Pact Broker provide no value for provider verification.
- [ ] **Coverage thresholds target branches, not just lines** — branch coverage catches uncovered conditionals; line coverage misses them.
- [ ] **Mutation testing CI threshold set** — Stryker/pitest `break` threshold causes CI failure; confirm it's set or tests are advisory only.
- [ ] **Flaky test quarantine policy documented** — "retry 3 times" without a fix deadline creates permanent technical debt.
- [ ] **Test naming follows AAA or GWT** — Arrange/Act/Assert or Given/When/Then. Tests named `test1()` or `testFoo()` are not documentation.
- [ ] **Snapshot tests have a review policy** — snapshot updates (`--updateSnapshot`) must be deliberately reviewed, not auto-committed.
