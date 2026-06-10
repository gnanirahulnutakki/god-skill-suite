---
name: god-argocd-gitops
description: "God-level ArgoCD and GitOps mastery. Covers ArgoCD architecture (API server, repo server, application controller, Redis cache), Application and ApplicationSet CRDs, sync strategies (automated vs manual, self-heal, prune), sync waves and hooks, multi-cluster management, RBAC and SSO (OIDC/SAML/Dex), App of Apps pattern, ApplicationSet generators (Git, list, cluster, matrix, merge), health assessments, custom health checks, resource hooks, diff customization, notification engine, image updater, and production operational patterns. Never fabricate ArgoCD CRD fields — verify against argo-cd.readthedocs.io. Covers ArgoCD 2.x."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level ArgoCD & GitOps

## Anti-Hallucination Rules (ArgoCD-Specific)

- NEVER invent ArgoCD CRD fields. Every field must exist in the ArgoCD Application/ApplicationSet/AppProject CRD spec.
- NEVER confuse Helm hooks with ArgoCD sync hooks — they are different systems. ArgoCD uses `argocd.argoproj.io/hook` annotation, not `helm.sh/hook`.
- NEVER claim ArgoCD runs `helm install` — ArgoCD runs `helm template` and applies the rendered manifests. Helm lifecycle hooks are NOT executed by ArgoCD.
- NEVER fabricate sync wave numbers — they can be any integer (negative, zero, positive). Lower numbers sync first.
- ALWAYS specify which ArgoCD version introduced a feature (e.g., ApplicationSets GA in 2.6+, notifications merged in 2.6+).

**Verification pattern:**
```bash
argocd app get <app-name> -o yaml
kubectl get applications.argoproj.io -n argocd -o yaml
kubectl explain applications.argoproj.io.spec
argocd version
```

---

## Phase 1: GitOps Principles

### 1.1 The Four GitOps Principles (OpenGitOps)

1. **Declarative**: The entire system is described declaratively in Git (YAML manifests, Helm charts, Kustomize overlays).
2. **Versioned and Immutable**: Git is the single source of truth. Every change is a commit. Every state is recoverable.
3. **Pulled Automatically**: Agents (ArgoCD, Flux) pull desired state from Git and apply it — NOT pushed via `kubectl apply` from CI.
4. **Continuously Reconciled**: Agents detect drift between desired state (Git) and actual state (cluster) and reconcile automatically.

### 1.2 Push vs Pull Deployment

```
Push-based (traditional CI/CD):
  CI pipeline → kubectl apply → Cluster
  Problems: CI credentials have cluster access, no drift detection, 
            no self-healing, state is wherever CI ran last

Pull-based (GitOps):
  Developer → Git commit → ArgoCD watches repo → ArgoCD applies to cluster
  Benefits: Git is audit log, RBAC via Git, drift detection, self-healing,
            credentials stay in cluster (not CI), declarative rollback = git revert
```

---

## Phase 2: ArgoCD Architecture

```
┌──────────────────────────────────────────────┐
│                ArgoCD Server                 │
├──────────────────────────────────────────────┤
│  API Server          │ UI + REST/gRPC API    │
│  Repo Server         │ Clones repos, renders │
│                      │ manifests (helm/kust) │
│  Application         │ Reconciliation loop,  │
│  Controller          │ sync, health checks   │
│  Redis               │ Cache for manifests   │
│  Dex (optional)      │ OIDC/SAML SSO         │
│  Notifications       │ Slack/email/webhook   │
│  Controller          │ alerts                │
└──────────────────────────────────────────────┘
```

**Repo Server**: Clones Git repos, runs `helm template` or `kustomize build`, returns rendered manifests. Stateless, horizontally scalable. Caches rendered manifests in Redis.

**Application Controller**: Watches Application CRDs, compares desired state (from repo server) with live state (from K8s API), performs sync operations. The brain of ArgoCD.

---

## Phase 3: Application CRD

### 3.1 Helm Source

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd              # Applications live in argocd namespace
  finalizers:
    - resources-finalizer.argocd.argoproj.io  # Delete K8s resources on app deletion
spec:
  project: default               # AppProject for RBAC boundaries

  source:
    repoURL: https://github.com/myorg/k8s-manifests.git
    targetRevision: main          # Branch, tag, or commit SHA
    path: charts/my-app           # Path within repo
    helm:
      releaseName: my-app
      valueFiles:
        - values.yaml
        - values-production.yaml
      parameters:                 # Override specific values
        - name: image.tag
          value: "v2.4.1"
      values: |                   # Inline values (merged last)
        replicaCount: 3

  destination:
    server: https://kubernetes.default.svc   # In-cluster
    namespace: production

  syncPolicy:
    automated:
      prune: true               # Delete resources removed from Git
      selfHeal: true            # Revert manual changes (drift correction)
      allowEmpty: false         # Prevent sync if no resources rendered
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true          # Prune after other resources synced
      - ApplyOutOfSyncOnly=true # Only apply changed resources
      - ServerSideApply=true    # Use server-side apply (K8s 1.22+)
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

  ignoreDifferences:            # Ignore known drift (e.g., autoscaler changes replicas)
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
    - group: ""
      kind: Service
      jqPathExpressions:
        - .spec.clusterIP
```

### 3.2 Kustomize Source

```yaml
spec:
  source:
    repoURL: https://github.com/myorg/k8s-manifests.git
    targetRevision: main
    path: overlays/production     # Path to kustomization.yaml
    kustomize:
      namePrefix: prod-
      nameSuffix: ""
      images:
        - my-app=ghcr.io/myorg/my-app:v2.4.1
      commonLabels:
        environment: production
      commonAnnotations:
        owner: platform-team
```

### 3.3 Multi-Source Application (ArgoCD 2.6+)

```yaml
spec:
  sources:
    - repoURL: https://charts.bitnami.com/bitnami
      chart: postgresql
      targetRevision: 13.2.24
      helm:
        releaseName: my-db
        valueFiles:
          - $values/postgresql/values-production.yaml
    - repoURL: https://github.com/myorg/k8s-values.git
      targetRevision: main
      ref: values                 # Reference this source as $values
```

---

## Phase 4: Sync Waves and Hooks

### 4.1 Sync Waves

Resources are synced in wave order (lowest first). Same-wave resources sync in parallel.

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-1"   # Sync before wave 0
---
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "0"    # Default wave
---
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "1"    # Sync after wave 0
```

**Typical wave ordering:**
```
Wave -3: Namespaces, CRDs
Wave -2: RBAC (ServiceAccounts, Roles, RoleBindings)
Wave -1: ConfigMaps, Secrets, PVCs
Wave  0: Deployments, StatefulSets, Services (default)
Wave  1: Ingress, NetworkPolicies
Wave  2: Jobs, CronJobs
Wave  3: Monitoring (ServiceMonitors, PrometheusRules)
```

### 4.2 Resource Hooks

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync          # Run before sync
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
    argocd.argoproj.io/sync-wave: "-1"
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: my-app:latest
          command: ["python", "manage.py", "migrate"]
```

**Hook phases:**
```
PreSync   → Before main sync (migrations, schema changes)
Sync      → During sync (same as normal resources)
PostSync  → After all resources healthy (smoke tests, notifications)
SyncFail  → If sync fails (cleanup, alerting)
Skip      → Never synced (documentation-only resources)
```

**Delete policies:**
```
HookSucceeded       → Delete after success
HookFailed          → Delete after failure
BeforeHookCreation  → Delete previous run before new one
```

---

## Phase 5: ApplicationSet

### 5.1 Git Generator (Directory)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: cluster-apps
  namespace: argocd
spec:
  generators:
    - git:
        repoURL: https://github.com/myorg/k8s-manifests.git
        revision: main
        directories:
          - path: apps/*             # One Application per subdirectory
          - path: apps/experimental  # Exclude this directory
            exclude: true
  template:
    metadata:
      name: '{{path.basename}}'
    spec:
      project: default
      source:
        repoURL: https://github.com/myorg/k8s-manifests.git
        targetRevision: main
        path: '{{path}}'
      destination:
        server: https://kubernetes.default.svc
        namespace: '{{path.basename}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
```

### 5.2 Cluster Generator

```yaml
spec:
  generators:
    - clusters:
        selector:
          matchLabels:
            environment: production
  template:
    metadata:
      name: '{{name}}-my-app'
    spec:
      source:
        repoURL: https://github.com/myorg/k8s-manifests.git
        path: overlays/production
      destination:
        server: '{{server}}'
        namespace: my-app
```

### 5.3 Matrix Generator (Combinations)

```yaml
spec:
  generators:
    - matrix:
        generators:
          - git:
              repoURL: https://github.com/myorg/k8s-manifests.git
              revision: main
              directories:
                - path: apps/*
          - clusters:
              selector:
                matchLabels:
                  environment: production
  template:
    metadata:
      name: '{{path.basename}}-{{name}}'
    spec:
      source:
        path: '{{path}}'
      destination:
        server: '{{server}}'
        namespace: '{{path.basename}}'
```

---

## Phase 6: RBAC and SSO

### 6.1 AppProject RBAC

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: team-backend
  namespace: argocd
spec:
  description: "Backend team project"
  sourceRepos:
    - "https://github.com/myorg/backend-*"     # Repo whitelist
    - "https://charts.bitnami.com/bitnami"
  destinations:
    - namespace: "backend-*"                     # Namespace whitelist
      server: "https://kubernetes.default.svc"
    - namespace: "backend-*"
      server: "https://prod-cluster.example.com"
  clusterResourceWhitelist:
    - group: ""
      kind: Namespace
  namespaceResourceBlacklist:
    - group: ""
      kind: ResourceQuota                        # Prevent teams from modifying quotas
  roles:
    - name: backend-developer
      description: "Backend team dev access"
      policies:
        - p, proj:team-backend:backend-developer, applications, get, team-backend/*, allow
        - p, proj:team-backend:backend-developer, applications, sync, team-backend/*, allow
        - p, proj:team-backend:backend-developer, applications, override, team-backend/*, deny
        - p, proj:team-backend:backend-developer, applications, delete, team-backend/*, deny
      groups:
        - backend-team          # OIDC group mapping
```

### 6.2 OIDC SSO Configuration

```yaml
# argocd-cm ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-cm
  namespace: argocd
data:
  url: https://argocd.example.com
  oidc.config: |
    name: Keycloak
    issuer: https://keycloak.example.com/realms/platform
    clientID: argocd
    clientSecret: $oidc.keycloak.clientSecret    # From argocd-secret
    requestedScopes:
      - openid
      - profile
      - email
      - groups
```

---

## Phase 7: Notifications

```yaml
# argocd-notifications-cm ConfigMap
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-notifications-cm
  namespace: argocd
data:
  service.slack: |
    token: $slack-token
  trigger.on-sync-succeeded: |
    - when: app.status.operationState.phase in ['Succeeded']
      send: [app-sync-succeeded]
  trigger.on-sync-failed: |
    - when: app.status.operationState.phase in ['Error', 'Failed']
      send: [app-sync-failed]
  template.app-sync-succeeded: |
    slack:
      attachments: |
        [{
          "color": "#18be52",
          "title": "{{.app.metadata.name}} synced successfully",
          "fields": [
            {"title": "Revision", "value": "{{.app.status.sync.revision}}", "short": true},
            {"title": "Namespace", "value": "{{.app.spec.destination.namespace}}", "short": true}
          ]
        }]
  template.app-sync-failed: |
    slack:
      attachments: |
        [{
          "color": "#E96D76",
          "title": "{{.app.metadata.name}} sync FAILED",
          "fields": [
            {"title": "Error", "value": "{{.app.status.operationState.message}}", "short": false}
          ]
        }]
```

```yaml
# Subscribe Application to notifications
metadata:
  annotations:
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: platform-deploys
    notifications.argoproj.io/subscribe.on-sync-failed.slack: platform-alerts
```

---

## Phase 8: Health Assessments

### 8.1 Custom Health Checks

```yaml
# argocd-cm ConfigMap — custom health check for a CRD
data:
  resource.customizations.health.certmanager.io_Certificate: |
    hs = {}
    if obj.status ~= nil then
      if obj.status.conditions ~= nil then
        for i, condition in ipairs(obj.status.conditions) do
          if condition.type == "Ready" and condition.status == "True" then
            hs.status = "Healthy"
            hs.message = condition.message
            return hs
          end
        end
      end
    end
    hs.status = "Progressing"
    hs.message = "Waiting for certificate to be issued"
    return hs
```

### 8.2 Resource Status Types

```
Healthy     → Resource is operating correctly
Progressing → Resource is still being created/updated
Degraded    → Resource has errors but may recover
Suspended   → Resource is paused (e.g., suspended CronJob)
Missing     → Resource expected but not found in cluster
Unknown     → Health cannot be determined
```

---

## Cross-Domain Connections

**ArgoCD ↔ Helm:** ArgoCD renders Helm via `helm template` (not `helm install`). This means: Helm hooks are NOT executed, `helm test` does not run, Helm release secrets are NOT created. Use ArgoCD sync waves/hooks instead of Helm hooks.

**ArgoCD ↔ Kustomize:** ArgoCD natively supports Kustomize sources. The `kustomize build` command is executed by the repo server. Patches, overlays, and generators work as expected.

**ArgoCD ↔ RBAC/SSO:** AppProjects provide tenant isolation. Combined with OIDC group mapping (via Keycloak, Okta, AzureAD), you get per-team access control with Git as the permission boundary.

**ArgoCD ↔ Observability:** ArgoCD exports Prometheus metrics (`argocd_app_info`, `argocd_app_sync_total`, `argocd_app_health_status`). Build Grafana dashboards to monitor sync status, drift frequency, and deployment velocity across all applications.

---

## Self-Review Checklist

- [ ] Every Application has a `finalizer` to clean up K8s resources on deletion
- [ ] `syncPolicy.automated.prune: true` is set (or explicitly documented why not)
- [ ] `selfHeal: true` is enabled for production applications
- [ ] `ignoreDifferences` configured for known drift (HPA replicas, Service clusterIP)
- [ ] Sync waves order resources correctly (CRDs → RBAC → Config → Apps → Ingress)
- [ ] PreSync hooks run database migrations before deployment
- [ ] AppProject restricts source repos and destination namespaces per team
- [ ] SSO is configured with group-based RBAC (no shared admin passwords)
- [ ] Notifications configured for sync failures (Slack/PagerDuty)
- [ ] `ServerSideApply=true` enabled for large manifests and CRD management
- [ ] ApplicationSets used for multi-cluster/multi-tenant deployments (not manual Application copies)
- [ ] Image tags are pinned (not `latest`) — use ArgoCD Image Updater for automated tag updates
- [ ] `argocd app diff` reviewed before manual syncs
