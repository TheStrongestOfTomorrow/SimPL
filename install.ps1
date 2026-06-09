# ═══════════════════════════════════════════════════════════════
# SimPL Quick Install Script for Windows
# Usage:   irm https://raw.githubusercontent.com/thestrongestoftomorrow/SimPL/main/install.ps1 | iex
#          OR:  .\install.ps1
# ═══════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SimPL - Windows Installer" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ── Check Python ──────────────────────────────────────────────
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 8) {
                $pythonCmd = $cmd
                Write-Host "  Python:   $ver ✓" -ForegroundColor Green
                break
            }
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host "  Python 3.8+ is required but not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Install Python from: https://www.python.org/downloads/"
    Write-Host "  Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

# ── Check Node.js (optional) ──────────────────────────────────
try {
    $nodeVer = & node --version 2>&1
    Write-Host "  Node.js:  $nodeVer ✓ (NPM Bridge available)" -ForegroundColor Green
} catch {
    Write-Host "  Node.js:  Not found (optional, for NPM Bridge)" -ForegroundColor DarkGray
}

# ── Clone or update ───────────────────────────────────────────
$installDir = "$env:USERPROFILE\.simpl"

if (Test-Path $installDir) {
    Write-Host ""
    Write-Host "  SimPL directory already exists at $installDir" -ForegroundColor Yellow
    Write-Host "  Updating..."
    Push-Location $installDir
    git pull -q 2>$null
    Pop-Location
} else {
    Write-Host ""
    Write-Host "  Cloning SimPL repository..."
    git clone -q https://github.com/thestrongestoftomorrow/SimPL.git $installDir
}

Write-Host "  ✓ SimPL downloaded to $installDir" -ForegroundColor Green

# ── Create launcher ───────────────────────────────────────────
$binDir = "$env:APPDATA\SimPL"
New-Item -ItemType Directory -Force -Path $binDir | Out-Null

# Create simpl.bat
$batContent = @"
@echo off
REM SimPL Launcher - Auto-generated
if [%1]==[] (
    $pythonCmd "$installDir\simpl.py" --tui %*
) else (
    $pythonCmd "$installDir\simpl.py" %*
)
"@

Set-Content -Path "$binDir\simpl.bat" -Value $batContent -Force
Write-Host "  ✓ Created launcher: $binDir\simpl.bat" -ForegroundColor Green

# ── Add to PATH ───────────────────────────────────────────────
$pathParts = $env:PATH -split ";"
if ($pathParts -notcontains $binDir) {
    $env:PATH = "$binDir;$env:PATH"
    # Persist for future sessions
    try {
        [Environment]::SetEnvironmentVariable("PATH", "$binDir;" + [Environment]::GetEnvironmentVariable("PATH", "User"), "User")
        Write-Host "  ✓ Added $binDir to PATH" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ Could not add to PATH automatically." -ForegroundColor Yellow
        Write-Host "    Add $binDir to your PATH manually."
    }
} else {
    Write-Host "  ✓ $binDir is already in PATH" -ForegroundColor Green
}

# ── Done ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Usage:"
Write-Host "    simpl                    Launch the TUI"
Write-Host "    simpl run hello.simpl    Run a script"
Write-Host "    simpl --repl             Interactive REPL"
Write-Host "    simpl install super-math Install a package"
Write-Host ""
Write-Host "  Getting started:"
Write-Host "    simpl                    # Launch TUI and explore!"
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
