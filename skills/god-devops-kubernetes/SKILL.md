---
name: god-devops-kubernetes
description: "God-level Kubernetes and Helm expertise. Covers cluster architecture, workload design, networking (CNI, ingress, service mesh, eBPF), storage, RBAC, pod security, autoscaling, operators, CRDs, Helm chart authoring and debugging, multi-cluster management, GitOps with ArgoCD/Flux, K8s API deep dives, kubectl power usage, and troubleshooting methodology. Never fabricates API fields — always cites kubectl explain or official API reference. Covers Kubernetes versions 1.24 through current."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Kubernetes & Helm

## Anti-Hallucination Rules (Kubernetes-Specific)

- NEVER invent Kubernetes API fields. Every field must be verifiable with `kubectl explain <resource>.<field>`.
- NEVER state a feature is available in a version without verifying the Kubernetes changelog.
- NEVER claim a Helm function exists without verifying in the Helm docs or `helm template` output.
- When in doubt about a CRD field: read the CRD spec (`kubectl get crd <name> -o yaml`) before answering.
- Always state the API version being used: `apps/v1`, `networking.k8s.io/v1`, etc.

**Verification pattern (use before asserting)**:
```bash
kubectl explain deployment.spec.strategy.rollingUpdate
kubectl api-resources | grep <resource>
kubectl api-versions | grep <group>
helm show values <chart>
helm template <release> <chart> --debug
```

---

## Phase 1: Cluster Architecture Understanding

### 1.1 Control Plane Components (know these deeply)
- **kube-apiserver**: All cluster operations go through this. Understand admission webhooks, audit logging, RBAC enforcement.
- **etcd**: The source of truth. Understand backup, restore, quorum (needs 2n+1 nodes for n failures). Never store non-Kubernetes data here.
- **kube-scheduler**: Assigns pods to nodes. Understand: node affinity, taints/tolerations, topology spread, priority classes.
- **kube-controller-manager**: Runs reconciliation loops (ReplicaSet, Deployment, StatefulSet controllers, etc.).
- **cloud-controller-manager**: Handles cloud-specific controllers (load balancers, volumes, routes).

### 1.2 Data Plane Components
- **kubelet**: Runs on every node. Manages pod lifecycle. Reports node status. Runs container runtime.
- **kube-proxy**: Manages iptables/ipvs rules for Service networking. (May be replaced by eBPF CNIs like Cilium)
- **Container Runtime**: containerd (standard), CRI-O. Docker is deprecated as a runtime.
- **CNI Plugin**: Handles pod networking. Choose based on need:

| CNI | Use Case |
|-----|---------|
| Calico | Network policy heavy, BGP routing, large clusters |
| Cilium | eBPF-based, high performance, L7 policy, Hubble observability |
| Flannel | Simple overlay, small clusters, minimal features |
| Weave | Multi-host networking, encryption built-in |
| AWS VPC CNI | EKS native, pods get VPC IPs |

---

## Phase 2: Workload Design

### 2.1 Resource Specification (Always Set These)

```yaml
resources:
  requests:           # Used for scheduling decisions — ALWAYS set
    cpu: "100m"       # 100 millicores = 0.1 CPU
    memory: "128Mi"
  limits:             # Hard cap — set memory limit, be careful with CPU limit
    cpu: "500m"       # CPU throttling (not kill) — consider not setting in latency-sensitive apps
    memory: "256Mi"   # OOMKill if exceeded — must be set
```

**Memory limit = memory request** for most apps to prevent noisy neighbor eviction.
**CPU limit**: controversial — CPU limits cause throttling even when node has spare capacity. Profile before setting.

### 2.2 Pod Disruption Budget (Always for Production)

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-service-pdb
spec:
  minAvailable: 2        # OR maxUnavailable: 1 — never both
  selector:
    matchLabels:
      app: my-service
```

Without PDBs, node drains can take down all replicas simultaneously.

### 2.3 Topology Spread Constraints (Multi-AZ Resilience)

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: my-service
  - maxSkew: 1
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: my-service
```

### 2.4 Probes (All Three — All Different)

```yaml
livenessProbe:          # If this fails: restart the container
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 10
  failureThreshold: 3

readinessProbe:         # If this fails: remove from Service endpoints (stop traffic)
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  failureThreshold: 3

startupProbe:           # Gives slow-starting apps time before liveness kicks in
  httpGet:
    path: /healthz
    port: 8080
  failureThreshold: 30
  periodSeconds: 10
```

---

## Phase 3: Networking Deep Dive

### 3.1 Service Types — Use the Right One
- **ClusterIP**: Internal only. Default. Use for service-to-service communication.
- **NodePort**: Exposes on node IP:port. Use only for debugging or bare metal without LB.
- **LoadBalancer**: Creates cloud LB. Use for external traffic entry points.
- **ExternalName**: CNAME alias to external service. Use for migrating to/from cluster.

### 3.2 Ingress vs Gateway API
- **Ingress**: Stable, widely supported, limited features. Good for simple HTTP/HTTPS routing.
- **Gateway API**: Future standard. More expressive. Use for complex routing, multi-tenant ingress, traffic splitting.

```yaml
# Gateway API — HTTPRoute (preferred for new deployments)
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: my-service-route
spec:
  parentRefs:
    - name: prod-gateway
  hostnames:
    - "api.example.com"
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /v1
      backendRefs:
        - name: my-service
          port: 8080
          weight: 90
        - name: my-service-canary
          port: 8080
          weight: 10    # 10% canary traffic
```

### 3.3 Network Policies (Always Implement — Deny by Default)

```yaml
# Default deny all ingress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-ingress
  namespace: production
spec:
  podSelector: {}
  policyTypes:
    - Ingress

# Allow only specific traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-api-ingress
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: my-service
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api-gateway
      ports:
        - port: 8080
```

---

## Phase 4: RBAC & Security

### 4.1 RBAC Principle of Least Privilege

```yaml
# ServiceAccount — one per service, never default
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service
  namespace: production
  annotations:
    # For IRSA (EKS) or Workload Identity (GKE)
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/my-service-role

# Role — namespace-scoped (prefer over ClusterRole unless needed)
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: my-service-role
  namespace: production
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]    # Read-only, specific resources
    resourceNames: ["my-config"]  # Specific resource names when possible
```

### 4.2 Pod Security Standards

Apply at namespace level:
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted    # Strictest level
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
```

Restricted profile requires:
- Non-root user
- Non-root group
- Read-only root filesystem (or explicit volume mounts)
- No privilege escalation (`allowPrivilegeEscalation: false`)
- No privileged containers
- Seccomp profile set (RuntimeDefault or custom)
- Drop all capabilities, add only what's needed

---

## Phase 5: Helm Mastery

### 5.1 Chart Structure
```
my-chart/
├── Chart.yaml          # Name, version, dependencies
├── values.yaml         # Default values
├── values-prod.yaml    # Production overrides
├── templates/
│   ├── _helpers.tpl    # Named templates (DRY)
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   └── NOTES.txt       # Post-install instructions
└── tests/
    └── test-connection.yaml
```

### 5.2 Helm Best Practices

```yaml
# _helpers.tpl — always use named templates for repeated values
{{- define "myapp.labels" -}}
app.kubernetes.io/name: {{ include "myapp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
```

**Testing charts**:
```bash
helm lint my-chart/
helm template my-release my-chart/ --values values-prod.yaml | kubeval
helm template my-release my-chart/ | kubectl apply --dry-run=client -f -
helm test my-release --namespace production
```

**Upgrade safely**:
```bash
helm upgrade my-release my-chart/ \
  --values values-prod.yaml \
  --atomic \              # Rollback automatically on failure
  --timeout 5m \
  --cleanup-on-fail \
  --history-max 10
```

---

## Phase 6: Troubleshooting Methodology

### 6.1 Pod Troubleshooting Flow

```
Pod not running?
├── Pending → Scheduling issue
│   ├── kubectl describe pod <name> → Events section
│   ├── Insufficient resources? → kubectl describe nodes
│   ├── Node selector/affinity mismatch? → kubectl get nodes --show-labels
│   └── PVC not bound? → kubectl get pvc
├── CrashLoopBackOff → Application issue
│   ├── kubectl logs <pod> --previous
│   ├── kubectl logs <pod> -c <init-container>
│   └── Check liveness probe timing (startupProbe needed?)
├── ImagePullBackOff → Registry issue
│   ├── Image name/tag correct?
│   ├── ImagePullSecret configured?
│   └── Registry reachable from node?
└── OOMKilled → Memory limit exceeded
    ├── kubectl top pod <name>
    ├── Check memory limit — too low?
    └── Profile application memory usage
```

### 6.2 Network Troubleshooting

```bash
# Test pod-to-pod connectivity
kubectl run netshoot --image=nicolaka/netshoot --rm -it -- bash
curl http://my-service.namespace.svc.cluster.local:8080/health
nslookup my-service.namespace.svc.cluster.local

# Check endpoints (if Service has no endpoints, check label selector match)
kubectl get endpoints my-service

# Check network policies blocking traffic
kubectl get networkpolicies -n namespace
```

### 6.3 Self-Review Checklist (Kubernetes)

- [ ] All deployments have resource requests and limits
- [ ] All production deployments have PodDisruptionBudgets
- [ ] All production deployments span multiple AZs (topologySpreadConstraints)
- [ ] All services have readiness, liveness, and startup probes
- [ ] NetworkPolicy default-deny is applied to all production namespaces
- [ ] No pods run as root
- [ ] All ServiceAccounts are named and minimal-permission
- [ ] Secrets are not in Git — pulled from secrets manager
- [ ] HPA configured for all stateless services
- [ ] All Helm values files are reviewed for production correctness before deploy
