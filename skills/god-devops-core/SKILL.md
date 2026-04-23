---
name: god-devops-core
description: "God-level DevOps skill covering CI/CD pipeline design, container orchestration, infrastructure as code, GitOps, secrets management, artifact management, build systems, deployment strategies, and infrastructure automation. Use for any task involving pipelines, Docker, Terraform, Ansible, GitHub Actions, GitLab CI, Jenkins, ArgoCD, Flux, or any infrastructure automation. Never fabricates tool flags or config keys — always verifies against official docs. Treats every pipeline as a security boundary."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level DevOps Core

## Anti-Hallucination Rules (DevOps-Specific)

- NEVER invent CLI flags. If unsure of an exact flag, say so and provide the verification command.
- NEVER assume a tool version's behavior without stating the version. Terraform 0.12 vs 1.x are different worlds.
- NEVER claim a pipeline step "should work" — trace it. Every step has inputs, outputs, and failure modes.
- ALWAYS verify tool installation commands against the official installation docs for the target OS.
- NEVER hardcode credentials in pipeline files, even in examples. Always use secret references.

---

## Phase 1: DevOps Mindset

DevOps is not a toolchain. It is a discipline of **feedback acceleration** — reducing the time between a code change and verified, observable behavior in production.

Every decision must be evaluated against:
1. **MTTR** (Mean Time to Recovery) — How fast can we recover from failure?
2. **Deployment frequency** — How often can we safely ship?
3. **Change failure rate** — What % of changes cause incidents?
4. **Lead time for changes** — How long from commit to production?

These are the DORA metrics. Optimize for all four simultaneously.

---

## Phase 2: CI/CD Pipeline Design

### 2.1 Pipeline Anatomy (Non-Negotiable Stages)

```
[Source] → [Validate] → [Build] → [Test] → [Security Scan] → [Package]
         → [Publish Artifact] → [Deploy Staging] → [Integration Test]
         → [Deploy Canary] → [Smoke Test] → [Deploy Production]
         → [Post-Deploy Verification] → [Done]
```

**Every stage must**:
- Have explicit success/failure criteria
- Fail fast — no stage waits for a previous one to "probably" pass
- Be idempotent — re-running produces the same result
- Emit structured logs
- Have a timeout defined

### 2.2 Pipeline Security Rules

- Pin all action/plugin versions to SHA hash, not floating tags
  ```yaml
  # WRONG — supply chain attack vector
  uses: actions/checkout@v3
  # RIGHT — pinned to immutable SHA
  uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
  ```
- Never print environment variables in logs (`set -x` leaks secrets)
- Use OIDC for cloud authentication — never long-lived credentials in CI secrets
- Scan dependencies before building, not after
- Sign artifacts; verify signatures before deployment

### 2.3 GitHub Actions — Deep Patterns

```yaml
# Reusable workflow pattern
name: Build and Test
on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
    secrets:
      registry-token:
        required: true

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write        # for OIDC
      packages: write
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/github-actions
          aws-region: us-east-1
```

**Cache strategy**:
```yaml
- uses: actions/cache@v4
  with:
    path: |
      ~/.npm
      ~/.cache/pip
      vendor/
    key: ${{ runner.os }}-deps-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-deps-
```

### 2.4 Deployment Strategies — Choose Deliberately

| Strategy | Risk | Rollback Speed | Use Case |
|----------|------|---------------|----------|
| Recreate | High | Fast (redeploy old) | Dev/staging only |
| Rolling | Medium | Slow | Stateless services, low traffic |
| Blue/Green | Low | Instant (DNS/LB flip) | Critical services, easy rollback SLA |
| Canary | Lowest | Automatic (route traffic back) | High-risk changes, new features |
| Shadow | Zero (production unaffected) | N/A | Testing new service behavior |
| Feature Flag | Zero | Instant flag toggle | Business logic changes |

Default recommendation: **Canary + feature flags** for all production services.

---

## Phase 3: Infrastructure as Code

### 3.1 Terraform Best Practices

**State management** (non-negotiable):
```hcl
terraform {
  backend "s3" {
    bucket         = "my-tf-state"
    key            = "prod/main.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "tf-state-lock"   # Always use locking
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"              # Pin major versions
    }
  }
}
```

**Module structure**:
```
infrastructure/
├── modules/
│   ├── networking/
│   ├── compute/
│   └── database/
├── environments/
│   ├── dev/
│   ├── staging/
│   └── prod/
└── global/
```

**Drift detection**: Run `terraform plan` in CI on every PR. Alert on drift in production via scheduled plan runs.

**Checklist before every `terraform apply`**:
- [ ] `terraform fmt` passes
- [ ] `terraform validate` passes
- [ ] `tflint` passes
- [ ] `tfsec` or `checkov` passes (security scan)
- [ ] Plan reviewed by a second person for production
- [ ] State backup confirmed
- [ ] Rollback plan documented

### 3.2 GitOps Principles

- Infrastructure is declared in Git. Git is the single source of truth.
- Every change goes through PR — no manual `kubectl apply` or `aws` commands in production
- ArgoCD/Flux continuously reconciles cluster state to Git state
- Sync status is monitored and alerted on

```yaml
# ArgoCD Application
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-service
  namespace: argocd
spec:
  project: production
  source:
    repoURL: https://github.com/org/infra
    targetRevision: main
    path: apps/my-service
  destination:
    server: https://kubernetes.default.svc
    namespace: my-service
  syncPolicy:
    automated:
      prune: true           # Remove resources not in Git
      selfHeal: true        # Revert manual changes
    syncOptions:
      - CreateNamespace=true
      - PruneLast=true
```

---

## Phase 4: Container Standards

### 4.1 Dockerfile Production Rules

```dockerfile
# 1. Use official, minimal base images — pin exact version
FROM python:3.12.3-slim-bookworm AS base

# 2. Multi-stage builds — never ship build tools to production
FROM base AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM base AS production
# 3. Non-root user — always
RUN useradd --uid 1001 --no-create-home appuser
# 4. Copy only what's needed
COPY --from=builder /install /usr/local
COPY --chown=1001:1001 src/ /app/src/
WORKDIR /app
USER 1001
# 5. Read-only filesystem where possible
# 6. Health check always defined
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1
# 7. No ENTRYPOINT that runs as shell
ENTRYPOINT ["/app/bin/server"]
```

**Container scanning** (run in CI, block on critical):
```bash
trivy image --severity CRITICAL,HIGH --exit-code 1 myimage:tag
grype myimage:tag
docker scout cves myimage:tag
```

### 4.2 Secrets Management

**Never**:
- Hardcode secrets in Dockerfiles, docker-compose, or CI yaml
- Mount `.env` files into containers in production
- Use Kubernetes Secrets without encryption at rest and access control

**Always**:
- Use a secrets manager: AWS Secrets Manager, HashiCorp Vault, Doppler, Azure Key Vault
- Inject secrets as environment variables at runtime via the secrets manager SDK or sidecar
- Rotate secrets automatically; every secret has a TTL
- Audit all secret access

```bash
# Vault pattern — fetch at startup
SECRET=$(vault kv get -field=password secret/myapp/db)
```

---

## Phase 5: Build Systems & Artifact Management

### 5.1 Artifact Versioning
- Semantic versioning: `MAJOR.MINOR.PATCH`
- Git SHA tagging for every build: `myimage:sha-a1b2c3d`
- Never use `:latest` in production — it is a footgun
- Store immutable artifacts — never overwrite a released version

### 5.2 Artifact Registries
- Container: ECR, GCR, ACR, GitHub Packages, Harbor
- Packages: npm, PyPI (private: Artifactory, Nexus, CodeArtifact)
- Scan on push, scan before pull in production

---

## Phase 6: Self-Review Checklist (DevOps)

Before considering any DevOps work complete:
- [ ] Pipeline runs in < 15 minutes total (if not, identify and fix bottlenecks)
- [ ] No secrets in any code, config, or log
- [ ] All infrastructure changes are in version control
- [ ] Rollback tested — not just documented
- [ ] Observability pipeline included (metrics, logs, traces)
- [ ] Runbook written for every new deployment
- [ ] Disaster recovery scenario tested for any new stateful resource
- [ ] Cost impact of new infrastructure estimated
- [ ] Security scan passes with no critical/high findings
- [ ] Deployment does not require downtime (if it does, document and get sign-off)
