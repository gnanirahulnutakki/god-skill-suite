---
name: god-kustomize
description: "God-level Kustomize mastery. Covers base/overlay architecture, strategic merge patches, JSON 6902 patches, components, generators (ConfigMapGenerator, SecretGenerator), transformers (images, labels, annotations, namespaces, prefixes/suffixes), vars and replacements, Helm chart integration via helmCharts, multi-environment management, Kustomize plugins, and production patterns for managing Kubernetes manifests without templating. Never fabricate kustomization.yaml fields — verify against kubectl kustomize docs. Covers Kustomize v5.x (bundled with kubectl 1.27+)."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Kustomize

## Anti-Hallucination Rules (Kustomize-Specific)

- NEVER invent `kustomization.yaml` fields — verify against `kustomize build` output or official docs.
- NEVER confuse `patchesStrategicMerge` (deprecated) with `patches` (current) — use `patches` with `patch` or `path` field.
- NEVER claim Kustomize supports Go template syntax — Kustomize is template-free by design.
- NEVER fabricate transformer names — `images`, `labels`, `namePrefix`, `nameSuffix`, `namespace`, `commonLabels`, `commonAnnotations` are the built-in transformers.
- ALWAYS specify whether a feature requires standalone Kustomize or is available in `kubectl kustomize` (they may differ in version).

**Verification pattern:**
```bash
kustomize build overlays/production
kubectl kustomize overlays/production
kustomize build overlays/production | kubectl apply --dry-run=client -f -
kustomize version
```

---

## Phase 1: Core Concepts

### 1.1 Template-Free Philosophy

Kustomize modifies Kubernetes YAML through overlays and patches — NOT templates. Unlike Helm, there are no `{{ }}` expressions. The base manifests are valid Kubernetes YAML that can be applied directly.

```
Base (reusable, unmodified K8s YAML)
  ↓
Overlay (environment-specific modifications)
  ↓
Final rendered YAML
```

### 1.2 Directory Structure

```
k8s/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── namespace.yaml
├── overlays/
│   ├── development/
│   │   ├── kustomization.yaml
│   │   ├── replica-patch.yaml
│   │   └── dev-config.env
│   ├── staging/
│   │   ├── kustomization.yaml
│   │   └── staging-patch.yaml
│   └── production/
│       ├── kustomization.yaml
│       ├── production-patch.yaml
│       ├── hpa.yaml
│       └── pdb.yaml
└── components/
    ├── monitoring/
    │   ├── kustomization.yaml
    │   └── servicemonitor.yaml
    └── network-policy/
        ├── kustomization.yaml
        └── networkpolicy.yaml
```

---

## Phase 2: kustomization.yaml

### 2.1 Base kustomization.yaml

```yaml
# base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - namespace.yaml
  - deployment.yaml
  - service.yaml
  - configmap.yaml

commonLabels:
  app.kubernetes.io/name: my-app
  app.kubernetes.io/part-of: my-platform

commonAnnotations:
  owner: backend-team
```

### 2.2 Overlay kustomization.yaml

```yaml
# overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base                    # Reference the base
  - hpa.yaml                     # Additional resources for production
  - pdb.yaml

namespace: production             # Override namespace for all resources

namePrefix: prod-                 # Prefix all resource names
nameSuffix: ""

images:
  - name: my-app                  # Match container image name
    newName: ghcr.io/myorg/my-app
    newTag: v2.4.1
    # OR: digest: sha256:abc123...

labels:
  - pairs:
      environment: production
    includeSelectors: false        # Don't add to selectors (safe)

patches:
  - path: production-patch.yaml   # File-based patch
  - target:                       # Inline patch with target selector
      kind: Deployment
      name: my-app
    patch: |
      - op: replace
        path: /spec/replicas
        value: 5

components:
  - ../../components/monitoring
  - ../../components/network-policy

configMapGenerator:
  - name: app-config
    behavior: merge               # Merge with base ConfigMap
    literals:
      - LOG_LEVEL=warn
      - DB_HOST=prod-db.example.com

secretGenerator:
  - name: app-secrets
    envs:
      - secrets.env               # KEY=VALUE file
    type: Opaque
```

---

## Phase 3: Patches

### 3.1 Strategic Merge Patch

Merges with the existing resource — you only specify the fields you want to change.

```yaml
# overlays/production/production-patch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app                    # Must match the base resource name
spec:
  replicas: 5
  template:
    spec:
      containers:
        - name: my-app            # Must match container name
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2000m"
              memory: "1Gi"
          env:
            - name: LOG_LEVEL
              value: "warn"
```

### 3.2 JSON 6902 Patch

Precise operations: `add`, `remove`, `replace`, `move`, `copy`, `test`.

```yaml
# In kustomization.yaml:
patches:
  - target:
      group: apps
      version: v1
      kind: Deployment
      name: my-app
    patch: |
      - op: replace
        path: /spec/replicas
        value: 5
      - op: add
        path: /spec/template/spec/containers/0/env/-
        value:
          name: FEATURE_FLAG
          value: "true"
      - op: remove
        path: /spec/template/spec/containers/0/env/2
      - op: replace
        path: /metadata/annotations/deployment.kubernetes.io~1revision
        value: "42"
```

**Path escaping:** `/` in field names becomes `~1`, `~` becomes `~0`.

### 3.3 Target Selectors

```yaml
patches:
  - target:
      kind: Deployment                    # All Deployments
    patch: |
      - op: add
        path: /spec/template/metadata/annotations
        value:
          sidecar.istio.io/inject: "true"

  - target:
      kind: Service
      labelSelector: "tier=frontend"      # Only Services with label
    patch: |
      - op: replace
        path: /spec/type
        value: LoadBalancer

  - target:
      kind: Deployment
      annotationSelector: "team=backend"  # By annotation
    patch: ...

  - target:
      kind: .*                            # Regex — all kinds
      name: .*-canary                     # Regex — names ending in -canary
    patch: ...
```

---

## Phase 4: Generators

### 4.1 ConfigMapGenerator

```yaml
configMapGenerator:
  # From literals
  - name: app-config
    literals:
      - DATABASE_URL=postgres://localhost:5432/mydb
      - CACHE_TTL=300

  # From files
  - name: nginx-config
    files:
      - nginx.conf
      - config/default.conf

  # From env file
  - name: app-env
    envs:
      - app.env

  # Options
  - name: app-config
    literals:
      - KEY=VALUE
    options:
      disableNameSuffixHash: true   # Don't append hash suffix
      labels:
        app: my-app
      annotations:
        note: auto-generated
```

**Name suffix hash:** By default, Kustomize appends a content hash to ConfigMap/Secret names (e.g., `app-config-abc123`). This forces pods to restart when config changes. Use `disableNameSuffixHash: true` only when you handle restarts another way.

### 4.2 SecretGenerator

```yaml
secretGenerator:
  - name: app-secrets
    type: kubernetes.io/tls
    files:
      - tls.crt=certs/server.crt
      - tls.key=certs/server.key

  - name: docker-registry
    type: kubernetes.io/dockerconfigjson
    files:
      - .dockerconfigjson=docker-config.json
```

---

## Phase 5: Components

Components are reusable kustomization fragments that can be included in any overlay — unlike bases, they can contain patches and transformers.

```yaml
# components/monitoring/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1alpha1    # Note: v1alpha1 for components
kind: Component

resources:
  - servicemonitor.yaml

patches:
  - target:
      kind: Deployment
    patch: |
      - op: add
        path: /spec/template/metadata/annotations/prometheus.io~1scrape
        value: "true"
      - op: add
        path: /spec/template/metadata/annotations/prometheus.io~1port
        value: "8080"
```

```yaml
# components/network-policy/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1alpha1
kind: Component

resources:
  - networkpolicy.yaml

patches:
  - target:
      kind: Deployment
    patch: |
      - op: add
        path: /metadata/labels/network-policy
        value: "restricted"
```

---

## Phase 6: Replacements (Modern vars)

`vars` is deprecated. Use `replacements` instead.

```yaml
replacements:
  - source:
      kind: Service
      name: my-service
      fieldPath: metadata.name
    targets:
      - select:
          kind: Deployment
          name: my-app
        fieldPaths:
          - spec.template.spec.containers.[name=my-app].env.[name=SERVICE_NAME].value

  - source:
      kind: ConfigMap
      name: app-config
      fieldPath: data.DATABASE_URL
    targets:
      - select:
          kind: Deployment
        fieldPaths:
          - spec.template.spec.containers.0.env.[name=DB_URL].value
```

---

## Phase 7: Helm Integration

Kustomize can render Helm charts as a generator (Kustomize v4.1+).

```yaml
# kustomization.yaml
helmCharts:
  - name: ingress-nginx
    repo: https://kubernetes.github.io/ingress-nginx
    version: 4.8.3
    releaseName: ingress
    namespace: ingress-system
    valuesFile: ingress-values.yaml
    includeCRDs: true
    additionalValuesFiles:
      - ingress-overrides.yaml

helmGlobals:
  chartHome: charts/           # Where to download charts
```

```bash
# Build with Helm chart rendering
kustomize build --enable-helm overlays/production
```

---

## Phase 8: Multi-Environment Management

### 8.1 Pattern: Shared Base with Per-Environment Overlays

```yaml
# overlays/development/kustomization.yaml
resources:
  - ../../base
namespace: development
images:
  - name: my-app
    newTag: latest
patches:
  - target:
      kind: Deployment
    patch: |
      - op: replace
        path: /spec/replicas
        value: 1
configMapGenerator:
  - name: app-config
    behavior: merge
    literals:
      - LOG_LEVEL=debug
      - DB_HOST=localhost
```

```yaml
# overlays/production/kustomization.yaml
resources:
  - ../../base
  - hpa.yaml
  - pdb.yaml
namespace: production
images:
  - name: my-app
    newTag: v2.4.1
patches:
  - target:
      kind: Deployment
    patch: |
      - op: replace
        path: /spec/replicas
        value: 5
configMapGenerator:
  - name: app-config
    behavior: merge
    literals:
      - LOG_LEVEL=warn
      - DB_HOST=prod-db.internal
components:
  - ../../components/monitoring
  - ../../components/network-policy
```

---

## Cross-Domain Connections

**Kustomize ↔ ArgoCD:** ArgoCD natively renders Kustomize overlays. No special configuration needed — just point the Application source to the overlay directory.

**Kustomize ↔ Helm:** Use `helmCharts` in kustomization.yaml or Helm post-renderers with Kustomize for patching Helm output.

**Kustomize ↔ CI/CD:** `kustomize edit set image my-app=ghcr.io/org/app:${COMMIT_SHA}` in CI pipelines updates the image tag, then commit to Git for GitOps.

**Kustomize ↔ Config Management:** ConfigMapGenerator with hash suffixes provides immutable config — pods automatically restart when config changes, no manual rollout needed.

---

## Self-Review Checklist

- [ ] Base manifests are valid standalone YAML (can `kubectl apply -f base/`)
- [ ] Overlays only modify what differs per environment — no duplicated base content
- [ ] `kustomize build` output is reviewed before applying
- [ ] ConfigMap/Secret hash suffixes are enabled (default) for automatic rollouts
- [ ] Components used for cross-cutting concerns (monitoring, network policies)
- [ ] Patches use `target` selectors (not deprecated `patchesStrategicMerge`)
- [ ] `replacements` used instead of deprecated `vars`
- [ ] Image tags updated via `images` transformer (not raw patches)
- [ ] `namespace` transformer applied at overlay level (not hardcoded in base)
- [ ] Labels added with `includeSelectors: false` to avoid breaking selector immutability
- [ ] Helm charts rendered via `helmCharts` when mixing Helm + Kustomize
- [ ] All overlays tested: `kustomize build overlays/<env> | kubectl apply --dry-run=server -f -`
