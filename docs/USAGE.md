# God-Level Skill Suite — Usage Guide

## Installation Methods

### Method 1: uv (Fastest — Recommended)
```bash
# One-liner: clone and run
git clone https://github.com/gnanirahulnutakki/god-skill-suite.git
cd god-skill-suite
uv run installer/install.py
```

### Method 2: pip
```bash
pip install god-skill-suite
god-skills
```

### Method 3: pipx (Isolated)
```bash
pipx install god-skill-suite
god-skills
```

### Method 4: Shell bootstrap (macOS/Linux)
```bash
curl -sSL https://raw.githubusercontent.com/gnanirahulnutakki/god-skill-suite/main/installer/install.sh | bash
```

### Method 5: PowerShell (Windows)
```powershell
irm https://raw.githubusercontent.com/gnanirahulnutakki/god-skill-suite/main/installer/install.ps1 | iex
```

### Method 6: Manual copy
```bash
# Copy skills directly to your tool's skills directory
cp -r skills/god-meta-conductor ~/.claude/skills/
cp -r skills/god-dev-core ~/.claude/skills/
# ... etc
```

---

## CLI Reference

```
python installer/install.py [OPTIONS]

Options:
  --targets TEXT        Comma-separated: claude-code,codex,cursor,windsurf,
                        gemini,continue,perplexity,custom
  --all-skills          Install all 50 skills without prompting
  --dry-run             Preview what would be installed without making changes
  --non-interactive     Skip all prompts (use with --targets and --all-skills)
  --list-skills         Print all available skills and exit
  --list-targets        Print all supported targets and exit

Examples:
  # Interactive mode (default)
  python installer/install.py

  # Install everything to Claude Code
  python installer/install.py --targets claude-code --all-skills --non-interactive

  # Install to multiple targets
  python installer/install.py --targets claude-code,cursor,codex --all-skills

  # Preview without changing anything
  python installer/install.py --targets claude-code --dry-run

  # Using uv
  uv run installer/install.py --targets claude-code --all-skills

  # Using pip-installed CLI
  god-skills --targets claude-code --all-skills
```

---

## Per-Tool Instructions

### Claude Code

Skills install to `~/.claude/skills/` and are loaded automatically.

```bash
# Verify installation
ls ~/.claude/skills/ | grep god-

# Start Claude Code with skills active
claude

# In a session, reference a skill
> "Load god-devops-kubernetes and review this Helm chart"
```

**Recommended CLAUDE.md addition:**
```markdown
# Skills
Always load god-meta-conductor first. It enforces zero-hallucination behavior
and task focus. Then load domain-specific skills as needed.
```

### Codex CLI (OpenAI)

```bash
# Install Codex CLI first
npm install -g @openai/codex

# Skills install to ~/.codex/skills/
ls ~/.codex/skills/

# Use in a session
codex
> "Using god-security-core, audit this Python file for vulnerabilities"
```

### Cursor

Skills install to `~/.cursor/skills/` (global) or `.cursor/rules/` (project).

In Cursor settings, add to your AI rules:
```
Load god-meta-conductor for all sessions. Apply god-dev-core principles to all code generation.
```

In chat: `@god-iam-aws What permissions does this Lambda need?`

### Windsurf

Skills install to `~/.windsurf/skills/`.

In the Cascade chat panel, reference skills by name to activate them.

### Gemini CLI

```bash
# Install Gemini CLI
npm install -g @google/gemini-cli

# Skills install to ~/.gemini/skills/
gemini

> "Apply god-mlops-core: help me design this ML training pipeline"
```

### Perplexity Computer

The installer will attempt to use the `agentskills` CLI if available:
```bash
pip install agentskills
agentskills install skills/god-meta-conductor/
```

Or upload manually at: https://www.perplexity.ai/computer/skills

### Custom Path

```bash
python installer/install.py --targets custom
# You'll be prompted for your directory path
```

---

## Prompt Libraries

Every skill now includes an extensive, specialized prompt library precisely tuned to evoke the best "Pro-Developer" logic from the model. 

1. Navigate to the skill folder (e.g. `skills/god-backend-mastery/prompts/`)
2. Open `examples.md`
3. Copy one of the optimized prompts (such as "Deep Code Review", "System Design", or "Troubleshooting").
4. Paste the prompt into your AI chat session alongside the `SKILL.md` file.

These prompts bypass generalized LLM pleasantries and immediately force the model into rigorous architectural or code-review contexts.

---

## Loading Skills Effectively

### The Golden Rule: Load Meta-Conductor First

Every session, every time:
```
Load god-meta-conductor.
```

This activates:
- Zero-hallucination mode
- Tunnel-vision task focus
- Mid-task message handling (extensions, not redirects)
- Explicit uncertainty declarations
- Self-verification loops

### Domain Combinations That Work Best

| Task | Skills to Load |
|------|---------------|
| Code review | `god-meta-conductor` + `god-dev-codebase` + `god-security-core` + `god-dev-core` |
| K8s debugging | `god-meta-conductor` + `god-devops-kubernetes` + `god-observability` + `god-networking` |
| ML pipeline | `god-meta-conductor` + `god-mlops-core` + `god-data-engineering` + `god-observability` |
| Security audit | `god-meta-conductor` + `god-security-core` + `god-security-cloud` + `god-iam-aws` |
| System design | `god-meta-conductor` + `god-systems-design` + `god-database-mastery` + `god-architecture-patterns` |
| Research paper | `god-meta-conductor` + `god-dev-research` + `god-research-review` + `god-ai-prompting` |
| DevOps setup | `god-meta-conductor` + `god-devops-core` + `god-devops-kubernetes` + `god-infra-as-code` + `god-observability` |
| LLM app | `god-meta-conductor` + `god-llm-sdk` + `god-mlops-llm` + `god-ai-architect` + `god-ai-prompting` |
| Full-stack | `god-meta-conductor` + `god-frontend-mastery` + `god-backend-mastery` + `god-api-design` + `god-database-mastery` |

### Telling the Model to Use a Skill

Different tools have different syntax, but the pattern is universal:

```
"Using the god-devops-kubernetes skill, [task]"
"Apply god-security-core principles to [task]"
"As a god-level researcher (god-dev-research), find papers on [topic]"
"With god-meta-conductor active, review this entire codebase for [issues]"
```

---

## Updating Skills

```bash
cd god-skill-suite
git pull
python installer/install.py --targets claude-code --all-skills --non-interactive
```

---

## Troubleshooting

### Skills not loading
- Verify the skill is in the correct directory: `ls ~/.claude/skills/god-meta-conductor/`
- Ensure `SKILL.md` exists inside the skill directory
- Check your tool's documentation for skill loading mechanism

### Installer fails
```bash
# Try dry-run to see what it would do
python installer/install.py --dry-run

# Check Python version (3.10+ required)
python --version

# Check if target path is writable
ls -la ~/.claude/
```

### agentskills not found (for Perplexity)
```bash
pip install agentskills
# or
uv pip install agentskills
```
