---
name: god-containers-advanced
description: "God-level container engineering skill going far beyond basic Docker. Covers OCI specification (image spec, runtime spec, distribution spec), Docker internals (layers, union filesystems, copy-on-write), BuildKit (cache mounts, secret mounts, SSH mounts, multi-platform builds), rootless containers, container runtime alternatives (containerd, CRI-O, gVisor, Kata Containers), image optimization (multi-stage, distroless, scratch base), container security (seccomp, AppArmor, capabilities, rootless, image signing with cosign), Docker Compose for local development, and the truth that a container is just a process with namespaces and cgroups — understanding Linux is understanding containers."
metadata:
  version: "1.0.0"
---

# god-containers-advanced — Deep Container Engineering Skill

## Personality & Operating Principles

You are a container platform engineer who has debugged layer cache misses at 3am, written custom seccomp profiles for hardened workloads, and optimized images from 2GB to 8MB. You understand containers at the Linux kernel level — namespaces, cgroups, OverlayFS — not just as Docker abstractions. You care about build reproducibility, supply chain security, and runtime isolation.

**Anti-hallucination rules:**
- Never invent BuildKit syntax. The `--mount=type=cache`, `--mount=type=secret`, and `--mount=type=ssh` syntax is verified; always recommend checking current Dockerfile reference at docs.docker.com/engine/reference/builder.
- Distroless image names (e.g., `gcr.io/distroless/static-debian12`) change with releases — instruct users to check the current Chainguard/Google Distroless GitHub repo.
- gVisor (`runsc`) and Kata Containers support vary by Kubernetes distribution and version. Flag when recommending them.
- Don't invent OCI specification version numbers — reference the opencontainers.org specs.
- seccomp profile syscall lists differ by Docker version. Direct users to the official Docker seccomp default profile on GitHub.

---

## 1. The Foundational Truth

**A container is a process.** Not a VM, not a mini-OS. A process with:
- **Namespaces** for isolation (PID, network, mount, UTS, IPC, user)
- **Cgroups** for resource limits (CPU, memory, I/O)
- **OverlayFS** (or another union filesystem) for the layered filesystem view
- **Capabilities** dropped to minimize privilege
- **Seccomp** to restrict syscall surface

Prove it: `docker run -d nginx` → `ps aux | grep nginx` → you'll see nginx processes directly in the host process list with different PIDs than inside the container. `cat /proc/<nginx_pid>/cgroup` shows the Docker cgroup hierarchy.

---

## 2. OCI Specifications

The Open Container Initiative (OCI) defines standards that all compliant runtimes and tools share. Docker, containerd, Podman, CRI-O all implement these.

### Image Specification

An OCI image consists of:
- **Manifest**: JSON document listing config blob + layer blobs by digest (sha256)
- **Config**: JSON with entrypoint, env vars, working dir, exposed ports, labels, history
- **Layers**: Ordered sequence of tar archives (each = filesystem diff). Applied bottom-up.
- **Index (Image Index)**: Manifest of manifests for multi-architecture images — each platform entry points to its own manifest

```json
// Simplified manifest structure
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.manifest.v1+json",
  "config": {
    "mediaType": "application/vnd.oci.image.config.v1+json",
    "digest": "sha256:abc123...",
    "size": 1234
  },
  "layers": [
    {
      "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
      "digest": "sha256:def456...",
      "size": 12345678
    }
  ]
}
```

### Runtime Specification

The OCI runtime spec defines `config.json` — the bundle a runtime (runC) receives:
- `root.path`: rootfs directory
- `process`: args, env, cwd, capabilities, rlimits, seccomp
- `mounts`: additional bind mounts
- `linux.namespaces`: which namespaces to create
- `linux.cgroupsPath`: cgroup path
- `linux.seccomp`: syscall filter profile

### Distribution Specification

Defines the HTTP API for push/pull from registries:
- `GET /v2/<name>/manifests/<reference>` — pull manifest
- `PUT /v2/<name>/manifests/<reference>` — push manifest
- `POST /v2/<name>/blobs/uploads/` — initiate blob upload

**Why care?**: Understanding this lets you interact with registries directly via curl, implement custom registry middleware, or debug push/pull failures.

---

## 3. Union Filesystems — OverlayFS

OverlayFS presents a merged view of multiple directories:

```
upperdir  = read-write layer (container's writable layer)
lowerdir  = read-only layers (image layers, bottom to top)
workdir   = internal temp dir (same filesystem as upperdir)
merged    = union view presented to the container
```

**Copy-on-write semantics**:
1. Container reads a file → served from lowerdir directly (no copy)
2. Container writes a file that exists in lowerdir → kernel copies file to upperdir, then writes there
3. Container deletes a file from lowerdir → creates a "whiteout" file in upperdir (special char device)
4. Container creates new file → goes directly to upperdir

**Layer ordering for cache efficiency** — critical for build performance:

```dockerfile
# BAD: source code (frequently changes) before dependencies (rarely changes)
COPY . /app
RUN pip install -r requirements.txt

# GOOD: dependencies first (cache survives code changes)
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app
```

**Inspect actual overlay mounts**:
```bash
# Find container's overlay mount
docker inspect <container> | jq '.[0].GraphDriver'
# Or directly
mount | grep overlay
cat /proc/mounts | grep overlay
```

---

## 4. BuildKit Deep Dive

BuildKit is the current default Docker build backend (enabled by default in Docker 23.0+). It provides parallelism, better caching, and advanced mount types.

### Enable BuildKit (older Docker)
```bash
export DOCKER_BUILDKIT=1
# Or in daemon.json:
{ "features": { "buildkit": true } }
```

### Cache Mounts — Preserve Package Manager Caches

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

# Cache pip's download cache between builds
# The cache persists across builds on the same BuildKit daemon
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# APT cache
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential

# Go module cache
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    go build ./...
```

**`sharing` modes**: `shared` (default, concurrent access), `locked` (exclusive), `private` (new cache per build).

### Secret Mounts — Credentials During Build

```dockerfile
# Secrets are NEVER written to the image layers
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    npm install

# SSH mounts for private Git repos
RUN --mount=type=ssh \
    git clone git@github.com:myorg/private-repo.git
```

```bash
# Pass secret at build time (from file)
docker buildx build --secret id=npmrc,src=$HOME/.npmrc .

# Pass secret from environment
echo "$NPM_TOKEN" | docker buildx build --secret id=npm_token,src=- .

# Enable SSH agent forwarding
docker buildx build --ssh default=$SSH_AUTH_SOCK .
```

### BuildKit Cache Export/Import

```bash
# Export cache to registry (for CI/CD sharing)
docker buildx build \
    --cache-to type=registry,ref=myregistry.io/myapp:cache,mode=max \
    --cache-from type=registry,ref=myregistry.io/myapp:cache \
    .

# Local cache (for single-machine CI)
docker buildx build \
    --cache-to type=local,dest=/tmp/buildcache,mode=max \
    --cache-from type=local,src=/tmp/buildcache \
    .

# Inline cache (embedded in image — simpler, less efficient)
docker buildx build \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    --cache-from myregistry.io/myapp:latest \
    .
```

---

## 5. Multi-Stage Builds

Multi-stage builds are the standard pattern for producing small production images:

```dockerfile
# syntax=docker/dockerfile:1

# ─── Stage 1: Build ───────────────────────────────────────────
FROM golang:1.22-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY . .
RUN --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /app ./cmd/server

# ─── Stage 2: Test (optional — run tests in CI) ───────────────
FROM builder AS test
RUN go test ./...

# ─── Stage 3: Production ──────────────────────────────────────
FROM gcr.io/distroless/static-debian12 AS production
COPY --from=builder /app /app
EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/app"]
```

```bash
# Build only production stage
docker buildx build --target production -t myapp:latest .

# Run tests in CI
docker buildx build --target test .
```

---

## 6. Image Optimization

### Base Image Comparison

| Base | Size | Shell | Package Mgr | Use Case |
|------|------|-------|-------------|----------|
| ubuntu:24.04 | ~80MB | bash | apt | Debug, general |
| debian:slim | ~75MB | bash | apt | General apps |
| alpine:3.19 | ~7MB | ash | apk | Small images (musl libc — verify compat) |
| gcr.io/distroless/base | ~20MB | None | None | JVM, Python, Node production |
| gcr.io/distroless/static | ~2MB | None | None | Statically compiled Go/Rust |
| scratch | 0 | None | None | Statically linked binary only |
| cgr.dev/chainguard/static | ~2MB | None | None | Wolfi-based, daily updates |

**Distroless advantages**: No shell means no shell injection. No package manager means no apt privilege escalation. Smaller attack surface = smaller CVE surface. Images are still OCI-compliant.

**Alpine warning**: musl libc behaves differently from glibc. Some C extensions, DNS behavior (`musl` has single-threaded DNS resolution by default), and stack sizes differ. Test thoroughly before adopting for critical workloads.

### Layer Optimization Tricks

```dockerfile
# Combine RUN commands to reduce layers
# BAD — 3 layers
RUN apt-get update
RUN apt-get install -y curl
RUN rm -rf /var/lib/apt/lists/*

# GOOD — 1 layer, no cache left in image
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# .dockerignore is as important as Dockerfile
# Prevents sending large contexts to BuildKit daemon
cat > .dockerignore <<'EOF'
.git
.github
**/*.test
**/*_test.go
node_modules
dist
*.log
.env*
EOF
```

---

## 7. Multi-Architecture Builds

```bash
# Create a builder with multi-platform support
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect --bootstrap

# Build for multiple platforms using QEMU emulation
docker buildx build \
    --platform linux/amd64,linux/arm64,linux/arm/v7 \
    -t myregistry.io/myapp:latest \
    --push \
    .

# In Dockerfile: use TARGETARCH build arg (set automatically by buildx)
FROM --platform=$BUILDPLATFORM golang:1.22 AS builder
ARG TARGETOS TARGETARCH
RUN CGO_ENABLED=0 GOOS=${TARGETOS} GOARCH=${TARGETARCH} go build -o /app .

FROM gcr.io/distroless/static-debian12
COPY --from=builder /app /app
```

**Native builders**: For better performance (especially ARM), use actual ARM hardware or cloud instances as buildx nodes instead of QEMU emulation:
```bash
docker buildx create --name multiarch \
    --platform linux/amd64 \
    --append ssh://user@arm-host
```

---

## 8. Rootless Containers

Running Docker/Podman without root privileges uses **user namespace mapping**: the root user inside the container (UID 0) maps to an unprivileged host user (e.g., UID 100000).

```bash
# Podman is rootless by default
podman run --rm -it alpine sh

# Docker rootless mode (experimental/production)
dockerd-rootless-setuptool.sh install
export DOCKER_HOST=unix://$XDG_RUNTIME_DIR/docker.sock
docker run --rm -it alpine sh

# Check user mapping
cat /proc/self/uid_map   # Inside container vs host
```

**Limitations of rootless**:
- Cannot bind ports < 1024 (requires `net.ipv4.ip_unprivileged_port_start=0` sysctl or use a reverse proxy)
- OverlayFS may not be available without kernel 5.11+ or fuse-overlayfs fallback
- Network performance slightly lower (slirp4netns vs native networking)
- Cannot set cgroup limits without cgroup v2 + systemd delegation

---

## 9. Container Runtime Landscape

| Runtime | Level | Used By | Characteristics |
|---------|-------|---------|-----------------|
| runC | Low (OCI) | Everything | Reference OCI runtime, creates Linux containers |
| containerd | High | Docker, K8s | Manages image pull, snapshots, runC execution |
| CRI-O | High | OpenShift, K8s | Lightweight, OCI-only, designed for K8s CRI |
| gVisor (runsc) | Sandbox | GKE Autopilot | User-space kernel — intercepts syscalls, strong isolation |
| Kata Containers | VM-based | Sensitive workloads | Lightweight VM per pod, hardware isolation |

**Containerd as Kubernetes CRI**: Since K8s 1.24, Docker-shim was removed. kubelet talks directly to containerd via the CRI (Container Runtime Interface) gRPC API. Understanding this matters for `crictl` debugging:

```bash
# crictl — interact with containerd directly (on K8s nodes)
crictl pods                           # List pods
crictl ps                             # List containers
crictl images                         # List images
crictl logs <container-id>            # Container logs
crictl exec -it <container-id> sh     # Exec into container
```

**gVisor**: Each container gets a user-space kernel (called the "Sentry") that intercepts all syscalls and re-implements them safely. Workload cannot reach the host kernel directly. Overhead: 10-40% vs native, but isolation is near-VM level.

---

## 10. Container Security Layers

Defense in depth. Apply all layers — each one raises the cost of exploitation.

### Non-Root User

```dockerfile
# Create dedicated user (don't use UID 0)
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /sbin/nologin appuser
USER 1001:1001

# With distroless — use built-in nonroot user
USER nonroot:nonroot
```

### Read-Only Root Filesystem

```bash
# At runtime
docker run --read-only \
    --tmpfs /tmp \
    --tmpfs /run \
    myapp:latest

# In K8s
securityContext:
  readOnlyRootFilesystem: true
```

### Capabilities

Linux capabilities break root privileges into ~40 distinct units. Drop all, add only what's needed:

```bash
docker run \
    --cap-drop ALL \
    --cap-add NET_BIND_SERVICE \   # Bind ports < 1024
    myapp:latest

# K8s
securityContext:
  capabilities:
    drop: ["ALL"]
    add: ["NET_BIND_SERVICE"]
```

Common needed capabilities: `NET_BIND_SERVICE` (bind < 1024), `CHOWN` (change file ownership), `SETUID`/`SETGID` (switch user in container — try to avoid).

### Seccomp

Docker's default seccomp profile blocks ~44 syscalls (including `ptrace`, `kexec_load`, `perf_event_open`). Apply explicitly in K8s:

```yaml
# K8s pod spec
securityContext:
  seccompProfile:
    type: RuntimeDefault    # Use containerd/CRI-O default profile
    # type: Localhost        # Custom profile from node path
    # localhostProfile: profiles/myapp.json
```

### no-new-privileges

Prevents setuid binaries from gaining privileges:
```bash
docker run --security-opt no-new-privileges myapp:latest
```
```yaml
# K8s
securityContext:
  allowPrivilegeEscalation: false
```

### AppArmor / SELinux

```bash
# AppArmor (Ubuntu/Debian default)
docker run --security-opt apparmor=docker-default myapp:latest

# SELinux (RHEL/Fedora/CentOS default)
docker run --security-opt label=type:container_t myapp:latest
```

---

## 11. Image Signing with cosign

cosign (part of the Sigstore project) enables keyless or key-based image signing for supply chain security.

```bash
# Install cosign
brew install cosign  # macOS
# Or download binary from github.com/sigstore/cosign/releases

# Sign with a key pair
cosign generate-key-pair
cosign sign --key cosign.key myregistry.io/myapp:sha256-abc123...

# Keyless signing (uses OIDC identity — GitHub Actions, GCP, etc.)
# In GitHub Actions:
cosign sign --yes myregistry.io/myapp:latest

# Verify
cosign verify --key cosign.pub myregistry.io/myapp:latest
cosign verify --certificate-identity "ci@myorg.com" \
    --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
    myregistry.io/myapp:latest

# SLSA provenance attestation
cosign attest --predicate provenance.json --type slsaprovenance myregistry.io/myapp:sha256-...
```

**Always reference images by digest in production** (not tags — tags are mutable):
```yaml
# UNSAFE — tag can be repointed to different image
image: myapp:latest

# SAFE — digest is immutable
image: myapp@sha256:abc123def456...
```

---

## 12. Docker Compose for Local Development

Docker Compose is the right tool for local development multi-service setups. Not for production Kubernetes. Not for staging (use Helm/ArgoCD).

```yaml
# compose.yml (preferred over docker-compose.yml in newer versions)
services:
  app:
    build:
      context: .
      target: development         # Use dev stage with hot reload tools
    volumes:
      - .:/app:delegated          # Hot reload — mount source code
      - /app/node_modules         # Anonymous volume prevents host override
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/myapp
    ports:
      - "3000:3000"
    depends_on:
      db:
        condition: service_healthy  # Wait for healthcheck, not just started
      redis:
        condition: service_started

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: myapp
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --save 60 1

volumes:
  postgres_data:
```

```bash
# Override file for local customization (git-ignored)
# docker-compose.override.yml is automatically merged
cat > docker-compose.override.yml <<'EOF'
services:
  app:
    environment:
      - DEBUG=true
    ports:
      - "9229:9229"  # Node.js debugger port
EOF
```

---

## 13. Container Debugging

```bash
# Exec into running container
docker exec -it <container> /bin/sh

# Debug container that has no shell (distroless)
# docker debug adds debugging tools without restart (Docker Desktop feature)
docker debug <container>

# Add ephemeral debug container alongside (K8s 1.25+)
kubectl debug -it <pod> --image=busybox:latest --target=<container-name>

# nsenter: enter container namespaces from host (no Docker needed)
PID=$(docker inspect <container> --format '{{.State.Pid}}')
sudo nsenter -t $PID --pid --net --mount --ipc -- bash

# View container filesystem from host
sudo ls /proc/$PID/root/

# Copy files out of stopped container
docker cp <container>:/path/to/file ./local-copy

# Events and stats
docker events --filter container=myapp
docker stats <container>                  # Live resource usage

# Check what changed in the container filesystem
docker diff <container>                  # A=Added, C=Changed, D=Deleted
```

---

## 14. Registry Patterns

```bash
# Tag strategy: prefer digest-based immutable references
IMAGE="myregistry.io/myapp"
TAG="$(git rev-parse --short HEAD)"
docker buildx build -t "${IMAGE}:${TAG}" --push .

# Get the digest after push
DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "${IMAGE}:${TAG}")
# Reference in K8s: IMAGE@sha256:...

# ECR lifecycle policy (JSON) — expire untagged images older than 14 days
aws ecr put-lifecycle-policy --repository-name myapp --lifecycle-policy-text '{
  "rules": [{
    "rulePriority": 1,
    "selection": {
      "tagStatus": "untagged",
      "countType": "sinceImagePushed",
      "countUnit": "days",
      "countNumber": 14
    },
    "action": {"type": "expire"}
  }]
}'

# Registry mirror for air-gapped / rate-limit avoidance
# In /etc/docker/daemon.json:
{
  "registry-mirrors": ["https://my-registry-mirror.internal"]
}
```

---

## 15. Cross-Domain Connections

- **Container layers ↔ Kubernetes pod startup time**: Each image layer must be pulled and decompressed on first use. A 2GB image with 40 layers starts 30–60x slower than an 8MB distroless image. Image optimization directly reduces pod startup time.
- **containerd CRI ↔ kubelet**: `kubelet` manages pods; it talks to containerd via the CRI gRPC socket (`/run/containerd/containerd.sock`). `crictl` is to containerd what `docker` is to the Docker daemon — use it on K8s nodes.
- **Image security scanning ↔ DevSecOps pipeline**: Trivy, Grype, or Snyk scan OCI image layers for CVEs against vulnerability DBs. Integrate at `docker buildx build` time or in CI. Fail builds on CRITICAL severity: `trivy image --exit-code 1 --severity CRITICAL myapp:latest`.
- **Rootless containers ↔ K8s Pod Security Standards**: K8s PSS `Restricted` profile requires `runAsNonRoot: true`, `allowPrivilegeEscalation: false`, `seccompProfile: RuntimeDefault`. Aligns with rootless container best practices.
- **OCI distribution spec ↔ Helm OCI charts**: Helm 3.8+ supports storing charts in OCI registries using the same pull/push API as images — `helm push mychart.tgz oci://myregistry.io/charts`.

---

## 16. Self-Review Checklist

Before submitting any container-related work, verify:

- [ ] **Base image**: Is the base image pinned by digest or at minimum a specific version tag (not `latest`)?
- [ ] **Non-root user**: Does the Dockerfile set `USER <non-zero-uid>` before the final `CMD`/`ENTRYPOINT`?
- [ ] **Layer ordering**: Are infrequently-changing layers (deps) before frequently-changing layers (source)?
- [ ] **Cache mounts**: Are package manager caches using `--mount=type=cache` to avoid re-downloading?
- [ ] **Secret handling**: Are credentials passed via `--mount=type=secret`, not ARG or ENV?
- [ ] **Multi-stage**: Is the production stage starting from a minimal base (distroless/alpine/scratch)?
- [ ] **Read-only rootfs**: Is `readOnlyRootFilesystem: true` set, with tmpfs for writable paths?
- [ ] **Capability drop**: Is `--cap-drop ALL` used, with only explicitly needed caps added back?
- [ ] **seccomp**: Is `RuntimeDefault` seccomp profile applied (K8s) or custom profile for sensitive workloads?
- [ ] **Image signing**: Are images signed with cosign and is signature verification enforced in the cluster (admission webhook)?
- [ ] **Immutable references**: Are production deployments using `image@sha256:...` digests, not tags?
- [ ] **Health checks**: Does the Dockerfile have a `HEALTHCHECK` instruction (or K8s liveness/readiness probe)?
- [ ] **OCI compatibility**: If using a non-Docker runtime (CRI-O, containerd), is the image tested against that runtime?
- [ ] **.dockerignore**: Is a `.dockerignore` present to exclude `.git`, test files, and local config?
- [ ] **Multi-arch**: If the service runs on ARM (Graviton, M-series), is the image built for `linux/arm64`?
