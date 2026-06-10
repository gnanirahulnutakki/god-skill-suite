---
name: god-linting-quality
description: "God-level linting and code quality mastery. Unified coverage of linting tools across languages and file types: ruff (Python), eslint (JavaScript/TypeScript), pylint (Python legacy), shellcheck (bash/sh), yamllint (YAML), hadolint (Dockerfile), golangci-lint (Go), markdownlint (Markdown), pre-commit hooks for automated enforcement, CI integration patterns, auto-fix workflows, custom rule authoring, and a framework for choosing the right linter per technology. Linting is not optional — it is the first line of defense against bugs that humans miss."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Linting & Code Quality

## Anti-Hallucination Rules

- NEVER invent linter rule codes — `E501`, `F401`, `W291` are real ruff/flake8 codes; verify others against the tool's docs.
- NEVER confuse tool-specific rule namespaces — ESLint uses `no-unused-vars`, ruff uses `F841`, ShellCheck uses `SC2086`.
- NEVER claim a linter supports a language it doesn't — ruff is Python-only, ESLint is JS/TS-only.
- ALWAYS specify the tool version when discussing rules — ESLint 9 uses flat config, ESLint 8 uses `.eslintrc`.

---

## 1. Linter Selection Guide

```
Language/Format    Recommended Linter     Alternative
───────────────────────────────────────────────────────────
Python             ruff                   pylint, flake8+plugins
JavaScript/TS      eslint + prettier      biome
Go                 golangci-lint          staticcheck, go vet
Rust               clippy                 (built-in)
Shell/Bash         shellcheck             (no real alternative)
YAML               yamllint               (no real alternative)
Dockerfile         hadolint               (no real alternative)
Markdown           markdownlint           remark-lint
JSON               spectral (API)         jsonlint
Terraform          tflint                 terraform validate
Kubernetes YAML    kubeconform            kubeval (deprecated)
Helm charts        helm lint              ct lint
SQL                sqlfluff               (no major alternative)
CSS                stylelint              (no major alternative)
```

---

## 2. ruff (Python)

The fastest Python linter — replaces flake8, isort, pycodestyle, pyflakes, and more.

```toml
# pyproject.toml
[tool.ruff]
target-version = "py311"
line-length = 100
fix = true                          # Auto-fix on run

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "UP",     # pyupgrade
    "B",      # flake8-bugbear
    "SIM",    # flake8-simplify
    "PTH",    # flake8-use-pathlib
    "RUF",    # ruff-specific rules
    "S",      # flake8-bandit (security)
    "C4",     # flake8-comprehensions
    "DTZ",    # flake8-datetimez
    "T20",    # flake8-print (no print in production)
    "ERA",    # eradicate (commented-out code)
    "PL",     # pylint subset
    "PERF",   # perflint (performance)
]
ignore = [
    "E501",   # Line length (handled by formatter)
    "S101",   # assert usage (ok in tests)
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "T20"]    # Allow assert and print in tests
"scripts/**/*.py" = ["T20"]          # Allow print in scripts

[tool.ruff.lint.isort]
known-first-party = ["mypackage"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

```bash
# Run ruff
ruff check .                         # Lint
ruff check . --fix                   # Lint + auto-fix
ruff format .                        # Format (replaces black)
ruff check --select I --fix .        # Fix imports only
```

---

## 3. ESLint (JavaScript/TypeScript)

```javascript
// eslint.config.js — ESLint 9+ flat config
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import react from "eslint-plugin-react";
import prettier from "eslint-config-prettier";

export default [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  prettier,                          // Must be last — disables conflicting rules
  {
    files: ["**/*.{ts,tsx}"],
    plugins: {
      react,
    },
    rules: {
      "no-unused-vars": "off",                          // Use TS version
      "@typescript-eslint/no-unused-vars": ["error", {
        argsIgnorePattern: "^_",                        // Allow _unused params
      }],
      "@typescript-eslint/no-explicit-any": "error",    // Ban 'any' type
      "@typescript-eslint/explicit-function-return-type": "warn",
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "react/jsx-no-leaked-render": "error",
      "react/self-closing-comp": "error",
    },
  },
  {
    files: ["**/*.test.{ts,tsx}"],
    rules: {
      "@typescript-eslint/no-explicit-any": "off",      // Relax in tests
    },
  },
];
```

---

## 4. ShellCheck

```bash
# Run ShellCheck
shellcheck script.sh
shellcheck -S error scripts/*.sh       # Only errors (CI gate)
shellcheck -f diff script.sh           # Show fixes as diffs

# Critical ShellCheck rules:
# SC2086: Double quote to prevent globbing and word splitting
# SC2046: Quote command substitution
# SC2006: Use $(...) instead of backticks
# SC2015: Note that A && B || C is not if-then-else
# SC2034: Variable appears unused
# SC2155: Declare and assign separately
# SC2164: Use cd ... || exit
# SC2181: Check exit code directly, not via $?
# SC2236: Use -z/-n instead of ! -z/! -n
```

---

## 5. hadolint (Dockerfile)

```bash
# Run hadolint
hadolint Dockerfile
hadolint --ignore DL3008 --ignore DL3013 Dockerfile

# Critical hadolint rules:
# DL3006: Always tag the version in FROM
# DL3008: Pin versions in apt-get install (apt-get install curl=7.88.1-10+deb12u5)
# DL3013: Pin versions in pip install
# DL3018: Pin versions in apk add
# DL3025: Use JSON notation for CMD/ENTRYPOINT
# DL3059: Multiple consecutive RUN instructions (merge them)
# DL4006: Set SHELL to ["/bin/bash", "-o", "pipefail", "-c"]
```

```yaml
# .hadolint.yaml
ignored:
  - DL3008    # Allow unpinned apt packages in dev
trustedRegistries:
  - docker.io
  - gcr.io
  - ghcr.io
override:
  warning:
    - DL3059  # Downgrade from error to warning
```

---

## 6. golangci-lint (Go)

```yaml
# .golangci.yml
linters:
  enable:
    - errcheck          # Check error returns
    - govet             # Suspicious constructs
    - staticcheck       # Comprehensive static analysis
    - unused            # Unused code
    - gosec             # Security issues
    - gocritic          # Opinionated lints
    - gofumpt           # Strict formatting
    - revive            # Fast, extensible linter
    - misspell          # Spelling errors
    - prealloc          # Slice preallocation
    - exhaustive        # Exhaustive enum switches
    - errorlint         # Error wrapping

linters-settings:
  govet:
    check-shadowing: true
  errcheck:
    check-type-assertions: true
  gocritic:
    enabled-tags:
      - diagnostic
      - performance
      - style

issues:
  exclude-rules:
    - path: _test\.go
      linters:
        - gosec         # Relax security in tests
        - errcheck      # Relax error checking in tests
  max-issues-per-linter: 0
  max-same-issues: 0
```

---

## 7. pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
        args: [--allow-multiple-documents]
      - id: check-json
      - id: check-merge-conflict
      - id: detect-private-key
      - id: check-added-large-files
        args: [--maxkb=500]

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.56.0
    hooks:
      - id: eslint
        files: \.[jt]sx?$
        types: [file]

  - repo: https://github.com/koalaman/shellcheck-precommit
    rev: v0.9.0
    hooks:
      - id: shellcheck

  - repo: https://github.com/adrienverge/yamllint
    rev: v1.33.0
    hooks:
      - id: yamllint
        args: [-c, .yamllint.yaml]

  - repo: https://github.com/hadolint/hadolint
    rev: v2.12.0
    hooks:
      - id: hadolint-docker
```

```bash
# Setup pre-commit
pip install pre-commit
pre-commit install                    # Install hooks
pre-commit run --all-files           # Run on all files
pre-commit autoupdate                # Update hook versions
```

---

## 8. CI Integration Pattern

```yaml
# GitHub Actions — lint job
lint:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Python linting (ruff)
      uses: astral-sh/ruff-action@v1
      with:
        args: "check ."

    - name: YAML lint
      run: |
        pip install yamllint
        yamllint -f parsable .

    - name: ShellCheck
      uses: ludeeus/action-shellcheck@master
      with:
        severity: warning

    - name: Dockerfile lint
      uses: hadolint/hadolint-action@v3.1.0
      with:
        dockerfile: Dockerfile
        failure-threshold: warning

    - name: Kubernetes manifest validation
      run: |
        curl -sL https://github.com/yannh/kubeconform/releases/latest/download/kubeconform-linux-amd64.tar.gz | tar xz
        ./kubeconform -strict -summary k8s/
```

---

## Cross-Domain Connections

**Linting ↔ CI/CD:** Linters in CI are non-negotiable gates. Auto-fix in pre-commit, block in CI. Never rely solely on local enforcement.

**Linting ↔ Security:** Security linters (bandit/ruff-S, gosec, eslint-plugin-security) catch vulnerabilities that functional tests miss: SQL injection, hardcoded secrets, insecure deserialization.

**Linting ↔ Code Review:** Automate style enforcement to free code reviewers for logic, architecture, and design review. If a reviewer comments on formatting, the linter is misconfigured.

---

## Self-Review Checklist

- [ ] Every language in the repo has a configured linter
- [ ] pre-commit hooks installed and run on every commit
- [ ] CI pipeline has a lint gate that blocks merge on failure
- [ ] Linter configs are in the repo root (not developer-local)
- [ ] Auto-fix enabled in pre-commit (ruff --fix, eslint --fix)
- [ ] Test files have relaxed rules where appropriate
- [ ] Security linters enabled (ruff S, gosec, eslint-plugin-security)
- [ ] Dockerfile validated with hadolint
- [ ] YAML validated with yamllint (especially CI pipeline files)
- [ ] K8s manifests validated with kubeconform
- [ ] Custom rule suppressions are documented with justification
- [ ] Linter versions pinned in CI and pre-commit config
