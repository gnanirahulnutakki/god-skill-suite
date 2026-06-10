---
name: god-shell-scripting
description: "God-level shell scripting mastery. Deep dive into bash and zsh scripting, POSIX compatibility, strict mode (set -euo pipefail), variable quoting and expansion, arrays and associative arrays, process substitution, here-documents, trap and signal handling, argument parsing (getopts, manual parsing), text processing (awk, sed, jq, yq), regular expressions, ShellCheck linting, portable scripting patterns, performance optimization, and production-grade script architecture. Never fabricate bash built-in names or POSIX features — verify against the Bash Reference Manual."
metadata:
  author: god-dev-suite
  version: '1.0'
---

# God-Level Shell Scripting

## Anti-Hallucination Rules

- NEVER invent bash built-in commands — `declare`, `local`, `readonly`, `export`, `getopts`, `mapfile`/`readarray`, `printf`, `read`, `trap`, `wait`, `shift` are real. Verify others.
- NEVER claim a feature is POSIX-compatible without checking — `[[ ]]`, arrays, `local`, `declare` are bash-only.
- NEVER write scripts without `set -euo pipefail` unless there's a specific documented reason.
- ALWAYS quote variable expansions (`"${var}"`) — unquoted variables are a bug.
- ALWAYS use ShellCheck (SC codes) as the authority for best practices.

---

## 1. Script Architecture

### 1.1 Production Script Template

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# ─── Constants ──────────────────────────────────────
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly VERSION="1.0.0"

# ─── Default Configuration ─────────────────────────
readonly LOG_LEVEL="${LOG_LEVEL:-info}"
readonly DRY_RUN="${DRY_RUN:-false}"

# ─── Color Output ───────────────────────────────────
if [[ -t 1 ]]; then
    readonly RED='\033[0;31m'
    readonly GREEN='\033[0;32m'
    readonly YELLOW='\033[0;33m'
    readonly BLUE='\033[0;34m'
    readonly NC='\033[0m'
else
    readonly RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

# ─── Logging ────────────────────────────────────────
log_info()  { printf "${GREEN}[INFO]${NC}  %s\n" "$*" >&2; }
log_warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*" >&2; }
log_error() { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; }
log_debug() { [[ "${LOG_LEVEL}" == "debug" ]] && printf "${BLUE}[DEBUG]${NC} %s\n" "$*" >&2; }

# ─── Cleanup ────────────────────────────────────────
readonly TMPDIR_WORK="$(mktemp -d)"
cleanup() {
    local exit_code=$?
    rm -rf "${TMPDIR_WORK}"
    if [[ ${exit_code} -ne 0 ]]; then
        log_error "Script failed with exit code ${exit_code}"
    fi
    exit "${exit_code}"
}
trap cleanup EXIT
trap 'log_error "Interrupted"; exit 130' INT TERM

# ─── Usage ──────────────────────────────────────────
usage() {
    cat <<EOF
Usage: ${SCRIPT_NAME} [OPTIONS] <command>

Options:
    -h, --help          Show this help
    -v, --verbose       Enable debug logging
    -n, --dry-run       Preview changes without applying
    -o, --output FILE   Output file (default: stdout)

Commands:
    deploy              Deploy the application
    rollback            Rollback to previous version
    status              Check deployment status

Environment Variables:
    LOG_LEVEL           Log level (debug|info|warn|error) [default: info]
    DRY_RUN             Enable dry-run mode (true|false) [default: false]

Examples:
    ${SCRIPT_NAME} deploy --verbose
    ${SCRIPT_NAME} rollback -o report.txt
    DRY_RUN=true ${SCRIPT_NAME} deploy
EOF
}

# ─── Argument Parsing ───────────────────────────────
parse_args() {
    local output_file=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)    usage; exit 0 ;;
            -v|--verbose) LOG_LEVEL="debug" ;;
            -n|--dry-run) DRY_RUN="true" ;;
            -o|--output)
                [[ $# -lt 2 ]] && { log_error "--output requires a value"; exit 1; }
                output_file="$2"; shift ;;
            --)           shift; break ;;
            -*)           log_error "Unknown option: $1"; usage; exit 1 ;;
            *)            break ;;
        esac
        shift
    done

    readonly COMMAND="${1:-}"
    readonly OUTPUT_FILE="${output_file}"

    if [[ -z "${COMMAND}" ]]; then
        log_error "No command specified"
        usage
        exit 1
    fi
}

# ─── Main Logic ─────────────────────────────────────
cmd_deploy() {
    log_info "Deploying..."
    if [[ "${DRY_RUN}" == "true" ]]; then
        log_warn "DRY RUN — no changes applied"
        return 0
    fi
    # Actual deployment logic here
}

cmd_rollback() {
    log_info "Rolling back..."
}

cmd_status() {
    log_info "Checking status..."
}

main() {
    parse_args "$@"
    case "${COMMAND}" in
        deploy)   cmd_deploy ;;
        rollback) cmd_rollback ;;
        status)   cmd_status ;;
        *)        log_error "Unknown command: ${COMMAND}"; usage; exit 1 ;;
    esac
}

main "$@"
```

---

## 2. Text Processing

### 2.1 awk

```bash
# Print specific columns
awk '{print $1, $3}' file.txt

# Filter by condition
awk '$3 > 100 {print $1, $3}' data.csv

# Sum a column
awk '{sum += $3} END {print "Total:", sum}' data.csv

# Field separator
awk -F',' '{print $1, $2}' data.csv

# Pattern matching
awk '/ERROR/ {count++} END {print count, "errors"}' app.log

# Multi-rule processing
awk '
    BEGIN { FS=","; OFS="\t" }
    NR == 1 { next }                    # Skip header
    $4 > 500 { slow++; print $1, $4 }   # Slow requests
    END { printf "Slow requests: %d\n", slow }
' access.log
```

### 2.2 sed

```bash
# In-place replacement (GNU sed)
sed -i 's/old/new/g' file.txt

# macOS sed requires backup extension
sed -i '' 's/old/new/g' file.txt

# Delete lines matching pattern
sed '/^#/d' config.txt              # Delete comments
sed '/^$/d' config.txt              # Delete blank lines

# Insert line before/after match
sed '/\[database\]/a\host = localhost' config.ini
sed '/\[database\]/i\# Database section' config.ini

# Address ranges
sed '10,20s/foo/bar/g' file.txt     # Replace only on lines 10-20
sed '/START/,/END/d' file.txt       # Delete between patterns
```

### 2.3 jq

```bash
# Parse JSON
echo '{"name": "Alice", "age": 30}' | jq '.name'
# Output: "Alice"

# Array operations
echo '[1,2,3,4,5]' | jq 'map(. * 2)'
# Output: [2,4,6,8,10]

# Filter and transform
cat data.json | jq '.users[] | select(.active == true) | {name, email}'

# Construct new JSON
cat pods.json | jq '[.items[] | {
    name: .metadata.name,
    namespace: .metadata.namespace,
    status: .status.phase,
    restarts: (.status.containerStatuses[0].restartCount // 0)
}]'

# Slurp multiple JSON objects into array
cat *.json | jq -s '.'

# Raw output (no quotes)
jq -r '.name' data.json

# kubectl + jq
kubectl get pods -o json | jq -r '.items[] | select(.status.phase != "Running") | .metadata.name'
```

### 2.4 yq

```bash
# Parse YAML (mikefarah/yq v4)
yq '.metadata.name' deployment.yaml

# Update YAML in place
yq -i '.spec.replicas = 5' deployment.yaml

# Convert YAML to JSON
yq -o=json deployment.yaml

# Merge YAML files
yq eval-all '. as $item ireduce ({}; . * $item)' base.yaml overlay.yaml

# Select from array
yq '.spec.containers[] | select(.name == "app") | .image' pod.yaml
```

---

## 3. Arrays and Associative Arrays

```bash
# Indexed arrays
declare -a fruits=("apple" "banana" "cherry")
fruits+=("date")                          # Append
echo "${fruits[0]}"                       # First element
echo "${fruits[@]}"                       # All elements
echo "${#fruits[@]}"                      # Length
unset 'fruits[1]'                         # Remove element

# Iterate
for fruit in "${fruits[@]}"; do
    echo "Processing: ${fruit}"
done

# Associative arrays (bash 4+)
declare -A config
config[host]="localhost"
config[port]="5432"
config[database]="mydb"

for key in "${!config[@]}"; do
    echo "${key}=${config[${key}]}"
done

# Read file into array
mapfile -t lines < file.txt              # bash 4+
readarray -t lines < file.txt           # Same as mapfile
```

---

## 4. Process Substitution and Pipes

```bash
# Process substitution — treat command output as a file
diff <(sort file1.txt) <(sort file2.txt)
comm -13 <(sort list1.txt) <(sort list2.txt)    # Lines in list2 not in list1

# Named pipes (FIFOs)
mkfifo /tmp/mypipe
producer_command > /tmp/mypipe &
consumer_command < /tmp/mypipe

# Here-string
grep "pattern" <<< "${variable}"

# Here-document with variable expansion disabled
cat <<'EOF'
This $variable is NOT expanded
$(this command is NOT executed)
EOF

# Coprocess
coproc DB_CONN { psql -U postgres mydb; }
echo "SELECT count(*) FROM users;" >&"${DB_CONN[1]}"
read -r count <&"${DB_CONN[0]}"
```

---

## 5. Error Handling Patterns

```bash
# Retry with exponential backoff
retry() {
    local -i max_attempts="${1}"
    local -i delay="${2}"
    shift 2
    local -i attempt=1

    until "$@"; do
        if (( attempt >= max_attempts )); then
            log_error "Command failed after ${max_attempts} attempts: $*"
            return 1
        fi
        log_warn "Attempt ${attempt}/${max_attempts} failed, retrying in ${delay}s..."
        sleep "${delay}"
        (( delay *= 2 ))
        (( attempt++ ))
    done
}

retry 5 2 curl -sf "https://api.example.com/health"

# Check command exists
require_command() {
    local cmd="$1"
    if ! command -v "${cmd}" &>/dev/null; then
        log_error "Required command not found: ${cmd}"
        exit 1
    fi
}

require_command kubectl
require_command jq
require_command helm
```

---

## 6. ShellCheck Integration

```bash
# Run ShellCheck
shellcheck script.sh
shellcheck -S warning script.sh          # Only warnings and above
shellcheck -f json script.sh             # JSON output for CI
shellcheck -x script.sh                  # Follow source'd files

# Common ShellCheck warnings:
# SC2086: Double quote to prevent globbing/splitting
# SC2046: Quote command substitution
# SC2034: Variable appears unused (false positive for exported vars)
# SC2155: Declare and assign separately
# SC2164: Use cd ... || exit

# Inline directives
# shellcheck disable=SC2034    # Suppress specific warning
readonly UNUSED_BUT_EXPORTED="${MY_VAR}"
```

---

## Cross-Domain Connections

**Shell ↔ CI/CD:** Every CI pipeline step runs shell commands. Strict mode, proper quoting, and retry patterns prevent intermittent failures.

**Shell ↔ Kubernetes:** `kubectl` output piped through `jq`/`yq` is the bread and butter of K8s scripting. Use `-o json` for machine parsing, never parse `kubectl get` text output.

**Shell ↔ Docker:** Entrypoint scripts, health checks, init scripts — all shell. Use `exec` to replace shell process with the application (PID 1 signal handling).

---

## Self-Review Checklist

- [ ] Script starts with `#!/usr/bin/env bash` and `set -euo pipefail`
- [ ] All variable expansions are quoted (`"${var}"`)
- [ ] `readonly` used for constants
- [ ] `local` used for function variables
- [ ] `trap cleanup EXIT` handles resource cleanup
- [ ] `mktemp` used for temp files (never hardcoded paths)
- [ ] ShellCheck passes with zero warnings
- [ ] Command existence checked before use (`command -v`)
- [ ] Error messages go to stderr (`>&2`)
- [ ] Exit codes are meaningful (0=success, 1=error, 130=interrupted)
- [ ] Here-docs use `<<'EOF'` (quoted) to prevent unexpected expansion
- [ ] Arrays iterated with `"${array[@]}"` (quoted, expanded individually)
