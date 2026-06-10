---
name: god-yaml-config
description: "God-level YAML and configuration file mastery. Covers YAML syntax (scalars, sequences, mappings), anchors and aliases, merge keys, multi-document files, the Norway problem (unquoted booleans), common gotchas (indentation, trailing spaces, implicit type coercion), JSON Schema validation, yamllint configuration, TOML vs YAML vs JSON comparison, environment-specific config management, secret handling patterns, and best practices for Kubernetes manifests, Helm values, CI/CD pipelines, and application configuration. Never fabricate YAML spec features — verify against yaml.org/spec."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level YAML & Configuration Mastery

## Anti-Hallucination Rules

- NEVER claim YAML supports a feature without verifying (e.g., YAML does NOT have native inheritance beyond anchors/aliases).
- NEVER confuse YAML 1.1 and YAML 1.2 behavior — boolean parsing differs significantly.
- NEVER ignore the Norway problem — `NO` is parsed as boolean `false` in YAML 1.1, not the string "NO".
- ALWAYS specify which YAML version when discussing type coercion (1.1 vs 1.2).
- ALWAYS recommend quoting ambiguous values.

---

## 1. YAML Fundamentals

### 1.1 Scalar Types and the Norway Problem

```yaml
# Strings — always safe when quoted
name: "Alice"
city: 'New York'
description: This is an unquoted string

# The Norway Problem (YAML 1.1):
# These are ALL parsed as boolean false:
country: NO          # boolean false, not the string "NO"
answer: no           # boolean false
flag: off            # boolean false
switch: n            # boolean false (some parsers)
value: false         # boolean false

# These are ALL parsed as boolean true:
answer: YES          # boolean true
flag: on             # boolean true
switch: y            # boolean true (some parsers)

# FIX: Always quote strings that could be misinterpreted
country: "NO"        # String "NO" — Norway is saved!
answer: "yes"        # String "yes"
flag: "on"           # String "on"

# Numbers — implicit type coercion
port: 8080           # integer
version: 1.0         # float (not string!)
version: "1.0"       # string — THIS is what you probably want
zip_code: 01234      # OCTAL number in YAML 1.1! Not "01234"
zip_code: "01234"    # String — correct

# Dates — implicit parsing
date: 2024-01-15     # Parsed as Date object, not string!
date: "2024-01-15"   # String — explicit is better

# Null values
value: null
value: ~
value:               # Empty value = null

# Special floats
infinity: .inf
negative_infinity: -.inf
not_a_number: .nan
```

### 1.2 Multiline Strings

```yaml
# Literal block scalar (|) — preserves newlines
description: |
  This is line one.
  This is line two.
  
  This is line four (blank line preserved).
# Result: "This is line one.\nThis is line two.\n\nThis is line four (blank line preserved).\n"

# Folded block scalar (>) — newlines become spaces
description: >
  This is a long paragraph
  that will be folded into
  a single line.
# Result: "This is a long paragraph that will be folded into a single line.\n"

# Chomping indicators:
# | or >     — clip (default): single trailing newline
# |- or >-   — strip: no trailing newline
# |+ or >+   — keep: all trailing newlines preserved

command: >-
  kubectl apply
  -f deployment.yaml
  --namespace production
# Result: "kubectl apply -f deployment.yaml --namespace production" (no trailing newline)
```

---

## 2. Anchors, Aliases, and Merge Keys

```yaml
# Anchor (&) and Alias (*)
defaults: &defaults
  timeout: 30
  retries: 3
  log_level: info

development:
  <<: *defaults              # Merge key — imports all fields from anchor
  log_level: debug           # Override specific field
  database:
    host: localhost

production:
  <<: *defaults
  timeout: 10               # Override
  database:
    host: prod-db.internal

# Anchor for repeated values
database_config: &db_config
  driver: postgresql
  pool_size: 10
  pool_timeout: 30

services:
  user_service:
    database:
      <<: *db_config
      name: users_db
  order_service:
    database:
      <<: *db_config
      name: orders_db
```

**Limitations of anchors:**
- Anchors are document-scoped — they cannot reference across YAML documents.
- Anchors are a YAML feature, NOT supported by all tools (e.g., `yq` and `kustomize` handle them, but Helm's template engine does not use anchors for chart values).
- Merge keys (`<<:`) are not part of the YAML 1.2 spec — they are a YAML 1.1 extension. Behavior may vary between parsers.

---

## 3. Multi-Document Files

```yaml
# Document separator: ---
# Document end: ...

---
apiVersion: v1
kind: Namespace
metadata:
  name: production
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: production
data:
  DATABASE_URL: "postgres://localhost:5432/mydb"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: production
# ...
```

```bash
# Process multi-document YAML
kubectl apply -f multi-doc.yaml           # kubectl handles multi-doc natively
yq eval 'select(.kind == "Deployment")' multi-doc.yaml   # Filter by document
yq eval-all '. | select(.kind == "ConfigMap")' multi-doc.yaml
```

---

## 4. Common Gotchas

### 4.1 Indentation

```yaml
# YAML uses spaces ONLY — tabs are ILLEGAL
# Consistent indentation (2 spaces recommended)

# Wrong — tab character causes parse error
items:
	- name: broken    # TAB — YAML error!

# Wrong — inconsistent indentation
items:
  - name: one
   value: broken     # 3 spaces instead of 4 — parse error

# Right
items:
  - name: one
    value: correct
```

### 4.2 Trailing Spaces

```yaml
# Trailing spaces after colons can cause issues
key:   value          # Works, but trailing spaces after value can cause problems
key: "value   "       # Explicit — trailing spaces are part of the string

# Trailing spaces on "empty" values
key:                   # null (trailing spaces are invisible but present)
```

### 4.3 Special Characters in Keys

```yaml
# Keys with special characters need quoting
"key with spaces": value
"key:with:colons": value
"key#with#hashes": value
"200": success          # String key, not integer

# Nested keys with dots (some tools interpret dots as nesting)
"app.config.timeout": 30     # Some tools see this as app → config → timeout
```

---

## 5. yamllint Configuration

```yaml
# .yamllint.yaml
extends: default

rules:
  line-length:
    max: 120
    level: warning
  indentation:
    spaces: 2
    indent-sequences: true     # Sequences indented relative to parent
  truthy:
    check-keys: true           # Flag unquoted yes/no/on/off in keys
    allowed-values: ['true', 'false']  # Only allow lowercase true/false
  comments:
    min-spaces-from-content: 1
  document-start: disable      # Don't require --- at start
  empty-lines:
    max: 1
  new-line-at-end-of-file: enable
  trailing-spaces: enable
  brackets:
    min-spaces-inside: 0
    max-spaces-inside: 1
  braces:
    min-spaces-inside: 0
    max-spaces-inside: 1
```

```bash
# Run yamllint
yamllint .
yamllint -d relaxed deployment.yaml     # Use relaxed preset
yamllint -f parsable deployment.yaml    # Machine-readable output (CI)
```

---

## 6. JSON Schema Validation

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["apiVersion", "kind", "metadata", "spec"],
  "properties": {
    "apiVersion": {
      "type": "string",
      "enum": ["apps/v1"]
    },
    "kind": {
      "type": "string",
      "enum": ["Deployment"]
    },
    "metadata": {
      "type": "object",
      "required": ["name"],
      "properties": {
        "name": {
          "type": "string",
          "pattern": "^[a-z][a-z0-9-]*$",
          "maxLength": 63
        }
      }
    }
  }
}
```

```bash
# Validate YAML against JSON Schema
# Tools: ajv-cli, check-jsonschema, kubeconform
pip install check-jsonschema
check-jsonschema --schemafile schema.json deployment.yaml

# Kubernetes-specific validation
kubeconform -strict -summary deployment.yaml
```

---

## 7. YAML vs TOML vs JSON Comparison

```
Feature              YAML           TOML           JSON
──────────────────────────────────────────────────────────
Comments             # yes          # yes          ✗ no
Multiline strings    | and >        """..."""       ✗ no (escape \n)
References/Anchors   & and *        ✗ no           ✗ no
Type coercion        aggressive     minimal        none
Readability          high           high           medium
Complexity           high           low            low
Indentation-based    yes            no             no
Standard             1.1/1.2        1.0            ECMA-404
K8s/Docker/CI use    dominant       rare           common

Recommendation:
  Kubernetes manifests → YAML (industry standard)
  Python packaging     → TOML (pyproject.toml)
  API responses        → JSON (universal)
  Application config   → YAML or TOML (readability)
  Data interchange     → JSON (simplicity, no ambiguity)
```

---

## Cross-Domain Connections

**YAML ↔ Kubernetes:** Every K8s manifest is YAML. The Norway problem can break boolean fields in K8s configs. Always quote ambiguous values.

**YAML ↔ CI/CD:** GitHub Actions, GitLab CI, CircleCI, and Argo Workflows all use YAML. Incorrect indentation is the #1 cause of CI pipeline failures.

**YAML ↔ Helm:** Helm values.yaml files have their own gotchas — `null` values, nested keys, and the interaction between values and Go templates.

---

## Self-Review Checklist

- [ ] All boolean values use lowercase `true`/`false` (not yes/no/on/off)
- [ ] All strings that could be misinterpreted are quoted (country codes, versions, zip codes)
- [ ] Dates are quoted if they should be strings (`"2024-01-15"`)
- [ ] Version numbers are quoted (`"1.0"` not `1.0`)
- [ ] Indentation uses spaces only (no tabs)
- [ ] yamllint configured and passes in CI
- [ ] Multiline strings use correct block scalar (| for literal, > for folded)
- [ ] Anchors/aliases used for DRY (but not overused for readability)
- [ ] JSON Schema validation for critical config files
- [ ] Trailing spaces removed
- [ ] Comments explain non-obvious configuration choices
- [ ] Multi-document files use `---` separators correctly
