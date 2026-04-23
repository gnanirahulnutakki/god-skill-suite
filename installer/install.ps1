# ─────────────────────────────────────────────────────────────────────────────
# God-Level Skill Suite — Windows PowerShell Bootstrap Installer
# Usage: irm https://raw.githubusercontent.com/your-org/god-skill-suite/main/installer/install.ps1 | iex
# Or: .\install.ps1
# ─────────────────────────────────────────────────────────────────────────────
param(
    [string]$Targets = "",
    [switch]$AllSkills,
    [switch]$DryRun,
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"

function Write-Banner {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║         GOD-LEVEL SKILL SUITE — WINDOWS INSTALLER           ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Test-Command($cmd) {
    return $null -ne (Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Install-UV {
    Write-Host "Installing uv..." -ForegroundColor Yellow
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
    $env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
}

function Clone-OrUpdate-Repo {
    $targetDir = "$env:USERPROFILE\.god-skill-suite"
    if (Test-Path "$targetDir\.git") {
        Write-Host "Updating existing installation at $targetDir..." -ForegroundColor Cyan
        git -C $targetDir pull --ff-only
    } else {
        Write-Host "Cloning god-skill-suite to $targetDir..." -ForegroundColor Cyan
        git clone --depth=1 "https://github.com/your-org/god-skill-suite.git" $targetDir
    }
    return $targetDir
}

Write-Banner

# Check git
if (-not (Test-Command "git")) {
    Write-Host "git is required. Install from: https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}

# Clone/update repo
$installDir = Clone-OrUpdate-Repo
Set-Location $installDir

# Build argument list
$args = @()
if ($Targets) { $args += "--targets", $Targets }
if ($AllSkills) { $args += "--all-skills" }
if ($DryRun) { $args += "--dry-run" }
if ($NonInteractive) { $args += "--non-interactive" }

# Prefer uv, fall back to python
if (Test-Command "uv") {
    Write-Host "Using uv to run installer..." -ForegroundColor Green
    uv run installer/install.py @args
} elseif (Test-Command "python") {
    $pythonVersion = python --version 2>&1
    Write-Host "Using $pythonVersion to run installer..." -ForegroundColor Green
    python installer/install.py @args
} elseif (Test-Command "python3") {
    python3 installer/install.py @args
} else {
    Write-Host "Installing uv (Python manager)..." -ForegroundColor Yellow
    Install-UV
    uv run installer/install.py @args
}
