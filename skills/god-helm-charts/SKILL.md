---
name: god-helm-charts
description: "God-level Helm chart mastery. Deep dive into chart authoring, template functions (sprig), named templates (_helpers.tpl), hooks and hook weights, chart testing (ct lint, ct install), OCI registry publishing, library charts, subcharts and dependency management, Helmfile for multi-chart orchestration, post-renderers, values.schema.json validation, production patterns (rolling updates, PDB, HPA templating), and debugging with helm template --debug. Never fabricate Helm template functions — verify against Helm docs and Sprig library. Covers Helm v3.x."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Helm Chart Mastery

## Anti-Hallucination Rules (Helm-Specific)

- NEVER invent Helm template functions. Every function must be verifiable in Helm docs or Sprig library docs.
- NEVER fabricate `.Values` paths — verify they exist in the chart's `values.yaml`.
- NEVER claim a Helm feature exists in a version without checking the Helm changelog (e.g., OCI support GA in Helm 3.8+).
- NEVER invent hook annotations — the valid set is: `pre-install`, `post-install`, `pre-delete`, `post-delete`, `pre-upgrade`, `post-upgrade`, `pre-rollback`, `post-rollback`, `test`.
- ALWAYS specify the Helm version when discussing features (v3.x vs v2.x differ fundamentally — Tiller is gone).
- ALWAYS use `helm template --debug` output to verify template rendering before asserting correctness.

**Verification pattern:**
```bash
helm template my-release ./my-chart --debug --values values-prod.yaml
helm lint ./my-chart --strict
helm show values <chart>
helm get manifest <release> -n <namespace>
```

---

## Phase 1: Chart Structure and Anatomy

### 1.1 Standard Chart Layout

```
my-chart/
├── Chart.yaml              # Chart metadata (required)
├── Chart.lock              # Dependency lock file (auto-generated)
├── values.yaml             # Default values
├── values.schema.json      # JSON Schema for values validation (optional but recommended)
├── .helmignore             # Files to exclude from packaging
├── crds/                   # Custom Resource Definitions (applied before templates)
│   └── my-crd.yaml
├── templates/
│   ├── NOTES.txt           # Post-install usage instructions
│   ├── _helpers.tpl        # Named template definitions (DRY)
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── serviceaccount.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   └── networkpolicy.yaml
├── charts/                 # Subcharts (dependencies)
└── tests/
    └── test-connection.yaml
```

### 1.2 Chart.yaml — Required Fields

```yaml
apiVersion: v2            # v2 = Helm 3 (v1 = Helm 2, deprecated)
name: my-chart
version: 1.2.3            # Chart version (SemVer)
appVersion: "2.4.1"       # Application version (informational)
description: "A Helm chart for My Application"
type: application         # application (default) or library
keywords:
  - my-app
  - backend
maintainers:
  - name: "Team Name"
    email: "team@example.com"
dependencies:
  - name: postgresql
    version: "~13.0"       # SemVer range
    repository: "https://charts.bitnami.com/bitnami"
    condition: postgresql.enabled    # Conditionally include
  - name: redis
    version: "^18.0"
    repository: "oci://registry-1.docker.io/bitnamicharts"  # OCI registry
    alias: cache-redis     # Rename in templates
```

**Dependency management:**
```bash
helm dependency update ./my-chart     # Download deps into charts/
helm dependency build ./my-chart      # Build from Chart.lock
helm dependency list ./my-chart       # Show deps and status
```

---

## Phase 2: Template Language Mastery

### 2.1 Built-in Objects

```yaml
# The primary objects available in templates:
{{ .Release.Name }}        # Release name (helm install <NAME>)
{{ .Release.Namespace }}   # Target namespace
{{ .Release.IsUpgrade }}   # true if upgrade, false if install
{{ .Release.IsInstall }}   # true if install
{{ .Release.Revision }}    # Revision number (starts at 1)
{{ .Release.Service }}     # Always "Helm"

{{ .Chart.Name }}          # From Chart.yaml
{{ .Chart.Version }}       # Chart version
{{ .Chart.AppVersion }}    # App version

{{ .Values.key }}          # From values.yaml or --set overrides

{{ .Template.Name }}       # Current template filename
{{ .Template.BasePath }}   # Template directory path

{{ .Capabilities.KubeVersion.Version }}  # K8s server version
{{ .Capabilities.APIVersions.Has "networking.k8s.io/v1" }}  # API check
```

### 2.2 Essential Sprig Functions

```yaml
# String functions
{{ .Values.name | lower }}
{{ .Values.name | upper }}
{{ .Values.name | title }}
{{ .Values.name | quote }}       # Wrap in double quotes
{{ .Values.name | squote }}      # Wrap in single quotes
{{ .Values.name | trunc 63 }}    # Truncate to 63 chars (K8s label limit)
{{ .Values.name | trimSuffix "-" }}
{{ printf "%s-%s" .Release.Name .Chart.Name }}
{{ regexMatch "^[a-z]+$" .Values.name }}

# Default values
{{ .Values.replicas | default 3 }}
{{ .Values.image.tag | default .Chart.AppVersion }}

# Type conversion
{{ .Values.port | int }}
{{ .Values.enabled | toString }}
{{ atoi "8080" }}

# Lists and dicts
{{ list "a" "b" "c" | join "," }}         # "a,b,c"
{{ .Values.tags | toJson }}                # Convert to JSON
{{ .Values.config | toYaml | nindent 4 }}  # Convert to YAML, indent 4

# Crypto
{{ randAlphaNum 32 }}               # Random 32-char string
{{ sha256sum .Values.config }}      # SHA-256 hash
{{ genPrivateKey "rsa" }}           # Generate RSA key
```

### 2.3 Flow Control

```yaml
# if/else
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
# ...
{{- end }}

# if/else if
{{- if eq .Values.service.type "LoadBalancer" }}
  type: LoadBalancer
{{- else if eq .Values.service.type "NodePort" }}
  type: NodePort
{{- else }}
  type: ClusterIP
{{- end }}

# with — changes scope (. becomes the value)
{{- with .Values.nodeSelector }}
nodeSelector:
  {{- toYaml . | nindent 8 }}
{{- end }}

# range — iterate over lists/maps
{{- range .Values.env }}
- name: {{ .name }}
  value: {{ .value | quote }}
{{- end }}

# range with index
{{- range $index, $val := .Values.ports }}
- containerPort: {{ $val.port }}
  name: {{ $val.name | default (printf "port-%d" $index) }}
{{- end }}

# range over map
{{- range $key, $val := .Values.annotations }}
{{ $key }}: {{ $val | quote }}
{{- end }}
```

### 2.4 Whitespace Control

```yaml
# {{- trims leading whitespace/newlines
# -}} trims trailing whitespace/newlines
# CRITICAL: misuse causes broken YAML

# Wrong — produces blank lines:
{{ if .Values.enabled }}
enabled: true
{{ end }}

# Right — clean output:
{{- if .Values.enabled }}
enabled: true
{{- end }}
```

---

## Phase 3: Named Templates (_helpers.tpl)

### 3.1 Standard Label Set

```yaml
{{/*
Common labels — applied to every resource.
*/}}
{{- define "myapp.labels" -}}
helm.sh/chart: {{ include "myapp.chart" . }}
{{ include "myapp.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels — used in matchLabels (must NOT change between upgrades).
*/}}
{{- define "myapp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "myapp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Chart name and version (for helm.sh/chart label).
*/}}
{{- define "myapp.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Expand the name of the chart. Truncate to 63 chars (K8s DNS name limit).
*/}}
{{- define "myapp.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name. Truncate to 63 chars.
*/}}
{{- define "myapp.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
ServiceAccount name.
*/}}
{{- define "myapp.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "myapp.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
```

### 3.2 Reusable Snippets

```yaml
{{/*
Container image reference — handles registry, repository, tag, digest.
*/}}
{{- define "myapp.image" -}}
{{- $registry := .Values.image.registry | default "" -}}
{{- $repository := .Values.image.repository -}}
{{- $tag := .Values.image.tag | default .Chart.AppVersion -}}
{{- if .Values.image.digest -}}
  {{- if $registry -}}
    {{- printf "%s/%s@%s" $registry $repository .Values.image.digest -}}
  {{- else -}}
    {{- printf "%s@%s" $repository .Values.image.digest -}}
  {{- end -}}
{{- else -}}
  {{- if $registry -}}
    {{- printf "%s/%s:%s" $registry $repository $tag -}}
  {{- else -}}
    {{- printf "%s:%s" $repository $tag -}}
  {{- end -}}
{{- end -}}
{{- end }}

{{/*
Checksum annotation for config — forces pod restart on config change.
*/}}
{{- define "myapp.configChecksum" -}}
checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
{{- end }}
```

---

## Phase 4: Hooks

### 4.1 Hook Types and Weights

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "myapp.fullname" . }}-db-migrate
  annotations:
    "helm.sh/hook": pre-upgrade,pre-install
    "helm.sh/hook-weight": "-5"        # Lower weight runs first
    "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
    # Delete policies:
    #   before-hook-creation: delete previous hook resource before new one created
    #   hook-succeeded: delete after hook succeeds
    #   hook-failed: delete after hook fails
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: {{ include "myapp.image" . }}
          command: ["python", "manage.py", "migrate", "--noinput"]
  backoffLimit: 3
```

### 4.2 Hook Ordering with Weights

```
Weight -10: Create database schema
Weight -5:  Run migrations
Weight 0:   Seed data (default weight)
Weight 5:   Run smoke tests
Weight 10:  Send notification
```

---

## Phase 5: Chart Testing

### 5.1 Helm Test Resources

```yaml
# templates/tests/test-connection.yaml
apiVersion: v1
kind: Pod
metadata:
  name: {{ include "myapp.fullname" . }}-test-connection
  labels:
    {{- include "myapp.labels" . | nindent 4 }}
  annotations:
    "helm.sh/hook": test
spec:
  restartPolicy: Never
  containers:
    - name: wget
      image: busybox:1.36
      command: ['wget']
      args: ['{{ include "myapp.fullname" . }}:{{ .Values.service.port }}/health']
```

```bash
helm test my-release -n production --timeout 5m
```

### 5.2 Chart Testing Tool (ct)

```bash
# Install chart-testing
brew install chart-testing   # macOS
# or: pip install chart-testing

# Lint all changed charts (CI-friendly)
ct lint --config ct.yaml --charts ./charts/

# Install and test in a Kind cluster
ct install --config ct.yaml --charts ./charts/ --upgrade

# ct.yaml configuration
cat <<'EOF' > ct.yaml
remote: origin
target-branch: main
chart-dirs:
  - charts
chart-repos:
  - bitnami=https://charts.bitnami.com/bitnami
helm-extra-args: --timeout 600s
validate-maintainers: false
EOF
```

### 5.3 values.schema.json (Values Validation)

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["image", "service"],
  "properties": {
    "replicaCount": {
      "type": "integer",
      "minimum": 1,
      "default": 1
    },
    "image": {
      "type": "object",
      "required": ["repository"],
      "properties": {
        "repository": { "type": "string" },
        "tag": { "type": "string" },
        "pullPolicy": {
          "type": "string",
          "enum": ["Always", "IfNotPresent", "Never"]
        }
      }
    },
    "service": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": ["ClusterIP", "NodePort", "LoadBalancer"]
        },
        "port": {
          "type": "integer",
          "minimum": 1,
          "maximum": 65535
        }
      }
    }
  }
}
```

---

## Phase 6: OCI Registry Support

```bash
# Helm 3.8+ — OCI support is GA

# Login to registry
helm registry login ghcr.io -u USERNAME -p TOKEN
helm registry login registry-1.docker.io -u USERNAME -p TOKEN

# Package chart
helm package ./my-chart

# Push to OCI registry
helm push my-chart-1.2.3.tgz oci://ghcr.io/myorg/charts

# Pull from OCI registry
helm pull oci://ghcr.io/myorg/charts/my-chart --version 1.2.3

# Install directly from OCI
helm install my-release oci://ghcr.io/myorg/charts/my-chart --version 1.2.3

# Show chart info from OCI
helm show chart oci://ghcr.io/myorg/charts/my-chart --version 1.2.3
```

---

## Phase 7: Library Charts

Library charts provide reusable templates but produce no Kubernetes manifests themselves.

```yaml
# Chart.yaml for library chart
apiVersion: v2
name: common-lib
version: 1.0.0
type: library    # Key difference — no templates rendered directly
```

```yaml
# In consumer chart's Chart.yaml:
dependencies:
  - name: common-lib
    version: "1.x.x"
    repository: "oci://ghcr.io/myorg/charts"
```

```yaml
# Library chart defines reusable templates:
# common-lib/templates/_deployment.tpl
{{- define "common-lib.deployment" -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "common-lib.fullname" . }}
  labels:
    {{- include "common-lib.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "common-lib.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "common-lib.selectorLabels" . | nindent 8 }}
    spec:
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports:
            - containerPort: {{ .Values.service.port }}
{{- end }}

# Consumer chart uses it:
# my-app/templates/deployment.yaml
{{ include "common-lib.deployment" . }}
```

---

## Phase 8: Helmfile — Multi-Chart Orchestration

```yaml
# helmfile.yaml — declarative multi-release management
repositories:
  - name: bitnami
    url: https://charts.bitnami.com/bitnami
  - name: ingress-nginx
    url: https://kubernetes.github.io/ingress-nginx

environments:
  default:
    values:
      - environments/default.yaml
  production:
    values:
      - environments/production.yaml

releases:
  - name: ingress
    namespace: ingress-system
    chart: ingress-nginx/ingress-nginx
    version: 4.8.3
    values:
      - values/ingress.yaml
    wait: true
    timeout: 300

  - name: my-app
    namespace: production
    chart: ./charts/my-app
    values:
      - values/my-app.yaml
      - values/my-app-{{ .Environment.Name }}.yaml
    needs:
      - ingress-system/ingress    # Dependency ordering
    set:
      - name: image.tag
        value: {{ requiredEnv "IMAGE_TAG" }}
    hooks:
      - events: ["presync"]
        showlogs: true
        command: "kubectl"
        args: ["apply", "-f", "crds/"]
```

```bash
# Helmfile commands
helmfile -e production sync          # Install/upgrade all releases
helmfile -e production diff          # Show what would change
helmfile -e production apply         # diff + sync (interactive)
helmfile -e production destroy       # Uninstall all
helmfile -e production status        # Status of all releases
helmfile -l name=my-app sync         # Sync only specific release
```

---

## Phase 9: Post-Renderers

Post-renderers modify Helm output after template rendering but before applying to the cluster. Use for Kustomize overlays on Helm output.

```bash
# Use Kustomize as a post-renderer
helm install my-release ./my-chart --post-renderer ./kustomize-post-render.sh
```

```bash
#!/bin/bash
# kustomize-post-render.sh
cat > /tmp/helm-output.yaml
kustomize build /tmp/kustomize-overlay
```

```yaml
# /tmp/kustomize-overlay/kustomization.yaml
resources:
  - /tmp/helm-output.yaml
patches:
  - target:
      kind: Deployment
    patch: |
      - op: add
        path: /spec/template/metadata/annotations/sidecar.istio.io~1inject
        value: "true"
```

---

## Phase 10: Production Patterns

### 10.1 Safe Upgrade Strategy

```bash
helm upgrade my-release ./my-chart \
  --namespace production \
  --values values-prod.yaml \
  --atomic \                    # Auto-rollback on failure
  --timeout 10m \
  --cleanup-on-fail \           # Delete new resources on failure
  --history-max 10 \            # Limit release history
  --wait \                      # Wait for all resources to be ready
  --wait-for-jobs               # Wait for hook jobs too
```

### 10.2 Rollback

```bash
helm rollback my-release 3 -n production    # Roll back to revision 3
helm history my-release -n production       # View release history
helm get values my-release -n production    # See current values
helm get manifest my-release -n production  # See rendered manifests
```

### 10.3 Diff Before Upgrade

```bash
# helm-diff plugin — essential for safe upgrades
helm plugin install https://github.com/databus23/helm-diff

helm diff upgrade my-release ./my-chart \
  --values values-prod.yaml \
  --normalize-manifests
```

---

## Phase 11: Debugging

```bash
# Template rendering debug
helm template my-release ./my-chart --debug 2>&1 | less

# Render specific template
helm template my-release ./my-chart -s templates/deployment.yaml

# Lint with strict mode
helm lint ./my-chart --strict --values values-prod.yaml

# Get rendered notes
helm get notes my-release -n production

# Get hooks
helm get hooks my-release -n production

# Dry run against cluster (server-side validation)
helm install my-release ./my-chart --dry-run --debug -n production
# Helm 3.13+: --dry-run=server (validates against actual cluster API)
```

---

## Cross-Domain Connections

**Helm ↔ ArgoCD/GitOps:** ArgoCD renders Helm charts server-side. Understand that ArgoCD runs `helm template` — it does NOT use `helm install`. This means hooks are handled differently (ArgoCD has its own sync waves/hooks). Helmfile is not natively supported by ArgoCD — use ArgoCD ApplicationSets for multi-chart management instead.

**Helm ↔ Kustomize:** Post-renderers bridge Helm and Kustomize. ArgoCD supports Helm + Kustomize natively via the `kustomize` build option with `helmCharts` in kustomization.yaml.

**Helm ↔ OCI/Container Registries:** Helm charts stored in OCI registries use the same authentication as container images. GHCR, ECR, GCR, ACR, and Docker Hub all support OCI Helm charts.

**Helm ↔ CI/CD:** Chart Testing (ct) is designed for CI pipelines. Lint on PR, install-test in Kind/k3s clusters, push to OCI registry on merge.

---

## Self-Review Checklist

- [ ] Chart has `values.schema.json` for input validation
- [ ] All labels follow `app.kubernetes.io/*` convention
- [ ] Selector labels are immutable (never change between upgrades)
- [ ] Named templates use `trunc 63 | trimSuffix "-"` for DNS compliance
- [ ] Whitespace control (`{{-` / `-}}`) produces clean YAML output
- [ ] `helm template --debug` renders without errors
- [ ] `helm lint --strict` passes
- [ ] Hook delete policies are set (avoid orphaned hook resources)
- [ ] Subcharts use `condition:` for optional inclusion
- [ ] Production upgrades use `--atomic --wait --timeout`
- [ ] `helm diff` reviewed before every production upgrade
- [ ] Image references support both tag and digest
- [ ] ConfigMap/Secret changes trigger pod restarts via checksum annotations
- [ ] NOTES.txt provides clear post-install instructions
- [ ] Chart tests exist and pass (`helm test`)
