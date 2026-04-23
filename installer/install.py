#!/usr/bin/env python3
"""
God-Level Skill Suite Installer
================================
Installs god-level AI skills into Claude Code, Codex CLI, Cursor,
Windsurf, Gemini CLI, and any custom path — with interactive selection.

Usage:
    python install.py
    uv run install.py
    python install.py --non-interactive --targets claude-code,cursor
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

# ─────────────────────────────────────────────
# ANSI Color Codes
# ─────────────────────────────────────────────
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIM    = "\033[2m"

def c(color: str, text: str) -> str:
    """Apply color if stdout is a terminal."""
    if sys.stdout.isatty():
        return f"{color}{text}{RESET}"
    return text

def banner():
    print()
    print(c(BOLD + CYAN, "╔══════════════════════════════════════════════════════════════╗"))
    print(c(BOLD + CYAN, "║          GOD-LEVEL SKILL SUITE — INSTALLER v1.0             ║"))
    print(c(BOLD + CYAN, f"║    52 Skills · Every Domain · Zero Hallucination Mode        ║"))
    print(c(BOLD + CYAN, "╚══════════════════════════════════════════════════════════════╝"))
    print()

# ─────────────────────────────────────────────
# Skill Registry
# ─────────────────────────────────────────────
SKILLS = [
    # Meta / Foundation
    {"name": "god-meta-conductor",      "category": "Foundation",      "desc": "Anti-hallucination, focus control, task continuity — LOAD FIRST"},
    {"name": "god-dev-core",            "category": "Foundation",      "desc": "DSA, OOP, SOLID, clean code, self-review loops"},
    {"name": "god-dev-research",        "category": "Foundation",      "desc": "Academic research, paper access, novelty checking, GitHub mining"},
    {"name": "god-dev-builder",         "category": "Foundation",      "desc": "E2E product building, system design, architecture to launch"},
    {"name": "god-dev-codebase",        "category": "Foundation",      "desc": "Codebase indexing, deep review, bug/vuln/quality audit"},

    # DevOps & Infrastructure
    {"name": "god-devops-core",         "category": "DevOps",          "desc": "CI/CD, pipelines, containers, GitOps, secrets, artifacts"},
    {"name": "god-devops-kubernetes",   "category": "DevOps",          "desc": "K8s deep dive, Helm, service mesh, networking, RBAC"},
    {"name": "god-infra-as-code",       "category": "DevOps",          "desc": "Terraform, Pulumi, CDK, Crossplane, Ansible"},
    {"name": "god-containers-advanced", "category": "DevOps",          "desc": "Docker internals, OCI, BuildKit, rootless, image security"},
    {"name": "god-linux-mastery",       "category": "DevOps",          "desc": "Linux internals, shell scripting, eBPF, performance, systemd"},
    {"name": "god-platform-engineering","category": "DevOps",          "desc": "IDP, Backstage, golden paths, developer experience"},

    # Cloud IAM
    {"name": "god-iam-aws",             "category": "Cloud IAM",       "desc": "AWS IAM, SCPs, IRSA, Access Analyzer, cross-account"},
    {"name": "god-iam-azure",           "category": "Cloud IAM",       "desc": "Azure Entra ID, RBAC, Managed Identity, PIM, Conditional Access"},
    {"name": "god-iam-gcp",             "category": "Cloud IAM",       "desc": "GCP IAM, Workload Identity, Org Policies, VPC Service Controls"},

    # Security
    {"name": "god-security-core",       "category": "Security",        "desc": "Threat modeling, OWASP, zero trust, STRIDE, crypto, supply chain"},
    {"name": "god-security-cloud",      "category": "Security",        "desc": "CSPM, CWPP, GuardDuty, Defender, SCC, cloud attack kill chain"},
    {"name": "god-auth-protocols",      "category": "Security",        "desc": "OAuth2, OIDC, SAML, JWT, WebAuthn, mTLS, SPIFFE"},
    {"name": "god-compliance-governance","category": "Security",       "desc": "SOC2, HIPAA, PCI-DSS v4, GDPR, ISO 27001"},

    # Observability & Reliability
    {"name": "god-observability",       "category": "Reliability",     "desc": "Prometheus, Grafana, ELK, OpenSearch, Splunk, Jaeger, OTel"},
    {"name": "god-sre-reliability",     "category": "Reliability",     "desc": "SLO/SLI, error budgets, incident management, chaos engineering"},
    {"name": "god-performance-engineering","category": "Reliability",  "desc": "Profiling, JVM tuning, Go perf, load testing, benchmarking"},

    # Networking
    {"name": "god-networking",          "category": "Networking",      "desc": "TCP/IP, DNS, TLS, BGP, eBPF, service mesh, cloud VPC, load balancing"},
    {"name": "god-edge-computing",      "category": "Networking",      "desc": "CDN, Cloudflare Workers, Lambda@Edge, cache strategies"},

    # Databases & Data
    {"name": "god-database-mastery",    "category": "Data",            "desc": "PostgreSQL, MongoDB, Redis deep dive, Kafka, Elasticsearch"},
    {"name": "god-message-streaming",   "category": "Data",            "desc": "Kafka internals, RabbitMQ, SQS/SNS, NATS, Pulsar"},
    {"name": "god-search-engineering",  "category": "Data",            "desc": "Elasticsearch, OpenSearch, Typesense, vector search, relevance"},
    {"name": "god-data-engineering",    "category": "Data",            "desc": "Spark, Flink, Airflow, dbt, Delta Lake, data quality, ELT"},
    {"name": "god-data-cleaning",       "category": "Data",            "desc": "Data preprocessing, feature engineering, validation, Polars"},
    {"name": "god-vector-databases",    "category": "Data",            "desc": "Pinecone, Qdrant, Weaviate, pgvector, HNSW, hybrid search"},

    # ML & AI
    {"name": "god-mlops-core",          "category": "ML/AI",           "desc": "ML pipelines, experiment tracking, model serving, drift monitoring"},
    {"name": "god-mlops-llm",           "category": "ML/AI",           "desc": "LLM fine-tuning, RAG, evals, vLLM, TGI, AI security"},
    {"name": "god-ml-data-training",    "category": "ML/AI",           "desc": "PyTorch training loops, distributed training, loss functions, optimizers"},
    {"name": "god-ai-architect",        "category": "ML/AI",           "desc": "AI system design, agent architectures, A2A protocols, LLM routing"},
    {"name": "god-ai-prompting",        "category": "ML/AI",           "desc": "Prompt engineering, CoT, few-shot, DSPy, structured output, evals"},
    {"name": "god-llm-sdk",             "category": "ML/AI",           "desc": "Claude SDK, OpenAI SDK, LangChain, LlamaIndex, Bedrock, Ollama"},

    # Software Engineering
    {"name": "god-frontend-mastery",    "category": "Engineering",     "desc": "React, Next.js, TypeScript, TanStack Query, performance, a11y"},
    {"name": "god-backend-mastery",     "category": "Engineering",     "desc": "Node.js, Python, Go, Java Spring — event loops, async, middleware"},
    {"name": "god-serverless-architecture","category":"Engineering",   "desc": "Lambda, DynamoDB, API Gateway, Step Functions, cold start, idempotency"},
    {"name": "god-api-design",          "category": "Engineering",     "desc": "REST, GraphQL, gRPC, AsyncAPI, contracts, versioning, security"},
    {"name": "god-systems-design",      "category": "Engineering",     "desc": "Distributed systems, consensus, consistency, event sourcing, CQRS"},
    {"name": "god-architecture-patterns","category": "Engineering",    "desc": "Microservices, saga, outbox, hexagonal, DDD, strangler fig"},
    {"name": "god-testing-mastery",     "category": "Engineering",     "desc": "pytest, JUnit, Playwright, Pact, Hypothesis, fuzz testing, mutation"},
    {"name": "god-git-workflow",        "category": "Engineering",     "desc": "Git internals, trunk-based dev, rebasing, monorepo, signed commits"},
    {"name": "god-auth-protocols",      "category": "Engineering",     "desc": "OAuth2, OIDC, SAML, JWT, WebAuthn, mTLS, SPIFFE"},
    {"name": "god-web3-blockchain",     "category": "Engineering",     "desc": "Solidity, EVM internals, Rust (Solana), smart contracts, DeFi, EVM gas"},

    # Research
    {"name": "god-research-review",     "category": "Research",        "desc": "Paper critique, peer review, novelty check, replication, citation"},

    # Operations
    {"name": "god-tech-support",        "category": "Operations",      "desc": "RCA, stack traces, log analysis, K8s debugging, distributed tracing"},
    {"name": "god-cost-engineering",    "category": "Operations",      "desc": "FinOps, cloud cost optimization, unit economics, Kubecost"},
    {"name": "god-project-management",  "category": "Operations",      "desc": "Agile, Kanban, estimation, roadmapping, stakeholders, OKRs"},

    # Developer Experience
    {"name": "god-devex-tooling",       "category": "DeveloperEx",     "desc": "VS Code, JetBrains, terminal, uv, ruff, mise, dotfiles, pre-commit"},
    {"name": "god-mobile-awareness",    "category": "DeveloperEx",     "desc": "iOS/Android, React Native, PWA, mobile API design, push notifications"},
    {"name": "god-ui-ux-design",        "category": "DeveloperEx",     "desc": "Interface design, typography, 8pt grids, accessibility, WCAG 2.2, HSL"},
]

# ─────────────────────────────────────────────
# Target Platform Definitions
# ─────────────────────────────────────────────
def get_default_paths() -> dict:
    home = Path.home()
    system = platform.system()

    paths = {
        "claude-code": {
            "label": "Claude Code CLI",
            "description": "Anthropic's Claude Code (claude CLI)",
            "paths": [
                home / ".claude" / "skills",
                home / ".config" / "claude" / "skills",
            ],
            "install_hint": "Install Claude Code: https://docs.anthropic.com/en/docs/claude-code",
            "format": "skill_dir",  # copies full skill directory
        },
        "codex": {
            "label": "OpenAI Codex CLI",
            "description": "OpenAI Codex CLI tool",
            "paths": [
                home / ".codex" / "skills",
                home / ".config" / "codex" / "skills",
            ],
            "install_hint": "Install Codex CLI: npm install -g @openai/codex",
            "format": "skill_dir",
        },
        "cursor": {
            "label": "Cursor",
            "description": "Cursor AI IDE (.mdc project rules)",
            "paths": [
                Path(".cursor") / "rules",  # project-level
                home / ".cursor" / "rules",
            ],
            "install_hint": "Download Cursor: https://cursor.sh",
            "format": "cursor_mdc",
        },
        "windsurf": {
            "label": "Windsurf (Codeium)",
            "description": "Windsurf AI IDE by Codeium",
            "paths": [
                home / ".windsurf" / "skills",
                home / ".config" / "windsurf" / "skills",
            ],
            "install_hint": "Download Windsurf: https://codeium.com/windsurf",
            "format": "skill_dir",
        },
        "gemini": {
            "label": "Gemini CLI",
            "description": "Google Gemini CLI",
            "paths": [
                home / ".gemini" / "skills",
                home / ".config" / "gemini" / "skills",
            ],
            "install_hint": "Install Gemini CLI: npm install -g @google/gemini-cli",
            "format": "skill_dir",
        },
        "continue": {
            "label": "Continue.dev",
            "description": "Continue VS Code / JetBrains extension",
            "paths": [
                home / ".continue" / "skills",
            ],
            "install_hint": "Install Continue: https://continue.dev",
            "format": "skill_dir",
        },
        "perplexity": {
            "label": "Perplexity Computer",
            "description": "Perplexity AI Computer (agentskills format)",
            "paths": [
                home / ".perplexity" / "skills",
            ],
            "install_hint": "Install via: agentskills install <skill-path>",
            "format": "skill_dir",
        },
        "custom": {
            "label": "Custom Path",
            "description": "Install to a custom directory you specify",
            "paths": [],
            "install_hint": "",
            "format": "skill_dir",
        },
    }
    return paths


# ─────────────────────────────────────────────
# Interactive Selection
# ─────────────────────────────────────────────
def select_targets(available_targets: dict) -> list[str]:
    """Interactive multi-select for installation targets."""
    print(c(BOLD, "\n📍 Where would you like to install the skills?\n"))
    print(c(DIM, "   (Space to toggle, Enter to confirm, 'a' for all, 'q' to quit)\n"))

    target_keys = list(available_targets.keys())
    selected = set()
    current = 0

    def render():
        os.system("clear" if platform.system() != "Windows" else "cls")
        banner()
        print(c(BOLD, "📍 Select Installation Targets:\n"))
        print(c(DIM, "   ↑/↓ navigate  |  SPACE toggle  |  A select all  |  ENTER confirm  |  Q quit\n"))
        for i, key in enumerate(target_keys):
            t = available_targets[key]
            marker = "[✓]" if key in selected else "[ ]"
            prefix = "→ " if i == current else "  "
            color = GREEN if key in selected else RESET
            cursor_color = CYAN + BOLD if i == current else RESET
            print(f"  {c(cursor_color, prefix)}{c(color, marker)}  {c(BOLD if i == current else RESET, t['label']): <25}  {c(DIM, t['description'])}")
        print()
        if selected:
            print(c(GREEN, f"  Selected: {', '.join(selected)}"))
        print()

    # Simple fallback for non-interactive environments
    if not sys.stdin.isatty():
        print("Non-interactive mode: specify --targets flag.")
        return []

    def getch():
        if platform.system() == "Windows":
            import msvcrt
            key = msvcrt.getch()
            if key in (b'\x00', b'\xe0'):
                key = msvcrt.getch()
                if key == b'H': return '\x1b[A'
                if key == b'P': return '\x1b[B'
                return key.decode('utf-8', 'ignore')
            return key.decode('utf-8', 'ignore')
        else:
            import tty, termios
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    ch2 = sys.stdin.read(2)
                    return ch + ch2
                return ch
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

    render()
    while True:
        key = getch()
        if key in ('\x1b[A', 'k'):  # up
            current = (current - 1) % len(target_keys)
        elif key in ('\x1b[B', 'j'):  # down
            current = (current + 1) % len(target_keys)
        elif key == ' ':  # toggle
            k = target_keys[current]
            if k in selected:
                selected.remove(k)
            else:
                selected.add(k)
        elif key in ('a', 'A'):  # all
            if len(selected) == len(target_keys):
                selected.clear()
            else:
                selected = set(target_keys)
        elif key in ('\r', '\n'):  # confirm
            if selected:
                break
            else:
                print(c(YELLOW, "\n  Please select at least one target.\n"))
        elif key in ('q', 'Q', '\x03'):  # quit
            print(c(YELLOW, "\nInstallation cancelled."))
            sys.exit(0)
        render()

    return list(selected)


def select_skill_categories(all_skills: list) -> list:
    """Let user select which categories to install."""
    categories = {}
    for s in all_skills:
        cat = s["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(s)

    print(c(BOLD, "\n📦 Which skill categories to install?\n"))
    print(c(DIM, "   Options:\n"))
    print(f"  {c(GREEN, '[1]')} Install ALL {len(all_skills)} skills (recommended — full god-level suite)")
    print(f"  {c(CYAN,  '[2]')} Select by category")
    print(f"  {c(YELLOW,'[3]')} Select individual skills")
    print()

    choice = input(c(BOLD, "  Your choice [1/2/3]: ")).strip()

    if choice == "1" or choice == "":
        return all_skills
    elif choice == "2":
        print(c(BOLD, "\n  Select categories (comma-separated numbers):\n"))
        cat_list = list(categories.keys())
        for i, cat in enumerate(cat_list, 1):
            count = len(categories[cat])
            print(f"  [{i:2}] {cat: <25} ({count} skills)")
        print()
        choices = input(c(BOLD, "  Categories (e.g. 1,3,5 or 'all'): ")).strip()
        if choices.lower() == "all":
            return all_skills
        selected_skills = []
        for num in choices.split(","):
            idx = int(num.strip()) - 1
            if 0 <= idx < len(cat_list):
                selected_skills.extend(categories[cat_list[idx]])
        return selected_skills
    elif choice == "3":
        print(c(BOLD, "\n  Select skills (comma-separated numbers):\n"))
        for i, s in enumerate(all_skills, 1):
            print(f"  [{i:2}] {s['name']: <35} {c(DIM, s['desc'][:50])}")
        print()
        choices = input(c(BOLD, "  Skills (e.g. 1,4,7): ")).strip()
        selected = []
        for num in choices.split(","):
            idx = int(num.strip()) - 1
            if 0 <= idx < len(all_skills):
                selected.append(all_skills[idx])
        return selected
    return all_skills


def get_custom_path() -> Path:
    """Prompt for a custom installation path."""
    print(c(BOLD, "\n  Enter custom installation path:"))
    path_str = input(c(CYAN, "  Path: ")).strip()
    path = Path(path_str).expanduser().resolve()
    return path


def resolve_install_path(target_key: str, target_info: dict) -> Optional[Path]:
    """Resolve the actual installation path for a target."""
    if target_key == "custom":
        return get_custom_path()

    # Try each candidate path
    for candidate in target_info["paths"]:
        parent = candidate.parent
        if parent.exists():
            return candidate

    # If none found, use first option and create it
    if target_info["paths"]:
        return target_info["paths"][0]

    return None


# ─────────────────────────────────────────────
# Installation Engine
# ─────────────────────────────────────────────
def get_skills_source_dir() -> Path:
    """Locate the skills directory relative to this script."""
    script_dir = Path(__file__).parent
    # Try common locations
    candidates = [
        script_dir / "skills",
        script_dir.parent / "skills",
        script_dir.parent.parent / "skills",
        Path.cwd() / "skills",
    ]
    for c_path in candidates:
        if c_path.exists() and c_path.is_dir():
            return c_path

    raise FileNotFoundError(
        "Could not locate 'skills/' directory. "
        "Ensure you're running from the god-skill-suite repository root."
    )


def install_skill(skill: dict, target_path: Path, target_format: str = "skill_dir", dry_run: bool = False) -> bool:
    """Install a single skill to the target path."""
    skill_name = skill["name"]

    try:
        source_dir = get_skills_source_dir() / skill_name
    except FileNotFoundError as e:
        print(c(RED, f"  ✗ {skill_name}: {e}"))
        return False

    if not source_dir.exists():
        print(c(YELLOW, f"  ⚠ {skill_name}: source not found at {source_dir}"))
        return False

    dest_dir = target_path / skill_name

    if dry_run:
        dest_display = dest_dir if target_format != "cursor_mdc" else target_path / f"{skill_name}.mdc"
        print(c(CYAN, f"  [DRY RUN] Would install: {skill_name} → {dest_display}"))
        return True

    try:
        target_path.mkdir(parents=True, exist_ok=True)
        if target_format == "cursor_mdc":
            mdc_file = target_path / f"{skill_name}.mdc"
            skill_source = source_dir / "SKILL.md"
            if not skill_source.exists():
                return False
            if mdc_file.exists():
                mdc_file.unlink()
            shutil.copy2(skill_source, mdc_file)
        else:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(source_dir, dest_dir)
        return True
    except Exception as e:
        print(c(RED, f"  ✗ {skill_name}: {e}"))
        return False


def try_agentskills_install(skill: dict, source_dir: Path) -> bool:
    """Try installing via agentskills CLI if available."""
    if shutil.which("agentskills") is None:
        return False

    skill_path = source_dir / skill["name"]
    if not skill_path.exists():
        return False

    try:
        result = subprocess.run(
            ["agentskills", "install", str(skill_path)],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def run_installation(
    selected_skills: list,
    selected_targets: list[str],
    target_configs: dict,
    dry_run: bool = False,
) -> dict:
    """Run the full installation."""
    results = {"success": [], "failed": [], "skipped": []}

    # Resolve paths for each target
    target_paths = {}
    for target_key in selected_targets:
        config = target_configs[target_key]
        path = resolve_install_path(target_key, config)
        if path:
            target_paths[target_key] = path
        else:
            print(c(YELLOW, f"  ⚠ Could not resolve path for {config['label']}"))

    print()
    print(c(BOLD, f"  Installing {len(selected_skills)} skills to {len(target_paths)} target(s)...\n"))

    for target_key, install_path in target_paths.items():
        config = target_configs[target_key]
        print(c(BOLD + BLUE, f"\n  ▶ {config['label']}"))
        print(c(DIM, f"    → {install_path}\n"))

        for skill in selected_skills:
            success = install_skill(skill, install_path, target_format=config.get("format", "skill_dir"), dry_run=dry_run)

            # Also try agentskills for Perplexity target
            if target_key == "perplexity" and not dry_run:
                try:
                    source = get_skills_source_dir()
                    agentskills_ok = try_agentskills_install(skill, source)
                except FileNotFoundError:
                    agentskills_ok = False

                if agentskills_ok:
                    print(c(GREEN, f"    ✓ {skill['name']} (via agentskills)"))
                    results["success"].append(f"{target_key}:{skill['name']}")
                    continue

            if success:
                print(c(GREEN, f"    ✓ {skill['name']}"))
                results["success"].append(f"{target_key}:{skill['name']}")
            else:
                results["failed"].append(f"{target_key}:{skill['name']}")

    return results


# ─────────────────────────────────────────────
# Post-Install Instructions
# ─────────────────────────────────────────────
def print_usage_guide(installed_targets: list[str], target_configs: dict, skills: list):
    print()
    print(c(BOLD + GREEN, "╔══════════════════════════════════════════════════════════════╗"))
    print(c(BOLD + GREEN, "║                  INSTALLATION COMPLETE ✓                    ║"))
    print(c(BOLD + GREEN, "╚══════════════════════════════════════════════════════════════╝"))
    print()
    print(c(BOLD, "  HOW TO USE YOUR GOD-LEVEL SKILLS\n"))

    usage = {
        "claude-code": [
            "Claude Code automatically loads skills from ~/.claude/skills/",
            "Start a session: claude",
            "The meta-conductor skill loads automatically — zero-hallucination mode activates",
            "Load specific skills with: /skill god-devops-core",
            "Or mention the skill in your prompt: 'Using god-kubernetes skill, review this manifest'",
        ],
        "codex": [
            "Codex CLI loads skills from ~/.codex/skills/",
            "Start a session: codex",
            "Reference skills in your prompt: 'Apply god-security-core to audit this code'",
        ],
        "cursor": [
            "Cursor automatically applies MDC rules from .cursor/rules/ in your project",
            "These have been installed as .mdc rule files.",
            "In chat: '@god-dev-core Please review this function'",
        ],
        "windsurf": [
            "Windsurf loads skills from ~/.windsurf/skills/",
            "In Cascade chat: reference skill by name to activate its principles",
        ],
        "gemini": [
            "Gemini CLI loads skills from ~/.gemini/skills/",
            "Run: gemini --skill god-mlops-core 'Help me design this ML pipeline'",
        ],
        "perplexity": [
            "Perplexity Computer: go to perplexity.ai/computer/skills",
            "Your skills are saved to your account — available in all sessions",
            "Mention the skill name in your prompt to activate it",
        ],
        "custom": [
            "Point your AI tool to the installation directory",
            "Each skill is a directory with a SKILL.md file",
            "Load skills by reading the SKILL.md content into your AI's context",
        ],
    }

    for target in installed_targets:
        config = target_configs[target]
        instructions = usage.get(target, ["Skills installed. Check your tool's documentation for skill loading."])
        print(c(BOLD + CYAN, f"  ▶ {config['label']}"))
        for line in instructions:
            print(c(DIM, f"    • {line}"))
        print()

    print(c(BOLD, "  RECOMMENDED LOAD ORDER\n"))
    print(c(DIM, "  Load these first in every session for maximum effectiveness:\n"))
    priority = [
        ("1st", "god-meta-conductor",    "Anti-hallucination + focus control"),
        ("2nd", "god-dev-core",          "Developer mindset + DSA + OOP"),
        ("3rd", "god-dev-research",      "Research methodology"),
        ("4th", "(domain skill)",        "e.g. god-devops-kubernetes for K8s work"),
        ("5th", "(task skill)",          "e.g. god-dev-codebase for code review"),
    ]
    for order, name, desc in priority:
        print(f"    {c(YELLOW, order):<8} {c(GREEN, name):<35} {c(DIM, desc)}")

    print()
    print(c(BOLD, "  FULL SKILL LIST\n"))
    categories = {}
    for s in skills:
        cat = s["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(s)

    for cat, cat_skills in categories.items():
        print(c(BOLD + CYAN, f"  {cat}"))
        for s in cat_skills:
            print(f"    {c(GREEN, '•')} {s['name']:<35} {c(DIM, s['desc'][:55])}")
        print()

    print(c(BOLD, "  GITHUB REPOSITORY"))
    print(c(CYAN, "    https://github.com/gnanirahulnutakki/god-skill-suite"))
    print(c(DIM,  "    Star it, fork it, contribute to it.\n"))


# ─────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="God-Level Skill Suite Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python install.py                          # Interactive mode
  python install.py --dry-run               # Preview without installing
  python install.py --targets claude-code   # Install to Claude Code only
  python install.py --targets claude-code,cursor --all-skills
  uv run install.py                         # Using uv package manager
        """
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview installation without making changes")
    parser.add_argument("--targets", type=str, help="Comma-separated targets: claude-code,codex,cursor,windsurf,gemini,perplexity,custom")
    parser.add_argument("--all-skills", action="store_true", help="Install all skills without prompting")
    parser.add_argument("--list-skills", action="store_true", help="List all available skills and exit")
    parser.add_argument("--list-targets", action="store_true", help="List all available targets and exit")
    parser.add_argument("--non-interactive", action="store_true", help="Non-interactive mode (use with --targets and --all-skills)")

    args = parser.parse_args()
    target_configs = get_default_paths()

    if args.list_skills:
        print(c(BOLD, "\nAvailable Skills:\n"))
        for s in SKILLS:
            print(f"  {c(GREEN, s['name']):<40} {c(DIM, s['desc'])}")
        print()
        return

    if args.list_targets:
        print(c(BOLD, "\nAvailable Targets:\n"))
        for key, config in target_configs.items():
            print(f"  {c(GREEN, key):<20} {config['label']}")
        print()
        return

    banner()

    if args.dry_run:
        print(c(YELLOW, "  DRY RUN MODE — No files will be modified\n"))

    # Determine targets
    if args.targets:
        selected_targets = [t.strip() for t in args.targets.split(",")]
        invalid = [t for t in selected_targets if t not in target_configs]
        if invalid:
            print(c(RED, f"  Unknown targets: {', '.join(invalid)}"))
            print(c(DIM, f"  Valid targets: {', '.join(target_configs.keys())}"))
            sys.exit(1)
    else:
        selected_targets = select_targets(target_configs)

    # Handle custom target
    if "custom" in selected_targets:
        custom_path = get_custom_path()
        target_configs["custom"]["paths"] = [custom_path]

    # Determine skills
    if args.all_skills or args.non_interactive:
        selected_skills = SKILLS
    else:
        selected_skills = select_skill_categories(SKILLS)

    if not selected_skills:
        print(c(YELLOW, "\n  No skills selected. Exiting."))
        return

    # Confirm
    print(c(BOLD, f"\n  Ready to install:"))
    print(f"    • {c(GREEN, str(len(selected_skills)))} skills")
    print(f"    • to {c(GREEN, str(len(selected_targets)))} target(s): {', '.join(selected_targets)}")
    if args.dry_run:
        print(c(YELLOW, "    • DRY RUN — no actual changes"))
    print()

    if not args.non_interactive:
        confirm = input(c(BOLD, "  Proceed? [Y/n]: ")).strip().lower()
        if confirm in ("n", "no"):
            print(c(YELLOW, "  Installation cancelled."))
            return

    # Run installation
    results = run_installation(
        selected_skills=selected_skills,
        selected_targets=selected_targets,
        target_configs=target_configs,
        dry_run=args.dry_run,
    )

    # Summary
    print()
    total = len(results["success"]) + len(results["failed"])
    print(c(BOLD, f"  Results: {c(GREEN, str(len(results['success'])))} succeeded, {c(RED, str(len(results['failed'])))} failed"))

    if results["failed"]:
        print(c(RED, "\n  Failed installations:"))
        for f in results["failed"]:
            print(c(RED, f"    ✗ {f}"))

    if not args.dry_run and results["success"]:
        print_usage_guide(selected_targets, target_configs, SKILLS)


if __name__ == "__main__":
    main()
