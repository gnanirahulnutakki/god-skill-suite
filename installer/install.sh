#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# God-Level Skill Suite — Shell Bootstrap Installer
# Works on macOS and Linux. Automatically detects available Python/uv.
# Usage: curl -sSL https://raw.githubusercontent.com/gnanirahulnutakki/god-skill-suite/main/installer/install.sh | bash
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_banner() {
    echo ""
    echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║         GOD-LEVEL SKILL SUITE — BOOTSTRAP INSTALLER         ║${NC}"
    echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_python() {
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            version=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

check_uv() {
    if command -v uv &>/dev/null; then
        echo "uv"
        return 0
    fi
    return 1
}

install_uv() {
    echo -e "${YELLOW}Installing uv (fast Python package manager)...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    export PATH="$HOME/.local/bin:$PATH"
    if command -v uv &>/dev/null; then
        echo -e "${GREEN}✓ uv installed${NC}"
        return 0
    fi
    return 1
}

clone_or_update_repo() {
    local repo_url="https://github.com/gnanirahulnutakki/god-skill-suite.git"
    local target_dir="$HOME/.god-skill-suite"

    if [ -d "$target_dir/.git" ]; then
        echo -e "${CYAN}Updating existing installation at $target_dir...${NC}"
        git -C "$target_dir" pull --ff-only
    else
        echo -e "${CYAN}Cloning god-skill-suite to $target_dir...${NC}"
        git clone --depth=1 "$repo_url" "$target_dir"
    fi
    echo "$target_dir"
}

main() {
    print_banner

    # Check for git
    if ! command -v git &>/dev/null; then
        echo -e "${RED}✗ git is required. Please install git and try again.${NC}"
        exit 1
    fi

    # Clone/update the repository
    INSTALL_DIR=$(clone_or_update_repo)
    cd "$INSTALL_DIR"

    # Determine Python runtime
    UV_CMD=""
    PYTHON_CMD=""

    if UV_CMD=$(check_uv 2>/dev/null); then
        echo -e "${GREEN}✓ Found uv — using it for installation${NC}"
    elif PYTHON_CMD=$(check_python 2>/dev/null); then
        echo -e "${GREEN}✓ Found Python ($PYTHON_CMD) — using it for installation${NC}"
        # Offer to install uv for better experience
        read -rp $'\n'"  Install uv for faster installs? [Y/n]: " choice
        choice="${choice:-Y}"
        if [[ "$choice" =~ ^[Yy]$ ]]; then
            if install_uv; then
                UV_CMD="uv"
            fi
        fi
    else
        echo -e "${YELLOW}No Python 3.10+ found. Installing uv (which includes Python management)...${NC}"
        if install_uv; then
            UV_CMD="uv"
        else
            echo -e "${RED}✗ Could not install uv. Please install Python 3.10+ manually:${NC}"
            echo -e "  ${CYAN}https://www.python.org/downloads/${NC}"
            exit 1
        fi
    fi

    # Run the installer
    echo ""
    echo -e "${BOLD}Launching interactive installer...${NC}"
    echo ""

    if [ -n "$UV_CMD" ]; then
        "$UV_CMD" run installer/install.py "$@"
    else
        "$PYTHON_CMD" installer/install.py "$@"
    fi
}

main "$@"
