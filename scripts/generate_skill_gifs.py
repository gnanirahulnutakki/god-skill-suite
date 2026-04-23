#!/usr/bin/env python3
"""
Generates animated dark-mode GIFs for each skill in the God-Level Skill Suite.
Each GIF features: skill name, key technologies, and a smooth typing animation.
Requires: Pillow (pip install pillow)
"""

import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ─── Skill metadata: name → (icon emoji, tech stack list, accent color RGB) ───
SKILL_META = {
    "god-meta-conductor":         ("🧠", ["Zero Hallucination", "Task Lock", "Researcher Mindset", "Self-Verification", "Cross-Domain"], (99, 179, 237)),
    "god-dev-core":               ("⚙️", ["DSA", "OOP / SOLID", "Design Patterns", "DRY / YAGNI", "Clean Code"], (154, 230, 180)),
    "god-dev-research":           ("🔬", ["arXiv / ACM / IEEE", "Novelty Checking", "Citation Analysis", "GitHub Research", "Peer Review"], (183, 148, 246)),
    "god-dev-builder":            ("🏗️", ["Scaffolding", "Architecture Decisions", "Iterative Delivery", "Tech Stack Selection", "MVP to Production"], (246, 173, 85)),
    "god-dev-codebase":           ("📖", ["Code Reading", "PR Review", "Surgical Refactoring", "Dependency Audits", "Legacy Systems"], (99, 179, 237)),
    "god-research-review":        ("📚", ["Literature Synthesis", "Critical Analysis", "Experimental Design", "NDCG / Metrics", "Paper Critique"], (183, 148, 246)),
    "god-frontend-mastery":       ("⚛️", ["React 18+ / Next.js", "TypeScript", "Core Web Vitals", "WCAG 2.2", "Micro-frontends"], (97, 218, 251)),
    "god-backend-mastery":        ("🖥️", ["Node.js Event Loop", "FastAPI", "Go Concurrency", "Spring Boot", "Circuit Breakers"], (154, 230, 180)),
    "god-serverless-architecture":("⚡", ["AWS Lambda", "DynamoDB", "API Gateway", "Step Functions", "Cold Start Optimization"], (246, 173, 85)),
    "god-api-design":             ("🔌", ["REST / GraphQL / gRPC", "OpenAPI", "API Versioning", "Rate Limiting", "AsyncAPI"], (99, 179, 237)),
    "god-systems-design":         ("🌐", ["CAP / PACELC", "Raft / Paxos", "CQRS / Event Sourcing", "Consistent Hashing", "Saga Pattern"], (246, 173, 85)),
    "god-architecture-patterns":  ("🏛️", ["Microservices / DDD", "Hexagonal Architecture", "Strangler Fig", "Event-Driven", "ADRs"], (183, 148, 246)),
    "god-testing-mastery":        ("🧪", ["Unit / E2E / Contract", "Mutation Testing", "Chaos Engineering", "Fuzz Testing", "Test Pyramid"], (154, 230, 180)),
    "god-git-workflow":           ("🌿", ["Git Internals", "Trunk-Based Dev", "Bisect / Reflog", "Monorepo Strategy", "Conventional Commits"], (246, 173, 85)),
    "god-auth-protocols":         ("🔑", ["OAuth 2.0 / OIDC", "SAML 2.0", "JWT (RS256/ES256)", "WebAuthn / Passkeys", "SPIFFE / SPIRE"], (99, 179, 237)),
    "god-web3-blockchain":        ("⛓️", ["Solidity / EVM", "Reentrancy Guard", "DeFi / AMM", "MEV / Front-Running", "Gas Optimization"], (183, 148, 246)),
    "god-devops-core":            ("🚢", ["CI/CD Pipelines", "GitOps", "Docker / Helm", "Deployment Strategies", "SRE Practices"], (246, 173, 85)),
    "god-devops-kubernetes":      ("☸️", ["Pods / Services", "RBAC / NetworkPolicy", "HPA / PDB", "Service Mesh", "CrashLoop Triage"], (97, 218, 251)),
    "god-infra-as-code":          ("🏗️", ["Terraform HCL", "Pulumi", "AWS CDK", "Crossplane", "GitOps State"], (154, 230, 180)),
    "god-containers-advanced":    ("📦", ["OCI Spec / OverlayFS", "BuildKit Multi-arch", "Rootless Containers", "gVisor / Kata", "cosign"], (99, 179, 237)),
    "god-linux-mastery":          ("🐧", ["Kernel / Cgroups v2", "eBPF / bpftrace", "Namespaces", "systemd", "Performance Tuning"], (246, 173, 85)),
    "god-platform-engineering":   ("🛤️", ["Backstage IDP", "Golden Paths", "Developer Portals", "Paved Roads", "DORA Metrics"], (183, 148, 246)),
    "god-iam-aws":                ("🔐", ["IAM Policies / Roles", "SCPs", "IRSA", "Permission Boundaries", "IAM Access Analyzer"], (246, 173, 85)),
    "god-iam-azure":              ("🔐", ["Entra ID / RBAC", "Managed Identities", "PIM", "Conditional Access", "Workload Identity"], (99, 179, 237)),
    "god-iam-gcp":                ("🔐", ["Resource Hierarchy", "Service Accounts", "Workload Identity", "Org Policy", "IAM Deny"], (154, 230, 180)),
    "god-security-core":          ("🛡️", ["STRIDE / OWASP", "Zero Trust", "SBOM / SLSA", "Vault / HSM", "Container Hardening"], (246, 173, 85)),
    "god-security-cloud":         ("☁️", ["Kill Chain", "GuardDuty / Defender", "CIEM", "Lateral Movement", "Cloud SIEM"], (183, 148, 246)),
    "god-compliance-governance":  ("📋", ["SOC 2 Type II", "HIPAA / PCI-DSS v4", "GDPR", "ISO 27001:2022", "NIST 800-53"], (99, 179, 237)),
    "god-observability":          ("📡", ["OpenTelemetry", "Prometheus / Grafana", "Jaeger / Zipkin", "Structured Logging", "SLO Alerting"], (97, 218, 251)),
    "god-sre-reliability":        ("📈", ["SLOs / SLIs / Error Budgets", "Toil Reduction", "GameDay", "Incident Response", "Capacity Planning"], (154, 230, 180)),
    "god-performance-engineering":("🚀", ["Flame Graphs", "JVM G1GC / ZGC", "Go pprof", "k6 / Gatling", "CPU / Memory Profiling"], (246, 173, 85)),
    "god-networking":             ("🌐", ["TCP BBR / CUBIC", "TLS 1.3", "DNS Deep Dive", "BGP / eBPF", "VPC Design"], (99, 179, 237)),
    "god-edge-computing":         ("🌍", ["Cloudflare Workers", "KV / R2 / Durable Objects", "Lambda@Edge", "TTFB Optimization", "Vercel Edge"], (183, 148, 246)),
    "god-database-mastery":       ("🗄️", ["PostgreSQL Internals", "EXPLAIN ANALYZE", "Sharding / Replication", "MongoDB / Cassandra", "Redis"], (246, 173, 85)),
    "god-data-engineering":       ("⚙️", ["Spark / Flink", "Airflow / Prefect", "dbt", "Lakehouse", "Streaming Pipelines"], (97, 218, 251)),
    "god-data-cleaning":          ("🧹", ["Outlier Detection", "Imputation", "Feature Engineering", "Data Quality", "Synthetic Generation"], (154, 230, 180)),
    "god-message-streaming":      ("📨", ["Kafka ISR / EOS", "RabbitMQ", "SQS / SNS FIFO", "NATS JetStream", "Pulsar"], (99, 179, 237)),
    "god-search-engineering":     ("🔍", ["Elasticsearch / OpenSearch", "BM25 Tuning", "Analyzer Pipelines", "NDCG Scoring", "Hybrid Search"], (246, 173, 85)),
    "god-vector-databases":       ("🔮", ["HNSW / ANN Algorithms", "Pinecone / Qdrant", "pgvector / Chroma", "Hybrid Search", "Embedding Models"], (183, 148, 246)),
    "god-mlops-core":             ("🤖", ["MLflow / W&B", "Model Serving (Triton)", "Drift Detection", "A/B Testing", "Feature Stores"], (154, 230, 180)),
    "god-mlops-llm":              ("🦾", ["LoRA / QLoRA Fine-tuning", "RLHF", "RAGAS / DeepEval", "Prompt Management", "LLMOps"], (99, 179, 237)),
    "god-ml-data-training":       ("🏋️", ["Dataset Curation", "Loss Functions", "Distributed Training", "Checkpointing", "Mixed Precision"], (246, 173, 85)),
    "god-ai-architect":           ("🏗️", ["RAG Pipelines", "Agent / Tool Use", "Multimodal", "Inference Optimization", "Responsible AI"], (97, 218, 251)),
    "god-ai-prompting":           ("💬", ["Chain-of-Thought", "Few-Shot / Zero-Shot", "Constitutional AI", "System Prompts", "Evaluation"], (183, 148, 246)),
    "god-llm-sdk":                ("🔧", ["Claude / OpenAI SDK", "LangChain / LlamaIndex", "Streaming", "Function Calling", "Token Management"], (154, 230, 180)),
    "god-cost-engineering":       ("💰", ["FinOps", "Reserved Instances", "Spot / Preemptible", "Rightsizing", "Cost Attribution"], (246, 173, 85)),
    "god-project-management":     ("📊", ["OKRs / RICE Scoring", "DORA Metrics", "Kanban / Little's Law", "Blameless Postmortems", "Technical Debt"], (99, 179, 237)),
    "god-tech-support":           ("🔧", ["Stack Trace Analysis", "Log Mining", "Network Debugging", "K8s Triage", "Root Cause Analysis"], (183, 148, 246)),
    "god-devex-tooling":          ("🛠️", ["VS Code / JetBrains", "tmux / fzf / ripgrep", "Debuggers / LSP", "Linters / Formatters", "AI Coding Assistants"], (97, 218, 251)),
    "god-mobile-awareness":       ("📱", ["SwiftUI / UIKit", "Jetpack Compose", "React Native", "Flutter", "Push Notifications"], (154, 230, 180)),
    "god-ui-ux-design":           ("🎨", ["HSL / Oklch Color", "8pt Grid System", "WCAG 2.2 AAA", "Spring Animations", "Design Tokens"], (246, 173, 85)),
}

# ─── Canvas settings ───
WIDTH, HEIGHT = 600, 340
BG_COLOR = (13, 17, 23)          # GitHub dark bg
CARD_COLOR = (22, 27, 34)        # Card bg
BORDER_COLOR = (48, 54, 61)      # Subtle border
TEXT_DIM = (139, 148, 158)       # Muted text
WHITE = (230, 237, 243)

FRAMES = 36          # Total animation frames
HOLD_FRAMES = 10     # Frames to hold on complete state
DURATION_MS = 60     # ms per frame

def load_font(size):
    """Try to load a system font, fall back gracefully."""
    candidates = [
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
        "/System/Library/Fonts/Monaco.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

def draw_frame(skill_name: str, icon: str, techs: list, accent: tuple, revealed: int) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = load_font(18)
    font_icon  = load_font(26)
    font_small = load_font(13)
    font_tech  = load_font(14)
    font_badge = load_font(11)

    # ── Card background ──
    draw.rounded_rectangle([16, 16, WIDTH - 16, HEIGHT - 16], radius=12, fill=CARD_COLOR, outline=BORDER_COLOR)

    # ── Accent top bar ──
    draw.rounded_rectangle([16, 16, WIDTH - 16, 22], radius=4, fill=accent)

    # ── Icon + title ──
    title_text = skill_name.replace("god-", "").replace("-", " ").upper()
    draw.text((32, 34), "GOD-LEVEL", font=font_badge, fill=accent)
    draw.text((32, 52), title_text, font=font_title, fill=WHITE)

    # ── Divider ──
    draw.line([(32, 82), (WIDTH - 32, 82)], fill=BORDER_COLOR, width=1)

    # ── Tech stack (revealed progressively) ──
    y = 96
    for i, tech in enumerate(techs[:5]):
        if i >= revealed:
            break
        # Bullet dot
        draw.ellipse([32, y + 5, 39, y + 12], fill=accent)
        # Tech name
        draw.text((50, y), tech, font=font_tech, fill=WHITE)
        # Typing cursor on last revealed item
        if i == revealed - 1 and revealed <= len(techs):
            cursor_x = 50 + draw.textlength(tech, font=font_tech) + 3
            draw.rectangle([cursor_x, y, cursor_x + 2, y + 14], fill=accent)
        y += 36

    # ── Bottom badge row ──
    badge_y = HEIGHT - 46
    draw.rounded_rectangle([32, badge_y, 32 + 120, badge_y + 22], radius=4, fill=(30, 40, 50), outline=BORDER_COLOR)
    draw.text((42, badge_y + 4), "ZERO HALLUCINATION", font=font_badge, fill=accent)

    draw.rounded_rectangle([164, badge_y, 164 + 90, badge_y + 22], radius=4, fill=(30, 40, 50), outline=BORDER_COLOR)
    draw.text((174, badge_y + 4), "VERIFIED ✓", font=font_badge, fill=(154, 230, 180))

    return img


def make_skill_gif(skill_name: str, output_path: Path):
    icon, techs, accent = SKILL_META.get(skill_name, ("⚡", ["Expert Level"], (99, 179, 237)))

    frames = []
    durations = []

    # Animate: reveal each tech one at a time
    total_items = len(techs[:5])
    frames_per_item = max(1, (FRAMES - HOLD_FRAMES) // total_items)

    for item_idx in range(total_items + 1):
        count = max(1, frames_per_item if item_idx < total_items else HOLD_FRAMES)
        for _ in range(count):
            f = draw_frame(skill_name, icon, techs, accent, item_idx)
            frames.append(f)
            durations.append(DURATION_MS if item_idx < total_items else 120)

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        loop=0,
        duration=durations,
        optimize=True,
    )


def main():
    skills_dir = Path(__file__).parent.parent / "skills"
    out_dir = Path(__file__).parent.parent / "assets" / "skill-gifs"
    out_dir.mkdir(parents=True, exist_ok=True)

    target = sys.argv[1] if len(sys.argv) > 1 else None
    skill_dirs = sorted([d for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith(".")])

    total = 0
    for skill_path in skill_dirs:
        name = skill_path.name
        if target and name != target:
            continue
        out_file = out_dir / f"{name}.gif"
        print(f"  Generating: {name}...", end="", flush=True)
        try:
            make_skill_gif(name, out_file)
            size = out_file.stat().st_size // 1024
            print(f" ✓ ({size}KB)")
            total += 1
        except Exception as e:
            print(f" ✗ ERROR: {e}")

    print(f"\nDone! Generated {total} GIFs → {out_dir}")

if __name__ == "__main__":
    main()
