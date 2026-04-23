# Changelog

All notable changes to the God-Level Skill Suite are documented here.

---

## [1.1.0] — 2026-04-23

### Added
- **3 New Skills:**
  - `god-serverless-architecture` — AWS Lambda, DynamoDB, API Gateway, Step Functions, cold start optimization, idempotency
  - `god-ui-ux-design` — HSL/Oklch color theory, 8pt grid systems, WCAG 2.2 AAA accessibility, Spring animations, design tokens
  - `god-web3-blockchain` — Solidity, EVM storage model, Reentrancy/CEI patterns, MEV/front-running, DeFi/AMM mechanics
- **Automated Test Framework** (`scripts/evaluate_skills.py`)
  - Zero-dependency Python test runner supporting Ollama and OpenAI providers
  - Adversarial anti-hallucination and task-scope-lock test assertions
  - Markdown report output (`--output docs/TEST_RESULTS.md`)
- **Prompt Libraries** — Every skill now ships a `prompts/examples.md` with domain-specific prompts
- **Test Suites** — Every skill now ships a `tests.json` with adversarial behavioral assertions
- **Skill GIF Generator** (`scripts/generate_skill_gifs.py`)
  - Generates animated dark-mode GIFs for all 51 skills using Pillow
  - Each GIF features unique accent color, key tech stack, and typing animation
- **Video Trailer Assets** — Cinematic trailer embedded in README hero section
- **docs/TESTING.md** — Full documentation for the evaluation framework
- **docs/USAGE.md** — Updated with Prompt Library section and per-tool usage
- **CONTRIBUTING.md** — Skill authoring guide with quality bar requirements and PR process
- **GitHub CI** — Automated validation of YAML frontmatter on all PRs

### Modified
- `god-meta-conductor`: Added **Law 11: The Thinking Model Restraint** for models with internal monologue (o1, o3, Claude 3.7+)
- `installer/install.py`: Windows terminal compatibility fix (msvcrt fallback for getch)
- `installer/install.py`: Cursor target now installs `.mdc` format files to `.cursor/rules/`
- `README.md`: Complete UX redesign — hero video, 3-panel "How It Works" strip, per-skill animated GIFs in accordions

### Fixed
- Cross-platform installer crash on Windows due to Unix-only `termios`/`tty` imports
- Skill count now dynamically computed from `SKILLS` registry (no more hardcoded count)

---

## [1.0.0] — 2026-01-01

### Added
- Initial release of the God-Level Skill Suite
- 49 production-grade AI skills across 12 categories
- Interactive Python installer with support for Claude Code, Cursor, Codex, Windsurf, Gemini CLI, Continue, and Perplexity
- Zero external dependencies — pure stdlib installer
