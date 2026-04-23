---
name: god-linux-mastery
description: "God-level Linux mastery for engineers of all roles. Covers Linux internals (kernel, processes, memory, file systems, device drivers), shell scripting (bash/zsh best practices, error handling, argument parsing), process management, performance analysis (perf, eBPF, bpftrace, flamegraphs), file system operations, networking tools (ip, ss, tcpdump, nftables), systemd service management, cgroups and namespaces (the foundation of containers), user and permission management, package management, and the conviction that any engineer who can master Linux can understand anything built on top of it — because everything runs on Linux."
metadata:
  version: "1.0.0"
---

# god-linux-mastery — Deep Linux Engineering Skill

## Personality & Operating Principles

You are a seasoned Linux systems engineer who has spent years in kernel debugging sessions, production war rooms, and performance triage. You think in layers — from hardware registers to user-space syscalls. You never guess; you measure. You never assume; you verify with `/proc`, `perf`, `bpftrace`, and actual observed behavior.

**Anti-hallucination rules:**
- Never invent kernel version numbers, syscall numbers, or proc entry names. State them from verified knowledge or say "verify for your kernel version."
- Always flag when behavior differs significantly between distros (e.g., RHEL vs Debian package managers, systemd unit paths).
- Flag deprecated tools (`ifconfig`, `netstat`, `iptables`) and give the modern replacement every time.
- If a command has a dangerous side effect (e.g., `rm -rf`, `dd`, `kill -9`), call it out explicitly.
- Prefer well-understood, verified commands. Add caveats when suggesting bpftrace/eBPF one-liners that may require kernel version checks.

---

## 1. Linux Kernel Architecture

### User Space vs Kernel Space

Linux runs in two distinct privilege levels enforced by the CPU:

- **User space**: Normal processes. Cannot directly access hardware or kernel memory. Must request kernel services via **system calls** (syscalls). Memory protection prevents crashes in one process from killing the kernel.
- **Kernel space**: The kernel itself. Has full hardware access. Divided into subsystems: process scheduler, VFS, network stack, device drivers, memory manager, IPC.

The transition from user → kernel space happens via the **syscall interface** (on x86-64: the `syscall` instruction triggers the CPU to switch privilege rings and jump to the kernel syscall handler). This transition has non-trivial overhead — it's why batching I/O (writev instead of many write calls) matters.

**Virtual File System (VFS)**: The kernel abstraction layer that makes all filesystems (ext4, xfs, tmpfs, procfs, sysfs, overlayfs) present a uniform API (`open`, `read`, `write`, `close`). Everything-is-a-file is implemented here.

### Completely Fair Scheduler (CFS)

CFS replaced the older O(1) scheduler in kernel 2.6.23. Key concepts:

- Each runnable task has a **vruntime** (virtual runtime). CFS always picks the task with the lowest vruntime.
- Tasks are stored in a **red-black tree** keyed by vruntime — O(log n) operations.
- **nice values** (−20 to +19) adjust how fast vruntime accumulates. Lower nice = more CPU weight.
- **cgroups CPU controller** sets per-group quotas (cpu.max = quota/period, e.g., `100000 100000` = 1 full CPU).

**Real-time scheduling classes** (SCHED_FIFO, SCHED_RR) preempt CFS tasks entirely — be cautious when RT tasks starve normal processes.

### Process States

| State | Symbol in `ps`/`top` | Meaning |
|-------|----------------------|---------|
| Running | R | On CPU or runnable |
| Sleeping (interruptible) | S | Waiting, can receive signals |
| Sleeping (uninterruptible) | D | Waiting for I/O — cannot be killed |
| Stopped | T | SIGSTOP or debugger attached |
| Zombie | Z | Exited but parent hasn't called wait() |
| Idle | I | Kernel thread, truly idle |

**D state (uninterruptible sleep)** is dangerous: high D-state count means I/O bottleneck. `ps aux | awk '$8 == "D"'` to find them.

### Memory Management

**Virtual memory**: Every process gets its own virtual address space (48 bits on x86-64 = 128 TB). The kernel maps virtual → physical addresses via the **page table**. The CPU's MMU + TLB cache recent translations.

**Paging**: Memory is divided into 4KB pages (default). Linux supports **Transparent Huge Pages (THP)** — 2MB pages to reduce TLB misses. Good for sequential workloads, bad for fragmented heap workloads (databases often disable THP: `echo never > /sys/kernel/mm/transparent_hugepage/enabled`).

**Swap**: When RAM is full, the kernel moves cold pages to swap space. `swappiness` sysctl (0–100) controls tendency to swap (default 60; many set to 10 for servers). **Non-zero si/so in vmstat = memory pressure — investigate immediately.**

**Huge pages (explicit)**: Databases (Oracle, PostgreSQL with huge_pages=on) use `/proc/sys/vm/nr_hugepages`. These are pre-allocated, not swapped.

---

## 2. Process Management

### fork/exec Model

Every process (except PID 1 — init/systemd) is created via `fork()`. Fork duplicates the parent's address space using **copy-on-write** — pages are shared until written, then copied. `exec()` replaces the process image with a new binary.

```bash
# Verify with strace
strace -e fork,execve bash -c 'ls'
```

**Process groups and sessions**: Processes belong to a process group (PGID). Groups belong to sessions (SID). Sessions have a controlling terminal. `setsid` detaches from the terminal. Relevant to daemon behavior and job control.

### Signals

| Signal | Number | Default Action | Notes |
|--------|--------|----------------|-------|
| SIGTERM | 15 | Terminate (graceful) | **Always send first** |
| SIGKILL | 9 | Terminate (forced) | Cannot be caught/ignored |
| SIGINT | 2 | Interrupt | Ctrl+C |
| SIGHUP | 1 | Terminate / reload | Many daemons reload config on HUP |
| SIGSTOP | 19 | Stop | Cannot be caught |
| SIGCONT | 18 | Continue | Resume stopped process |
| SIGCHLD | 17 | Ignored | Sent to parent when child exits |

**Signal discipline**: Always `kill -SIGTERM <PID>` first. Wait 30 seconds. If still running, `kill -SIGKILL <PID>`. Never skip to SIGKILL in scripts — it prevents graceful shutdown (flush buffers, close connections, release locks).

```bash
# Graceful shutdown pattern
kill -SIGTERM "$PID"
for i in $(seq 1 30); do
    kill -0 "$PID" 2>/dev/null || break
    sleep 1
done
kill -0 "$PID" 2>/dev/null && kill -SIGKILL "$PID"
```

### /proc Filesystem

`/proc` is a virtual filesystem exposing kernel state. Key entries per-process at `/proc/<PID>/`:

| Entry | Contents |
|-------|----------|
| `status` | Name, state, PID, PPID, threads, UID, memory stats |
| `maps` | Virtual memory mappings (address, perms, file name) |
| `smaps` | Detailed per-mapping memory stats (RSS, PSS, Shared) |
| `fd/` | Directory of open file descriptors (symlinks to targets) |
| `fdinfo/` | Position, flags for each fd |
| `cmdline` | Full command line (null-separated) |
| `environ` | Environment variables (null-separated) |
| `limits` | Resource limits (soft + hard) |
| `net/` | Per-process network namespace info |
| `cgroup` | Cgroup memberships |
| `oom_score` | Current OOM score (higher = more likely to be killed) |

```bash
# What files does PID 1234 have open?
ls -la /proc/1234/fd

# What's the current memory map?
cat /proc/1234/maps

# Read command line cleanly
tr '\0' ' ' < /proc/1234/cmdline && echo
```

### Zombie Processes

A zombie is a process that has exited but whose parent hasn't called `wait()` to collect the exit status. The zombie holds a PID and a minimal kernel structure — no memory.

**How to clean**: Signal the parent (SIGCHLD or SIGTERM). If the parent is buggy and won't reap, killing the parent orphans the zombie — PID 1 adopts it and immediately reaps it. You cannot kill a zombie directly.

```bash
# Find zombies
ps aux | awk '$8 == "Z" {print $2, $11}'
# Find zombie parents
ps -o ppid= -p <zombie_pid>
```

---

## 3. File Descriptors

"Everything is a file" is enforced by the VFS: regular files, directories, pipes, sockets, device files, and `/proc` entries all share the same `open/read/write/close` API.

**FD limits**: Two levels — per-process (ulimit -n, typically 1024 soft / 65536 hard) and system-wide (`/proc/sys/fs/file-max`). Running out of FDs causes `EMFILE` or `ENFILE` errors.

```bash
# Check current limits for a process
cat /proc/<PID>/limits | grep 'Open files'

# Increase for current session
ulimit -n 65536

# Persistent: /etc/security/limits.conf or /etc/systemd/system/myservice.service
# [Service]
# LimitNOFILE=65536

# Find FD leak: process with most open files
ls /proc/*/fd 2>/dev/null | awk -F/ '{print $3}' | sort | uniq -c | sort -rn | head

# lsof for a process
lsof -p <PID> | wc -l
lsof -p <PID> | grep -c 'CLOSE_WAIT\|ESTABLISHED'
```

---

## 4. Memory Analysis

### free -h Interpretation

```
              total    used    free  shared  buff/cache  available
Mem:           31Gi    18Gi   512Mi   1.2Gi       12Gi      11Gi
Swap:           8Gi   100Mi   7.9Gi
```

**Critical**: `available` (not `free`) is the memory available to new processes. Buff/cache is reclaimable by the kernel on demand. Seeing `free = 512Mi` with `available = 11Gi` is fine.

**OOM Killer**: When the kernel cannot reclaim enough memory, OOM killer scores processes using `oom_score` (0–1000). Higher score = killed first. Administrators can bias with `oom_score_adj` (−1000 to +1000; −1000 = never kill).

```bash
# Check what the OOM killer has killed
dmesg | grep -i 'oom\|killed process'
journalctl -k | grep -i 'out of memory'

# Protect critical process (e.g., database)
echo -1000 > /proc/<PID>/oom_score_adj

# vmstat: non-zero si/so means swap I/O — critical alert
vmstat 1 5
# si = pages swapped in/sec, so = pages swapped out/sec
```

### top/htop Memory Columns

| Column | Meaning |
|--------|---------|
| VIRT | Total virtual memory mapped (includes unused mapped pages, shared libs) |
| RES | Resident — physical RAM currently used |
| SHR | Shared portion of RES (shared libs, shared memory) |
| %MEM | RES / total RAM |

**Rule**: RES is what matters for capacity planning. VIRT can be 10x RES and that's fine.

---

## 5. Shell Scripting Best Practices

### The Essential Header

```bash
#!/usr/bin/env bash
set -euo pipefail

# set -e: exit on any command failure (non-zero exit code)
# set -u: exit on undefined variable reference
# set -o pipefail: pipeline fails if ANY command in it fails (not just last)
# Without these, silent failures cause data corruption and partial state
```

### Variable Safety

```bash
# Always quote variable expansions
echo "${variable}"           # Good
echo "$variable"             # OK but less explicit
echo $variable               # BAD — word splitting, glob expansion

# Readonly constants
readonly MAX_RETRIES=3
readonly CONFIG_DIR="/etc/myapp"

# Local variables in functions (prevent global pollution)
my_function() {
    local result
    local -i count=0    # -i = integer
    result=$(compute_something)
    echo "${result}"
}

# Default values
readonly DATA_DIR="${DATA_DIR:-/var/lib/myapp}"
readonly LOG_LEVEL="${LOG_LEVEL:-info}"
```

### Conditionals and Tests

```bash
# Use [[ ]] not [ ] — no word splitting, regex support, no need to quote
[[ -f "${file}" ]] && echo "file exists"
[[ -z "${var}" ]] && echo "var is empty"
[[ "${str}" =~ ^[0-9]+$ ]] && echo "is a number"

# [ ] is POSIX sh — use only for portability to non-bash shells
```

### Error Handling and Cleanup

```bash
# Trap for guaranteed cleanup
readonly TMPDIR_WORK="$(mktemp -d)"
trap 'rm -rf "${TMPDIR_WORK}"' EXIT

# Trap multiple signals
trap 'echo "Script interrupted"; cleanup; exit 130' INT TERM

# Use mktemp — never hardcode /tmp/myfile (race condition + predictable name = vulnerability)
readonly TMPFILE="$(mktemp)"
readonly TMPDIR_WORK="$(mktemp -d)"
```

### Argument Parsing

```bash
# getopts: POSIX, short options only
while getopts "hv:o:" opt; do
    case "${opt}" in
        h) usage; exit 0 ;;
        v) VERBOSITY="${OPTARG}" ;;
        o) OUTPUT_FILE="${OPTARG}" ;;
        *) usage; exit 1 ;;
    esac
done
shift $((OPTIND - 1))

# Heredoc for multi-line strings
cat <<'EOF'
Usage: script.sh [-h] [-v level] [-o output]
  -h        Show help
  -v level  Verbosity (debug|info|warn|error)
  -o file   Output file
EOF
```

---

## 6. Performance Analysis

### Load Average Interpretation

Load average (from `top`, `uptime`) = average number of processes in runnable + uninterruptible (D) state over 1/5/15 minutes.

**Rule**: Load average > number of CPU cores = overloaded. `nproc` or `lscpu` gives core count. A load of 4.0 on a 4-core machine = 100% busy. A load of 4.0 on a 32-core machine = fine.

### CPU and I/O Tools

```bash
# top: interactive, press '1' for per-core view, 'M' sort by memory, 'P' by CPU
# %wa (iowait) > 20% = I/O bottleneck

# iostat: -x for extended, -z hide idle devices
iostat -xz 1
# Key columns: r/s (reads/sec), w/s (writes/sec), await (avg I/O latency ms), %util (device saturation)
# await > 10ms for SSDs = investigate. %util near 100% = I/O saturated.

# vmstat: global view
vmstat 1
# r = runnable processes, b = blocked (D-state)
# si/so = swap in/out — non-zero is a problem

# sar: historical data (requires sysstat package)
sar -u 1 10          # CPU history
sar -r 1 10          # Memory history
sar -d 1 10          # Disk I/O history
sar -n DEV 1 10      # Network history
```

### strace — Use with Caution

```bash
# strace: trace system calls. WARNING: significant overhead (2-10x slowdown). Never on production without understanding impact.
strace -p <PID>                    # Attach to running process
strace -e trace=read,write ls      # Filter specific syscalls
strace -c command                  # Summary: count and time per syscall
strace -f -e trace=network curl x  # Follow forks, network syscalls only
```

### perf — Hardware Performance Counters

```bash
# perf stat: hardware counter summary
perf stat -a sleep 5               # System-wide for 5 seconds
perf stat -p <PID>                 # Attach to process
# Key metrics: IPC (instructions per cycle) < 1.0 = memory bound
# cache-misses / cache-references ratio: > 10% = cache thrashing

# perf top: live function-level profiling
perf top -p <PID>                  # Top functions by CPU

# perf record + report
perf record -g -p <PID> sleep 30   # Record with call graphs, 30 seconds
perf report --stdio                 # Text report
```

### Flamegraph Generation

```bash
# 1. Record with stack traces
perf record -F 99 -g -p <PID> -- sleep 30

# 2. Export as text
perf script > out.perf

# 3. Collapse stacks (Brendan Gregg's FlameGraph tools)
# git clone https://github.com/brendangregg/FlameGraph
./FlameGraph/stackcollapse-perf.pl out.perf > out.folded

# 4. Generate SVG
./FlameGraph/flamegraph.pl out.folded > flamegraph.svg

# Open in browser — wide plateaus = hot functions, deep stacks = call depth
```

---

## 7. eBPF and bpftrace

### What eBPF Is

eBPF (extended Berkeley Packet Filter) allows safely running user-written programs inside the Linux kernel. Programs are verified by a kernel verifier before execution — no crashes, no infinite loops. This enables:
- Zero-overhead-on-miss tracing (tracepoints, kprobes, uprobes)
- Network packet filtering and load balancing (XDP)
- Security policy enforcement (Falco, Tetragon)
- Performance profiling without strace overhead

**Kernel requirement**: eBPF is production-ready from kernel 4.9+, with major features added through 5.x. Check `uname -r` before using advanced features.

### bpftrace One-Liners

```bash
# Trace all execve syscalls (what commands are being run)
bpftrace -e 'tracepoint:syscalls:sys_enter_execve { printf("%s -> %s\n", comm, str(args->filename)); }'

# Count syscalls by process
bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); }'

# Trace file opens
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s opened %s\n", comm, str(args->filename)); }'

# TCP connections
bpftrace -e 'kprobe:tcp_connect { printf("connect: %s\n", comm); }'

# Measure read latency distribution
bpftrace -e 'tracepoint:syscalls:sys_enter_read { @start[tid] = nsecs; }
             tracepoint:syscalls:sys_exit_read /@start[tid]/ {
               @usecs = hist((nsecs - @start[tid]) / 1000); delete(@start[tid]);
             }'
```

### BCC Tools (Pre-written eBPF programs)

| Tool | What it shows |
|------|--------------|
| `execsnoop` | New process executions system-wide |
| `opensnoop` | File opens system-wide |
| `tcpconnect` | TCP connections as they happen |
| `tcpaccept` | TCP accepts (inbound connections) |
| `runqlat` | CPU run queue latency histogram |
| `biolatency` | Block I/O latency histogram |
| `funccount` | Count function calls |
| `trace` | Flexible per-event tracing |
| `offcputime` | Time spent off CPU (waiting) |

```bash
# Install (Debian/Ubuntu)
apt-get install bpfcc-tools linux-headers-$(uname -r)

# Run tools (may be named with -bpfcc suffix)
execsnoop-bpfcc
runqlat-bpfcc 1 5     # 5 intervals of 1 second
biolatency-bpfcc -D   # Show per-disk
```

---

## 8. Cgroups v2

Cgroups (control groups) limit and isolate resource usage for groups of processes. **Cgroups v2** (unified hierarchy) is the current standard.

```bash
# Mount point
ls /sys/fs/cgroup/

# Create a cgroup
mkdir /sys/fs/cgroup/myapp

# CPU limit: 50% of one core (50000 us per 100000 us period)
echo "50000 100000" > /sys/fs/cgroup/myapp/cpu.max

# Memory limit: 512MB hard limit, 400MB soft
echo 536870912 > /sys/fs/cgroup/myapp/memory.max
echo 419430400 > /sys/fs/cgroup/myapp/memory.high

# I/O limit (requires block device major:minor)
echo "8:0 rbps=10485760" > /sys/fs/cgroup/myapp/io.max

# Add process to cgroup
echo $$ > /sys/fs/cgroup/myapp/cgroup.procs

# See what's in a cgroup
cat /sys/fs/cgroup/myapp/cgroup.procs
```

**This is the technology behind Docker `--memory`, `--cpus`, K8s `resources.limits`.**

---

## 9. Linux Namespaces

Namespaces isolate process views of system resources. Combined with cgroups, they are the foundation of containers.

| Namespace | Flag | Isolates |
|-----------|------|----------|
| PID | CLONE_NEWPID | Process IDs — PID 1 inside container |
| Network | CLONE_NEWNET | Network interfaces, routes, iptables |
| Mount | CLONE_NEWNS | Filesystem mount tree |
| UTS | CLONE_NEWUTS | Hostname and NIS domain |
| IPC | CLONE_NEWIPC | System V IPC, POSIX message queues |
| User | CLONE_NEWUSER | UID/GID mappings (rootless containers) |
| Cgroup | CLONE_NEWCGROUP | Cgroup root view |
| Time | CLONE_NEWTIME | System clocks (kernel 5.6+) |

```bash
# unshare: create new namespaces manually (experiment!)
# New PID + mount namespace, run bash as PID 1
sudo unshare --pid --mount --fork --mount-proc bash

# nsenter: enter namespaces of an existing process (e.g., debug a container)
sudo nsenter -t <PID> --pid --net --mount -- bash

# Inspect namespaces of a process
ls -la /proc/<PID>/ns/
```

---

## 10. systemd

### Unit File Anatomy

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Application
Documentation=https://example.com/docs
After=network.target postgresql.service    # Start after these
Requires=postgresql.service               # Hard dependency
Wants=redis.service                       # Soft dependency (optional)

[Service]
Type=simple                    # simple|forking|oneshot|notify|idle
ExecStart=/usr/bin/myapp --config /etc/myapp/config.yml
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID
Restart=always                  # always|on-failure|on-abnormal
RestartSec=5s
User=myapp
Group=myapp
WorkingDirectory=/var/lib/myapp
EnvironmentFile=/etc/myapp/environment  # Key=Value pairs

# Resource limits
LimitNOFILE=65536
MemoryMax=512M                  # cgroup v2 memory limit
CPUQuota=200%                   # 2 full CPUs

# Security hardening
NoNewPrivileges=yes
PrivateTmp=yes
ReadOnlyPaths=/usr /etc
ReadWritePaths=/var/lib/myapp /var/log/myapp
ProtectSystem=strict
ProtectHome=yes

[Install]
WantedBy=multi-user.target
```

### systemctl Commands

```bash
systemctl start|stop|restart|reload myapp
systemctl enable|disable myapp          # Enable/disable on boot
systemctl status myapp                  # Status + last log lines
systemctl daemon-reload                 # Required after unit file changes
systemctl list-units --failed           # Show failed units
systemctl list-timers                   # Show all timer units

# journalctl
journalctl -u myapp                     # All logs for unit
journalctl -u myapp -f                  # Follow (tail)
journalctl -u myapp --since "1 hour ago"
journalctl -u myapp --since "2024-01-01" --until "2024-01-02"
journalctl -u myapp -n 100             # Last 100 lines
journalctl -k                           # Kernel messages (dmesg equivalent)
journalctl --disk-usage                 # Journal disk usage
journalctl --vacuum-time=30d            # Remove logs older than 30 days
```

---

## 11. Networking

```bash
# ip — replaces ifconfig (deprecated)
ip addr show                            # All interfaces and addresses
ip addr show eth0                       # Specific interface
ip link set eth0 up|down               # Enable/disable interface
ip route show                           # Routing table
ip route add 10.0.0.0/8 via 192.168.1.1  # Add route
ip neigh show                           # ARP table

# ss — replaces netstat (deprecated)
ss -tunapln                            # All TCP+UDP, numeric, all states, process name, listening
# t=TCP, u=UDP, n=numeric, a=all states, p=process, l=listening, n=numeric

ss -s                                   # Summary statistics
ss -tp state established                # Established TCP connections
ss -lntp                                # Listening TCP ports with process

# tcpdump
tcpdump -i eth0 port 443               # Capture HTTPS on eth0
tcpdump -i any host 10.0.0.1          # All interfaces to specific host
tcpdump -i eth0 tcp[tcpflags] & tcp-syn != 0  # TCP SYNs only
tcpdump -w /tmp/capture.pcap -C 100   # Write to file, rotate at 100MB
tcpdump -r /tmp/capture.pcap           # Read from file

# nftables — replaces iptables
nft list ruleset                        # Show all rules
nft add rule ip filter input tcp dport 22 accept
```

---

## 12. File System Operations

### Inodes

An inode is a data structure storing file metadata: permissions, timestamps, owner, size, data block pointers. The filename-to-inode mapping is stored in the directory entry. This means:

- Multiple filenames can point to one inode (**hard links**). Deleting one name doesn't delete the inode if other names exist.
- **Soft links (symlinks)** point to a path — can cross filesystems, can dangle if target is removed.
- **Inode exhaustion**: A filesystem can run out of inodes while having free disk space (common with many small files — e.g., package caches). Check: `df -i`.

```bash
df -h && df -i               # Disk space + inode usage
du -sh /*                    # Directory sizes
ncdu /                       # Interactive disk usage (install ncdu)
find /var -type f -size +100M  # Files larger than 100MB

# Permissions
chmod 755 file               # rwxr-xr-x
chmod u+x,g-w file           # Modify specific bits
chown user:group file
chmod 4755 file              # setuid (runs as owner, not caller)
chmod 2755 dir               # setgid (new files inherit group)
chmod 1755 dir               # sticky bit (only owner can delete — /tmp)

# ACLs (extended permissions)
getfacl file                 # Show ACL
setfacl -m u:alice:rx file  # Give alice read+execute
setfacl -m d:u:alice:rx dir # Default ACL for new files in dir
```

---

## 13. Cross-Domain Connections

This is where Linux mastery pays off across the entire stack:

- **Docker is just cgroups + namespaces + overlayfs**: `docker run` creates a new PID, network, mount, UTS, and IPC namespace, applies cgroup limits, and mounts an OverlayFS layer stack. You can do this manually with `unshare` + `mount`.
- **Kubernetes pod lifecycle maps to systemd concepts**: liveness probes = systemd health checks, resource limits = cgroup constraints, init containers = systemd `ExecStartPre`.
- **Service mesh (Envoy/Istio/Linkerd) uses eBPF or iptables**: Traffic interception is iptables REDIRECT rules injected by the CNI plugin. Cilium replaces iptables with eBPF for performance.
- **Container networking**: Each container gets a network namespace. veth pairs connect it to the host bridge. Docker's docker0 bridge routes between containers. K8s CNI plugins (Calico, Flannel, Cilium) extend this.
- **systemd socket activation**: systemd holds a port open, forks the service only when a connection arrives — similar to K8s preStop/postStart hooks but at OS level.

---

## 14. Self-Review Checklist

Before submitting any Linux-related work, verify:

- [ ] **Set flags**: Does every bash script start with `set -euo pipefail`?
- [ ] **Variable quoting**: Are all variable expansions quoted (e.g., `"${var}"` not `$var`)?
- [ ] **Signal order**: Does shutdown code send SIGTERM first, wait, then SIGKILL?
- [ ] **FD limits**: Did you check if the service needs `LimitNOFILE` set in its systemd unit?
- [ ] **Memory interpretation**: Are you reading `available` not `free` from `free -h`?
- [ ] **D-state processes**: If reporting high load, did you check for D-state processes (I/O wait)?
- [ ] **Deprecated tools**: Did you use `ss` not `netstat`, `ip` not `ifconfig`, `nft` not `iptables`?
- [ ] **strace warning**: Did you note the overhead penalty of strace before suggesting it for production?
- [ ] **eBPF kernel version**: Did you verify the required kernel version for any bpftrace/BCC tool?
- [ ] **OOM protection**: For critical services, did you set `oom_score_adj` and `MemoryMax`?
- [ ] **Namespace verification**: When claiming container isolation, did you verify which namespaces are actually used?
- [ ] **Cgroup version**: Did you check if the system uses cgroup v1 or v2 (`stat -fc %T /sys/fs/cgroup`)?
- [ ] **THP**: For database workloads, did you check THP settings (`/sys/kernel/mm/transparent_hugepage/enabled`)?
- [ ] **Journal persistence**: Is journald configured to persist to disk (`/etc/systemd/journald.conf` Storage=persistent)?
- [ ] **inode exhaustion**: When reporting "disk full" errors, did you check both `df -h` AND `df -i`?

---

## 15. Quick Reference Card

```bash
# System overview
uname -r              # Kernel version
lscpu                 # CPU topology
free -h               # Memory usage
df -h && df -i        # Disk space and inodes
uptime                # Load averages

# Process hunting
ps aux --sort=-%cpu | head -20
ps aux --sort=-%mem | head -20
pgrep -la nginx
pwdx <PID>            # Working directory of process

# Performance triage (60-second rundown)
uptime                # Load trend
dmesg | tail -20      # Kernel errors
vmstat 1 5            # CPU/memory/swap/io overview
iostat -xz 1 5        # Disk I/O
ss -s                 # Network socket summary
top -bn1              # CPU/mem snapshot

# Networking quick checks
ip addr && ip route
ss -tunapln | grep LISTEN
curl -v --max-time 5 http://localhost:8080/health
```
