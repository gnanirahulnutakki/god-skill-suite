---
name: god-dev-codebase
description: "God-level codebase review, indexing, and audit skill. Use when reviewing, auditing, or analyzing any codebase — existing or newly written. Covers deep code indexing, multi-pass review (bugs, vulnerabilities, architecture, quality, performance, maintainability), zero-shortcut audit methodology, tool-driven analysis, and continuous self-checking. Never skips files, never assumes correctness, never takes shortcuts. Reviews for security vulnerabilities (OWASP Top 10, CWE, CVE patterns), code quality, design principle adherence, test coverage adequacy, dependency risk, and technical debt."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Codebase Review & Audit

## Prime Directives

1. **Read everything**: No file is too small to skip. Config files, Makefiles, Dockerfiles, CI pipelines — all reviewed.
2. **Trust nothing**: Every function is assumed buggy until proven correct.
3. **Never conclude early**: A clean first pass means you missed something. Run every pass.
4. **Use tools, don't rely on eyes alone**: Install and run analysis tools for every category.
5. **Document everything found**: Every issue gets a severity, file, line number, explanation, and remediation.

---

## Phase 1: Codebase Indexing

### 1.1 Initial Reconnaissance
Before reviewing any code, map the terrain:

```bash
# Understand structure
find . -type f | head -100           # What files exist?
find . -name "*.go" | wc -l          # How many source files?
wc -l $(find . -name "*.py") | tail  # Total lines of code?
git log --oneline -20                # Recent commit history
git shortlog -sn --no-merges         # Who wrote what?
```

**Inventory checklist**:
- [ ] Language(s) and runtimes
- [ ] Dependency management (package.json, go.mod, requirements.txt, Cargo.toml, pom.xml)
- [ ] Build system (Make, Gradle, Bazel, CMake)
- [ ] CI/CD pipelines (GitHub Actions, Jenkins, CircleCI)
- [ ] Container / deployment config (Dockerfile, Helm charts, Kubernetes manifests)
- [ ] Infrastructure as code (Terraform, Pulumi, CDK)
- [ ] Test framework and structure
- [ ] Configuration and secrets management
- [ ] External integrations and APIs

### 1.2 Architecture Mapping
Understand the system before reading the code:

1. Draw (even mentally) the component diagram: What services/modules exist?
2. Draw the data flow: How does data enter, transform, and exit?
3. Identify the trust boundaries: Where does untrusted input enter? Where are privileged operations?
4. Identify the critical path: What code runs on every request?
5. Identify shared state: Databases, caches, queues, global variables

**Questions to answer**:
- What is the entry point(s)?
- What are the external dependencies?
- What data is persisted? Where? How?
- What are the authentication and authorization boundaries?
- What calls external services? Is that list complete?

### 1.3 Dependency Inventory
```bash
# Node.js
npm ls --all
npm audit

# Python
pip list
pip-audit
safety check

# Go
go list -m all
govulncheck ./...

# Java/Maven
mvn dependency:tree
mvn dependency-check:check

# Rust
cargo tree
cargo audit

# Ruby
bundle list
bundle-audit check --update

# Generic
trivy fs .                    # Multi-language vulnerability scan
syft . -o table               # SBOM generation
```

Flag any dependency:
- With known CVEs (critical or high severity)
- Abandoned (no commits in 2+ years, no response to issues)
- With extremely broad permissions for its stated purpose
- That is a transitive dependency doing something surprising

---

## Phase 2: Multi-Pass Code Review

Run all passes. Do NOT skip because a previous pass seemed clean.

---

### Pass 1: Correctness Review

**Methodology**: Read every function. For each function, mentally execute it.

Checklist for every function:
- [ ] Does it do what its name says, and ONLY that?
- [ ] Is the return value always defined? (null pointer dereference, uninitialized return)
- [ ] Are all error paths handled? (not just logged — handled)
- [ ] Are all loop termination conditions correct? (off-by-one, infinite loops)
- [ ] Is integer arithmetic safe? (overflow, underflow, division by zero)
- [ ] Are type conversions explicit and safe? (implicit narrowing, signed/unsigned)
- [ ] Are all allocated resources freed? (memory leaks, file handle leaks, connection leaks)
- [ ] Are concurrent modifications guarded? (race conditions, TOCTOU)
- [ ] Is state mutation visible to all callers that need to observe it?
- [ ] Are all external inputs validated before use?

**Tool support**:
```bash
# Static analysis — run ALL of these
# Go
go vet ./...
staticcheck ./...
errcheck ./...
golangci-lint run

# Python
pylint <src>
mypy <src>
pyflakes <src>

# JavaScript/TypeScript
eslint . --ext .js,.ts
tsc --noEmit

# Java
spotbugs -textui <jar>
pmd check -d src -R rulesets/java/quickstart.xml

# C/C++
clang-tidy <files>
cppcheck --enable=all <src>
scan-build make

# Rust (most is built-in)
cargo clippy -- -D warnings
cargo check
```

---

### Pass 2: Security Audit

#### 2.1 OWASP Top 10 Checklist (for every web-facing codebase)

**A01 — Broken Access Control**
- [ ] Are authorization checks present at EVERY endpoint that handles privileged data or actions?
- [ ] Are checks done server-side, not client-side only?
- [ ] Is there path traversal risk? (`../../../etc/passwd` style)
- [ ] Can authenticated users access other users' data by changing IDs?
- [ ] Are CORS headers configured restrictively?
- [ ] Are insecure direct object references avoided?

**A02 — Cryptographic Failures**
- [ ] Is sensitive data encrypted at rest? (PII, credentials, tokens)
- [ ] Is sensitive data encrypted in transit? (TLS everywhere, no HTTP fallback)
- [ ] Are weak algorithms used? (MD5, SHA1, DES, RC4 — all forbidden)
- [ ] Are secret keys hardcoded? (search codebase for entropy-looking strings)
- [ ] Are random values cryptographically secure? (`/dev/urandom`, `crypto/rand`, not `math/rand`)
- [ ] Are private keys and certificates stored securely?
- [ ] Is sensitive data logged? (passwords, tokens, PII in logs is a breach)

**A03 — Injection**
- [ ] SQL: Are all queries parameterized? Search for string concatenation in queries.
- [ ] NoSQL: Are MongoDB/Redis queries using untrusted input safely?
- [ ] Command injection: Is `exec()`, `system()`, `subprocess` used with user input?
- [ ] LDAP injection: Are LDAP queries parameterized?
- [ ] XML injection: Is XML parsed from untrusted sources with external entities disabled (XXE)?
- [ ] Template injection: Are templates rendered with user-controlled strings?

```bash
# Automated injection scanners
semgrep --config=auto .           # Broad pattern matching
bandit -r . -ll                   # Python security scanner
gosec ./...                       # Go security scanner
nodejsscan --directory .          # Node.js scanner
brakeman -A .                     # Ruby on Rails scanner
```

**A04 — Insecure Design**
- [ ] Is there threat modeling documentation?
- [ ] Are security requirements defined per feature?
- [ ] Is there rate limiting on authentication and API endpoints?
- [ ] Is account lockout implemented?

**A05 — Security Misconfiguration**
- [ ] Are default credentials changed?
- [ ] Are debug/development configs disabled in production?
- [ ] Are unnecessary features/ports/services disabled?
- [ ] Are error messages generic (not revealing stack traces to users)?
- [ ] Are HTTP security headers set? (CSP, HSTS, X-Frame-Options, etc.)

**A06 — Vulnerable Components**
- Already covered in dependency audit (Phase 1.3)
- [ ] Are dependencies pinned to exact versions?
- [ ] Is there a process for updating dependencies?

**A07 — Authentication & Identification Failures**
- [ ] Is password complexity enforced?
- [ ] Are passwords hashed with bcrypt/scrypt/argon2? (never SHA or MD5)
- [ ] Is MFA supported for privileged accounts?
- [ ] Are session tokens cryptographically random and sufficiently long?
- [ ] Are sessions invalidated on logout?
- [ ] Is there protection against credential stuffing?

**A08 — Software & Data Integrity**
- [ ] Is CI/CD pipeline secured against tampering?
- [ ] Are artifacts signed and verified?
- [ ] Are deserialization inputs validated? (Java deserialization RCE, pickle, etc.)

**A09 — Security Logging**
- [ ] Are authentication successes/failures logged?
- [ ] Are authorization failures logged?
- [ ] Are logs tamper-resistant?
- [ ] Are logs monitored/alerted?
- [ ] Is PII excluded from logs?

**A10 — SSRF (Server-Side Request Forgery)**
- [ ] Does the app make HTTP requests based on user-supplied URLs?
- [ ] Are those URLs validated against an allowlist?
- [ ] Are internal/metadata endpoints blocked? (169.254.169.254, localhost, etc.)

#### 2.2 Secret Scanning
```bash
# Install and run multiple secret scanners
trufflehog filesystem --directory=. --only-verified
gitleaks detect --source . -v
detect-secrets scan --all-files

# Manual patterns to grep for
grep -r "password\s*=\s*['\"]" . --include="*.py" --include="*.js" --include="*.go"
grep -r "api_key\s*=\s*['\"]" . 
grep -r "secret\s*=\s*['\"]" .
grep -r "BEGIN.*PRIVATE KEY" .
grep -r "AKIA[0-9A-Z]{16}" .    # AWS Access Key pattern
grep -r "ghp_[a-zA-Z0-9]{36}" . # GitHub PAT pattern
```

#### 2.3 CWE Top 25 Most Dangerous
Check for evidence of each in every codebase:
- CWE-787: Out-of-bounds write
- CWE-79: XSS (reflected, stored, DOM)
- CWE-125: Out-of-bounds read
- CWE-20: Improper input validation
- CWE-78: OS command injection
- CWE-416: Use after free
- CWE-22: Path traversal
- CWE-89: SQL injection
- CWE-352: CSRF
- CWE-434: Unrestricted file upload
- CWE-476: NULL pointer dereference
- CWE-502: Deserialization of untrusted data
- CWE-190: Integer overflow
- CWE-287: Improper authentication
- CWE-798: Hardcoded credentials

---

### Pass 3: Architecture & Design Review

- [ ] Does the high-level design match the implementation? (design drift)
- [ ] Are SOLID principles followed? (check for god classes, tight coupling)
- [ ] Is there circular dependency between modules?
- [ ] Are domain concepts properly separated from infrastructure? (clean architecture)
- [ ] Is configuration externalized properly? (12-factor app principle)
- [ ] Are there any distributed system anti-patterns? (synchronous chains, no retry, no timeout, no circuit breaker)
- [ ] Is the API design RESTful/idiomatic? (proper HTTP methods, status codes, versioning)
- [ ] Are events/messages idempotent (safe to deliver more than once)?
- [ ] Is there proper schema validation at API boundaries?

**Tool support**:
```bash
# Dependency analysis
# Python
pydeps <module> --max-bacon=3
# Java
jdeps --multi-release 11 <jar>
# Go
godepgraph ./... | dot -Tpng > deps.png
# JavaScript
madge --image deps.png src/
depcruise --include-only "^src" --output-type dot src | dot -T svg > deps.svg
```

---

### Pass 4: Performance Review

- [ ] Are there N+1 query patterns? (loop calling DB/API per iteration)
- [ ] Are database queries indexed for their access patterns?
- [ ] Is there unnecessary data loaded from DB that isn't used?
- [ ] Are there large memory allocations in hot paths?
- [ ] Is there blocking I/O on threads that serve requests?
- [ ] Are there large object copies where references would suffice?
- [ ] Is caching used appropriately? (TTL, invalidation strategy, stampede protection)
- [ ] Are there CPU-intensive operations that could be offloaded or cached?
- [ ] Are connection pools sized appropriately?
- [ ] Is pagination implemented for list endpoints?

**Tool support**:
```bash
# Profiling
go tool pprof cpu.prof        # Go CPU profile
py-spy top -- python app.py   # Python live profiler
async-profiler                # Java profiler
perf stat ./binary            # Linux system profiler
flamegraph.pl                 # Visualize profiling output

# Database
EXPLAIN ANALYZE <query>       # PostgreSQL query plan
pt-query-digest               # MySQL slow query analysis
```

---

### Pass 5: Test Coverage & Quality

```bash
# Coverage measurement
go test -coverprofile=coverage.out ./... && go tool cover -html=coverage.out
pytest --cov=src --cov-report=html
nyc --reporter=html npm test
mvn jacoco:report
cargo tarpaulin --out Html

# Mutation testing (finds tests that don't actually test)
pitest (Java)           # mvn org.pitest:pitest-maven:mutationCoverage
mutmut run (Python)     # mutmut run && mutmut results
stryker-mutator (JS)    # npx stryker run
```

Review:
- [ ] Is coverage above 80% for business logic? (100% for security-critical paths)
- [ ] Are there tests for every error path, not just the happy path?
- [ ] Are there integration tests for every external dependency?
- [ ] Do tests test behavior, or just call methods? (behavior testing vs structural testing)
- [ ] Are there flaky tests? (tests that sometimes pass, sometimes fail — delete or fix)
- [ ] Are test fixtures realistic, or trivially simple? (trivial inputs miss real bugs)

---

### Pass 6: Code Quality & Maintainability

```bash
# Code quality metrics
# Cognitive/Cyclomatic complexity
radon cc -s -a src/          # Python complexity
gocyclo -over 10 ./...       # Go complexity
eslint --rule 'complexity: [error, 10]' src/

# Duplication detection
jscpd --min-tokens 50 src/   # Detect copy-paste code
PMD CPD (Java)               # pmd cpd --minimum-tokens 100 --files src

# Code style
black --check src/           # Python formatting
gofmt -l .                   # Go formatting
prettier --check "src/**/*.ts"
```

Review:
- [ ] Are function names verbs that describe behavior? (`processPayment` not `payment`)
- [ ] Are class/struct names nouns? (`PaymentProcessor` not `ProcessPayment`)
- [ ] Is there commented-out code? (delete it — version control preserves history)
- [ ] Are magic numbers named constants?
- [ ] Is nesting depth >3? (extract function)
- [ ] Are there any `TODO`/`FIXME`/`HACK` comments? (catalogue and prioritize)
- [ ] Is the README accurate and complete?
- [ ] Is the API documented?
- [ ] Are breaking changes documented?

---

## Phase 3: Issue Reporting Standard

Every issue found must be reported with:

```
## Issue: [SEVERITY] Short Title

**Category**: [Bug | Security | Performance | Quality | Architecture | Test]
**Severity**: [Critical | High | Medium | Low | Info]
**File**: path/to/file.go
**Line**: 42-67
**CWE/CVE**: CWE-89 (if applicable)

### Description
What is wrong and why it matters.

### Evidence
```code snippet showing the issue```

### Impact
What can happen if this is not fixed? Who is affected?

### Remediation
Specific, actionable fix with code example.

### References
- Link to documentation, CVE, paper explaining why this is a problem
```

**Severity definitions**:
- **Critical**: Remote code execution, authentication bypass, data breach possible — fix before any deployment
- **High**: Significant security or data integrity risk, major correctness bug — fix before next release
- **Medium**: Security hardening, performance degradation, incorrect behavior in edge cases
- **Low**: Code quality, maintainability, non-security best practices
- **Info**: Observations, suggestions, optional improvements

---

## Phase 4: Self-Check After Review

After completing all passes, ask yourself:
1. Did I read EVERY file, or did I skip "boring" ones like config files? (skip nothing)
2. Did I run ALL the tools, or did I rely on manual reading alone?
3. Did I check the CI/CD pipeline itself for security issues?
4. Did I check the Dockerfile / deployment config for misconfigurations?
5. Did I check git history for accidentally committed secrets?
6. Did I look at every external dependency for known vulnerabilities?
7. Did I test my understanding by tracing a real request end-to-end through the code?

If the answer to any of these is "no" — go back and do it.
