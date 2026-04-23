---
name: god-platform-engineering
description: "God-level platform engineering skill covering Internal Developer Platforms (IDPs), golden paths, Backstage (software catalog, TechDocs, scaffolder templates, plugins), developer experience (DX) measurement, self-service infrastructure, paved roads vs off-road, platform as a product mindset, GitOps at scale, multi-tenancy patterns, namespace-as-a-service, environment management, developer cognitive load reduction, platform team topologies (Team Topologies book), and building platforms that accelerate every other engineering team. A platform engineer who understands ML, backend, DevOps, and security builds platforms that serve all of them. Never fabricates Backstage plugin names or Kubernetes CRD fields."
metadata:
  version: "\"1.0\""
---

# God-Level Platform Engineering

> You are a researcher-warrior. You build the roads every other team drives on. Your job is not to write product code — it is to eliminate the friction that slows product teams down. You know that a poorly designed abstraction wastes more engineering time than the operational complexity it was meant to hide. Every decision you make is backed by data, developer surveys, DORA metrics, and a relentless focus on cognitive load reduction. When you don't know a Backstage plugin name or a Kubernetes CRD field, you say so and look it up — you never invent it.

---

## 1. What Platform Engineering Actually Is

Platform engineering is the discipline of designing and building self-service internal platforms that reduce the cognitive load on product teams. The platform team produces a curated set of capabilities — golden paths, templates, tools, and workflows — so that stream-aligned teams can build, test, deploy, and operate software without waiting on other teams or deeply understanding infrastructure.

The core value proposition is cognitive load reduction. Every hour a product engineer spends debugging Kubernetes YAML, configuring observability pipelines, or chasing IAM permissions is an hour not spent on product. The platform eliminates these taxes.

**What a platform is NOT:**
- Not just a Kubernetes cluster with a README
- Not a shared CI/CD system with a Confluence page
- Not a set of Terraform modules in a repo nobody maintains
- Not infrastructure-as-a-service where every team must still do heavy lifting

**What a platform IS:**
- A product with a roadmap, SLAs, and developer-customers
- A collection of self-service capabilities accessible via APIs, UIs, or CLIs
- An abstraction layer that enforces standards without being a bottleneck
- A living system that evolves based on developer feedback

---

## 2. Team Topologies: The Organizational Foundation

*Team Topologies* (Skelton & Pais, 2019) provides the vocabulary and mental model for how platform teams fit into the engineering organization. Get this right before designing any technical system.

### Four Fundamental Team Types

| Team Type | Purpose | Owns | Example |
|-----------|---------|------|---------|
| **Stream-aligned** | Deliver value to end users along a flow of work | A slice of the business domain end-to-end | Payments team, Search team |
| **Platform** | Provide a compelling internal product to accelerate stream-aligned teams | The internal platform itself | Developer platform team, Data platform team |
| **Enabling** | Temporarily boost capabilities in other teams, then move on | A domain of expertise shared temporarily | Site Reliability, Security enablement |
| **Complicated-subsystem** | Handle components requiring deep specialist knowledge | A specific high-complexity system | ML model serving infrastructure, cryptography |

### Three Interaction Modes

- **X-as-a-Service**: One team provides, another consumes with minimal interaction. Clear boundaries. Low collaboration overhead. This is the target state for a mature platform team — stream-aligned teams consume the platform as a service.
- **Collaboration**: High-bandwidth working together for a defined period to discover new patterns. Used when building new platform capabilities with a pilot team.
- **Facilitation**: Enabling team helps another team overcome an obstacle, then steps away. Not permanent; the goal is to transfer capability.

### Implications for Platform Teams

A platform team runs its primary interaction with stream-aligned teams as **X-as-a-Service**. This means:
1. The interface must be stable and versioned
2. Documentation must be self-contained (TechDocs, runbooks)
3. The platform team must not become a bottleneck or approval gate
4. Stream-aligned teams must be able to provision resources without filing tickets

When the platform team is a bottleneck, it is operating as a complicated-subsystem team, not a platform team — a critical failure mode.

---

## 3. Internal Developer Platform (IDP): Core Capabilities

An IDP is not a single tool. It is the sum of capabilities the platform team provides. The CNCF's Platforms White Paper identifies core capabilities:

### Five Core IDP Capability Areas

1. **Application configuration management** — templated service configs, environment-specific overrides, secret injection patterns
2. **Infrastructure orchestration** — self-service databases, queues, storage; provisioned via APIs, not tickets
3. **Development environments** — standardized local dev setup, remote dev environments, ephemeral PR environments
4. **Application lifecycle management** — deployment pipelines, promotion workflows, rollback mechanisms
5. **Observability access** — pre-wired dashboards, traces, logs per service; no manual instrumentation required

### The Golden Rule
If a developer has to ask the platform team for something that happens more than once a month, it should be self-service.

---

## 4. Backstage: Architecture and Implementation

Backstage is an open platform for building developer portals, created by Spotify and donated to the CNCF. It is **not** an IDP out-of-the-box — it is a framework for building one.

### Architectural Components

```
┌─────────────────────────────────────────────────────────┐
│                    Backstage Frontend                    │
│  ┌──────────┐ ┌───────────┐ ┌────────┐ ┌───────────┐  │
│  │ Catalog  │ │ Scaffolder│ │TechDocs│ │  Plugins  │  │
│  └──────────┘ └───────────┘ └────────┘ └───────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │ REST / GraphQL
┌──────────────────────────▼──────────────────────────────┐
│                   Backstage Backend                      │
│  ┌──────────┐ ┌───────────┐ ┌────────┐ ┌───────────┐  │
│  │ Catalog  │ │ Scaffolder│ │TechDocs│ │   Proxy   │  │
│  │  (DB)   │ │  Actions  │ │Builder │ │           │  │
│  └──────────┘ └───────────┘ └────────┘ └───────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Software Catalog**: Central registry of all software components, APIs, infrastructure resources, teams, and services. Populated via `catalog-info.yaml` files in repositories, discovered automatically via entity providers (GitHub org discovery, LDAP group sync, etc.).

**Scaffolder (Software Templates)**: Allows teams to create new services from templates. Templates define parameters (form inputs), steps (fetch skeleton, publish to GitHub, register in catalog, create PagerDuty service), and produce fully-configured repositories with CI pipelines, observability, and catalog registration wired in from day zero.

**TechDocs**: Docs-as-code built into Backstage. Markdown files live alongside code (`docs/` directory), a `mkdocs.yml` file configures the site, and Backstage builds and serves them. Developers read documentation in the same portal they use for everything else — no Confluence sprawl.

**Proxy**: Backstage's built-in HTTP proxy for backend plugins that need to communicate with external services (e.g., PagerDuty, CircleCI, SonarQube) without exposing credentials to the browser or triggering CORS errors.

**Plugins**: The extension model. Each plugin is a package (frontend, backend, or both). Frontend plugins render UI. Backend plugins run server-side logic. Plugin interaction modes:
- **Standalone**: Entirely browser-rendered (e.g., Tech Radar)
- **Service backend**: Calls an internal service (e.g., Software Catalog)
- **Third-party backend via proxy**: Calls an external service through the proxy (e.g., CircleCI, PagerDuty)

> **Anti-hallucination rule**: Do not invent Backstage plugin names. Verified community plugins exist at https://backstage.io/plugins. Before referencing a plugin in a recommendation, confirm it exists there.

### Software Catalog Entity Kinds

All entities use the same envelope:
```yaml
apiVersion: backstage.io/v1alpha1
kind: <Kind>
metadata:
  name: my-service          # required, [a-z0-9A-Z-_.], max 63 chars
  namespace: default         # optional, defaults to "default"
  description: "..."
  labels: {}
  annotations: {}
  tags: []
spec:
  ...                        # varies by kind
```

| Kind | Purpose | Key `spec` fields |
|------|---------|-------------------|
| `Component` | A deployable piece of software | `type` (service/website/library), `lifecycle` (production/experimental/deprecated), `owner`, `system`, `providesApis`, `consumesApis`, `dependsOn` |
| `API` | An interface provided by a Component | `type` (openapi/asyncapi/graphql/grpc), `lifecycle`, `owner`, `definition` |
| `Resource` | Infrastructure a Component depends on | `type` (database/s3-bucket/kubernetes-cluster), `owner`, `system`, `dependsOn` |
| `System` | A collection of Components and Resources | `owner`, `domain` |
| `Domain` | A collection of Systems (business area) | `owner` |
| `Group` | An organizational unit | `type` (team/business-unit), `parent`, `children`, `members` |
| `User` | An individual | `memberOf` |

### Scaffolder Template Anatomy

```yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: python-service-template
  title: Python Microservice
  description: Creates a Python FastAPI service with CI, observability, and catalog registration
  tags: [python, backend, recommended]
spec:
  owner: platform-team
  type: service
  parameters:
    - title: Service Information
      required: [name, owner]
      properties:
        name:
          type: string
          title: Service Name
        owner:
          type: string
          title: Owning Team
          ui:field: OwnerPicker
  steps:
    - id: fetch-template
      name: Fetch Template
      action: fetch:template
      input:
        url: ./skeleton
        values:
          name: ${{ parameters.name }}
    - id: publish
      name: Publish to GitHub
      action: publish:github
      input:
        repoUrl: github.com?owner=myorg&repo=${{ parameters.name }}
    - id: register
      name: Register in Catalog
      action: catalog:register
      input:
        repoContentsUrl: ${{ steps['publish'].output.repoContentsUrl }}
        catalogInfoPath: /catalog-info.yaml
```

> The `action:` identifiers (e.g., `fetch:template`, `publish:github`, `catalog:register`) are official Backstage scaffolder built-in actions. Do not invent custom action names — verify custom actions are registered in the scaffolder backend before using them.

---

## 5. Golden Paths: Design and Enforcement

A golden path is the recommended, well-maintained, well-documented way to accomplish a common task. It is the "happy path" the platform team paves and maintains.

### What Makes a Good Golden Path

- **Reduces decisions**: Developers don't choose between 5 logging libraries — the golden path gives them one that's pre-integrated with the observability stack
- **Opinionated but documented**: The opinion is visible and the reasoning is documented in TechDocs
- **Accelerates the default case**: Starting a new Python service via a scaffolder template takes 5 minutes; doing it manually takes 5 hours
- **Composable**: Golden paths for sub-components (database, queue, cache) compose into a full service golden path

### Paved Roads vs. Off-Road

The platform should not be a wall — it should be a road. Teams that have legitimate reasons to go off-road should be able to, but with guardrails:

| Scenario | Platform Response |
|----------|------------------|
| Team follows golden path exactly | Zero friction, full support |
| Team needs minor variation (different DB version) | Supported via golden path parameters |
| Team needs significant deviation (different language) | Off-road with documented support contract — they own it |
| Team ignores security requirements | Non-negotiable enforcement via policy (OPA, Kyverno) |

**Guardrails for off-road teams:**
- Admission controllers (OPA Gatekeeper, Kyverno) enforce mandatory security policies regardless of which path was taken
- Resource quotas and LimitRanges apply to all namespaces
- Mandatory tagging enforced at the infrastructure layer
- Off-road teams get no SLA from the platform team on their custom stack

---

## 6. Self-Service Infrastructure

### Crossplane: Infrastructure via Kubernetes CRDs

Crossplane extends Kubernetes to provision external cloud resources (RDS databases, S3 buckets, GCP Cloud SQL, Azure Resource Groups) as Kubernetes custom resources. The key concepts:

- **Provider**: A Crossplane package that knows how to talk to a cloud API (e.g., `provider-aws`, `provider-gcp`, `provider-azure`)
- **Managed Resource (MR)**: A CRD that directly maps to one cloud resource (e.g., an `RDSInstance` CR that creates an AWS RDS instance)
- **Composite Resource (XR)**: A custom CRD that composes multiple Managed Resources into a higher-level abstraction (e.g., an `AppDatabase` that creates an RDS instance + parameter group + subnet group)
- **Composition**: The definition of how an XR is implemented — maps XR fields to MR fields
- **Claim**: A namespace-scoped version of an XR that developers submit (they don't need cluster-admin access)

**Developer workflow with Crossplane:**
```
Developer applies a Claim (e.g., AppDatabase) in their namespace
  → Crossplane creates the XR
  → Composition maps XR to Managed Resources
  → Providers create actual cloud resources (RDS, etc.)
  → Connection details injected as a Kubernetes Secret in developer's namespace
```

This is self-service infrastructure that respects namespace boundaries and requires no tickets to the platform team.

### Terraform Cloud / HCP Terraform for Self-Service

- **Workspaces** as the unit of self-service: one workspace per team/environment/service
- **No-code workflows**: Terraform Cloud can expose a module as a self-service form
- **Policy as Code**: Sentinel or OPA policies enforce guardrails on Terraform plans before apply
- **VCS-driven**: Changes require a PR, providing auditability

### Port.io as an Alternative Portal

Port is a commercial developer portal alternative to Backstage. It provides a software catalog, self-service actions, and scorecards without requiring a frontend engineering team to build and maintain a Backstage instance. Consider Port when:
- Engineering bandwidth for maintaining a Backstage deployment is limited
- The team needs a commercial SLA and support contract
- Rapid time-to-value is higher priority than full customizability

---

## 7. Multi-Tenancy in Kubernetes

Multi-tenancy patterns determine how multiple teams share a Kubernetes cluster safely.

### Pattern 1: Namespace-per-Team

Each team gets one or more namespaces. Isolation is achieved via RBAC (teams can only `get`/`create`/`delete` resources in their namespaces), NetworkPolicies (pods in team-A namespace cannot talk to team-B pods unless explicitly allowed), and ResourceQuotas (enforce CPU/memory limits per namespace).

**Namespace-as-a-Service**: The platform team provides a self-service mechanism (Backstage action, kubectl plugin, or Crossplane claim) for teams to request namespaces. On request, the platform provisions: namespace, RBAC RoleBindings, NetworkPolicy defaults, ResourceQuota, LimitRange, and registers the namespace in the catalog.

### Pattern 2: Namespace-per-Environment

A team gets a namespace per environment: `payments-dev`, `payments-staging`, `payments-prod`. Simpler mental model for smaller teams. Risk: environment sprawl if teams have many services.

### Pattern 3: Virtual Clusters (vcluster)

vcluster (by Loft Labs) runs a full Kubernetes control plane (API server, etcd) inside a namespace of a host cluster. Tenants get a complete Kubernetes experience — they can install CRDs, create cluster-scoped resources, and have admin access — without access to the host cluster.

Use vcluster when:
- Teams need to install their own CRDs (e.g., ML operators, database operators)
- Teams need cluster-admin access for testing or development
- CI/CD pipelines need isolated, ephemeral clusters per PR

### Pattern 4: Hierarchical Namespace Controller (HNC)

HNC (a Kubernetes SIG project) allows namespaces to have parent-child relationships. Policies (RBAC, NetworkPolicies) defined in a parent namespace propagate to children. Useful for organizing `payments` (parent) → `payments-dev`, `payments-staging`, `payments-prod` (children) with shared RBAC.

> **Anti-hallucination**: HNC is a real Kubernetes SIG project (sig-multitenancy). Do not confuse its CRDs with any other project. The primary CRD is `HierarchyConfiguration`.

---

## 8. Environment Management

### Environment Promotion Pipeline

```
Developer Branch → PR → Ephemeral Environment (auto-created)
  → Merge to main → Dev environment (auto-deployed)
    → Promotion gate (tests + approval) → Staging
      → Promotion gate (integration tests) → Production
```

Each promotion gate should be automated where possible. Manual gates belong only where regulatory or business approval is genuinely required.

### Environment Parity

Dev, staging, and production should be as similar as possible:
- Same Kubernetes version
- Same infrastructure topology (different scale, not different architecture)
- Same secrets management approach (different secrets, same pattern)
- Same observability stack wired up

Divergence between environments is a primary source of "works in staging, fails in prod" incidents.

### Ephemeral Environments for PRs

Every PR gets a fully functional environment (sometimes called a Preview Environment or Review App). Teardown on PR close. Implementation options:
- **ArgoCD ApplicationSets** with a PR generator that creates an Application per open PR
- **Argo Workflows / Tekton** that provision and destroy environments as pipeline steps
- **Namespace-per-PR** approach for lightweight environments

The platform team owns the mechanism; product teams get ephemeral environments for free.

---

## 9. Developer Experience Measurement

Never guess what developers need — measure it.

### DORA Metrics (Updated)

DORA's research has evolved. The current framework (as of 2024 research cycle) includes five metrics across two categories:

**Throughput metrics:**
- **Change lead time**: Time from commit to production deployment
- **Deployment frequency**: Number of deployments per unit time (or inverse: time between deployments)
- **Failed deployment recovery time**: Time to recover from a deployment that requires immediate intervention

**Instability metrics:**
- **Change fail rate**: Ratio of deployments requiring immediate intervention
- **Deployment rework rate**: Ratio of unplanned deployments caused by production incidents

High-performing organizations (per DORA research): deploy multiple times per day, have lead times under one hour, recover in under one hour, and have change fail rates below 5%.

### SPACE Framework

SPACE (Satisfaction, Performance, Activity, Communication/Collaboration, Efficiency) provides a multi-dimensional view of developer productivity. Use SPACE to avoid optimizing solely on throughput metrics at the expense of developer wellbeing.

- **Satisfaction**: Developer NPS, burnout surveys, tool satisfaction scores
- **Performance**: Quality outcomes — reliability, security posture, customer impact
- **Activity**: Deployments, PRs, code reviews (useful context, not primary signal)
- **Communication/Collaboration**: Code review turnaround, PR review coverage, on-call rotation health
- **Efficiency**: Flow time, context switching frequency, meeting load

### Platform-Specific Metrics

| Metric | What It Measures | How to Collect |
|--------|-----------------|----------------|
| Golden path adoption rate | % of services using recommended templates/patterns | Catalog + CI metadata |
| Self-service success rate | % of self-service actions that complete without platform team intervention | Platform action logs |
| Provisioning time | Time from resource request to resource ready | Crossplane/Terraform job duration |
| Time to first deployment (new service) | Onboarding speed for new teams/services | Scaffolder + deployment timestamps |
| Platform NPS | Developer satisfaction with the platform | Quarterly survey |
| Documentation coverage | % of catalog entities with linked TechDocs | Catalog API query |

---

## 10. Platform as a Product

### The Product Mindset

A platform team that operates without a product mindset builds tools nobody uses. Treat developers as customers:

- **Platform roadmap**: Quarterly priorities, public to all engineering
- **Platform NPS**: Quarterly survey. "On a scale of 0-10, how likely are you to recommend the platform to a colleague at another company?"
- **Platform SLAs**: Define and publish. "Self-service database provisioning: p99 < 5 minutes." "Scaffolder template execution: p95 < 3 minutes."
- **Platform office hours**: Weekly sessions where product teams can ask questions without filing tickets
- **Pilot programs**: Embed platform engineers in stream-aligned teams for 2-week discovery sprints before building new capabilities
- **Deprecation policy**: When removing capabilities, provide migration guides and a 90-day window

### Platform Roadmap Prioritization

Prioritize based on:
1. Number of teams blocked by the missing capability
2. Engineering hours lost per week across all affected teams
3. Security or compliance risk of the current state
4. Golden path adoption blocker

---

## 11. Cognitive Load Reduction

### Types of Cognitive Load (John Sweller's Model Applied to Engineering)

- **Intrinsic load**: The inherent complexity of the problem (understanding distributed transactions, ML model evaluation). Cannot be eliminated.
- **Extraneous load**: Complexity imposed by tools, processes, and environment. Should be eliminated or minimized.
- **Germane load**: Load that leads to learning and skill building. Should be balanced.

The platform team's job is to minimize extraneous cognitive load — the YAML configuration, the IAM policy debugging, the Dockerfile optimization.

### Warning Signs of Over-Abstraction

An abstraction that creates new cognitive load is worse than no abstraction:
- Developers must learn the platform's own DSL before they can do anything
- Error messages from the platform are cryptic and don't point to solutions
- Debugging failures requires understanding the abstraction internals
- The abstraction leaks: developers end up needing to know both layers

**Good abstraction test**: A new engineer can provision a database and deploy a service on day one, without reading more than one document, without filing a ticket, and without understanding Kubernetes internals.

---

## 12. Observability for the Platform Itself

The platform must be observable, not just the product services it hosts.

### Platform-Level SLOs

Define SLOs for the platform as a product:

```yaml
# Example platform SLO definitions
slo:
  name: self-service-provisioning-success-rate
  description: "Percentage of self-service resource requests that succeed without platform team intervention"
  target: 99.5%
  window: 30d

slo:
  name: scaffolder-template-execution-latency
  description: "p95 scaffolder template execution time"
  target: 3 minutes
  window: 7d

slo:
  name: catalog-freshness
  description: "% of entities last refreshed within 24 hours"
  target: 99%
  window: 1d
```

### Inner Loop vs. Outer Loop

- **Inner loop**: The local development cycle — write code, run tests, iterate. Platform impact: dev container standards, Tilt/Skaffold integration, local cluster tooling (kind, minikube, k3d).
- **Outer loop**: The CI/CD and deployment cycle — PR, CI, staging, production. Platform impact: pipeline templates, deployment mechanisms, promotion workflows.

Optimizing only the outer loop misses a large fraction of developer time. Fast inner loops (hot reload, local service mesh emulation) are as valuable as fast CI.

---

## 13. Cross-Domain Knowledge Requirements

A platform engineer who only knows Kubernetes builds a platform for DevOps engineers, not for everyone.

### ML Platform Requirements

ML teams need:
- GPU node pools with autoscaling (KEDA, Karpenter with GPU node class)
- Jupyter notebook environments (ephemeral, GPU-backed, cost-controlled)
- Model registry integration (MLflow, Weights & Biases)
- Training job submission via Kubernetes Jobs or Kubeflow
- Feature store access (Feast, Tecton)
- Inference serving infrastructure (Triton, Ray Serve, KServe)

The platform's golden path for ML must address all of these with self-service mechanisms. A platform engineer who can't articulate the difference between training and inference jobs cannot design the right abstractions.

### Security Requirements Built Into Golden Paths

Security must be embedded, not bolted on:
- Container image scanning in CI (Trivy, Grype) — mandatory in the scaffolder pipeline template
- SBOM generation (Syft) — integrated into the build
- Secret management via Kubernetes External Secrets Operator + Vault/AWS Secrets Manager (no hardcoded secrets)
- Pod Security Standards (Baseline or Restricted profile) enforced via admission controller
- Network policies generated by the namespace-as-a-service mechanism

### FinOps Requirements

Platform engineers expose cost to developers:
- Namespace-level cost dashboards (Kubecost) visible to each team in Backstage
- Cost as a first-class field in self-service forms ("estimated monthly cost: $X" shown before provisioning)
- Spot instance defaults for non-production workloads (enforced via namespace labels triggering node affinity)
- Resource request/limit guidance built into scaffolder templates

---

## 14. GitOps at Scale

### GitOps Principles

1. **Declarative**: Desired state expressed in Git
2. **Versioned and immutable**: History in Git; rollback by reverting a commit
3. **Pulled automatically**: The cluster pulls state from Git (ArgoCD, Flux), not pushed by CI
4. **Continuously reconciled**: If the cluster drifts from Git state, it is corrected

### ArgoCD at Scale

- **Application of Applications pattern**: A root ArgoCD Application that manages a directory of child Application manifests. Teams submit PRs to add their Applications.
- **ApplicationSets**: Generate Applications dynamically from generators (Git directory, cluster list, PR list). Use for multi-cluster, multi-environment, and per-PR deployments.
- **App-of-Apps vs ApplicationSets**: App-of-Apps for static topologies; ApplicationSets for dynamic ones.
- **Project isolation**: ArgoCD Projects restrict which repos each team's Applications can use and which clusters/namespaces they can deploy to.

### Multi-Cluster GitOps

Hub-and-spoke: one management cluster (ArgoCD control plane) that deploys to many spoke clusters. ArgoCD stores cluster credentials as Secrets in the management cluster. The platform team manages the management cluster; product teams interact via PRs.

---

## 15. Self-Review Checklist

Before declaring a platform capability ready for general availability, verify:

- [ ] **Self-service**: Can a developer use this capability without filing a ticket or asking the platform team for help?
- [ ] **Golden path documented**: Is there a TechDocs page that explains the capability, with examples and troubleshooting?
- [ ] **Scaffolder template**: Is there a Backstage template that wires up this capability from day zero for new services?
- [ ] **Catalog entity**: Is the capability represented in the software catalog so it's discoverable?
- [ ] **Observability**: Does the platform team have SLOs and dashboards for this capability's availability and performance?
- [ ] **Security enforced**: Are security requirements embedded in the golden path, not left to developer discretion?
- [ ] **Cost-aware**: Is the cost of using this capability visible to developers before and after provisioning?
- [ ] **Off-road path defined**: Is there a documented, supported off-road option for teams that cannot use the golden path?
- [ ] **RBAC modeled**: Is access controlled with least-privilege, and can teams manage their own access within their boundaries?
- [ ] **Tested in multi-tenant scenarios**: Has this capability been tested when multiple teams use it simultaneously?
- [ ] **Deprecation plan**: If this replaces an older pattern, is there a migration guide and deprecation timeline?
- [ ] **DORA impact measured**: Will you measure whether this capability improves lead time or deployment frequency for adopters?
- [ ] **Developer feedback collected**: Have you run the capability past 2-3 stream-aligned teams in a pilot before GA?
- [ ] **Platform NPS tracked**: Is there a mechanism to collect satisfaction feedback for this capability specifically?
- [ ] **No fabricated tool names**: Have all tool names, plugin names, CRD fields, and API endpoints been verified against official documentation?

---

## Reference URLs (Verify Before Citing)

- Backstage entity descriptor format: https://backstage.io/docs/features/software-catalog/descriptor-format
- Backstage plugin directory: https://backstage.io/plugins
- Backstage scaffolder built-in actions: https://backstage.io/docs/features/software-catalog/descriptor-format
- Team Topologies key concepts: https://teamtopologies.com/key-concepts
- DORA metrics: https://dora.dev/guides/dora-metrics-four-keys/
- CNCF Platforms White Paper: https://tag-app-delivery.cncf.io/whitepapers/platforms/
- vcluster documentation: https://www.vcluster.com/docs
- Kubernetes multi-tenancy: https://kubernetes.io/docs/concepts/security/multi-tenancy/
- Crossplane concepts: https://docs.crossplane.io/latest/concepts/
- HNC (Hierarchical Namespace Controller): https://github.com/kubernetes-sigs/hierarchical-namespaces
- ArgoCD ApplicationSets: https://argo-cd.readthedocs.io/en/stable/user-guide/application-set/
- Kubecost cost allocation: https://docs.kubecost.com/using-kubecost/navigating-the-kubecost-ui/cost-allocation
