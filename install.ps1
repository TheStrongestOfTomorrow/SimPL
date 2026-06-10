# SimPL Installer for Windows - GitHub Only
# Install: irm https://raw.githubusercontent.com/TheStrongestOfTomorrow/SimPL/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

$REPO = "TheStrongestOfTomorrow/SimPL"
$GITHUB_API = "https://api.github.com/repos/$REPO"
$INSTALL_DIR = "$env:USERPROFILE\.simpl"
$BIN_DIR = "$env:APPDATA\SimPL"

function Print-Banner {
    Write-Host ""
    Write-Host "  ____                  _ _____           " -ForegroundColor Cyan
    Write-Host " / ___|  ___  _ __  __| |_   _| __ __ _  ___ " -ForegroundColor Cyan
    Write-Host " \___ \ / _ \| '_ \/ _` | | || '__/ _` |/ _ \" -ForegroundColor Cyan
    Write-Host "  ___) | (_) | | | (_| | | || | | (_| |  __/" -ForegroundColor Cyan
    Write-Host " |____/ \___/|_|  \__,_| |_||_|  \__,_|\___|" -ForegroundColor Cyan
    Write-Host "                    v1.0.0" -ForegroundColor White
    Write-Host ""
}

function Get-LatestVersion {
    try {
        $release = Invoke-RestMethod -Uri "$GITHUB_API/releases/latest" -ErrorAction Stop
        return $release.tag_name
    } catch {
        return "v1.0.0"
    }
}

function Download-Binary {
    param([string]$Version)

    $arch = if ([Environment]::Is64BitOperatingSystem) { "x86_64" } else { "x86" }
    $assetName = "simpl-windows-$arch.exe"
    $downloadUrl = "https://github.com/$REPO/releases/download/$Version/$assetName"

    Write-Host "  [↓] Downloading SimPL $Version for windows-$arch..." -ForegroundColor Cyan

    New-Item -ItemType Directory -Force -Path $INSTALL_DIR | Out-Null
    $targetPath = Join-Path $INSTALL_DIR "simpl.exe"

    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $targetPath -ErrorAction Stop
        Write-Host "  [✓] Downloaded successfully" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  [!] Pre-built binary not available for windows-$arch" -ForegroundColor Yellow
        Write-Host "  [!] Attempting to build from source..." -ForegroundColor Yellow
        return Build-FromSource -Version $Version
    }
}

function Build-FromSource {
    param([string]$Version)

    if (Get-Command cargo -ErrorAction SilentlyContinue) {
        Write-Host "  [⚒] Building SimPL from source..." -ForegroundColor Cyan

        $tmpDir = Join-Path $env:TEMP "simpl-build"
        New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null

        Push-Location $tmpDir
        git clone "https://github.com/$REPO.git" simpl-src 2>$null
        Set-Location "simpl-src"
        cargo build --release 2>$null
        Copy-Item "target\release\simpl.exe" (Join-Path $INSTALL_DIR "simpl.exe") -Force
        Pop-Location

        Remove-Item -Recurse -Force $tmpDir
        Write-Host "  [✓] Built successfully from source" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  [✖] No pre-built binary and Rust not found." -ForegroundColor Red
        Write-Host ""
        Write-Host "  Install Rust: https://rustup.rs/" -ForegroundColor Cyan
        return $false
    }
}

function Add-ToPath {
    New-Item -ItemType Directory -Force -Path $BIN_DIR | Out-Null

    # Create wrapper batch file
    $wrapperPath = Join-Path $BIN_DIR "simpl.bat"
    $simplExe = Join-Path $INSTALL_DIR "simpl.exe"
    "@echo off`n`"$simplExe`" %*" | Set-Content $wrapperPath

    # Create studio wrapper
    $studioPath = Join-Path $BIN_DIR "simpl-studio.bat"
    "@echo off`n`"$simplExe`" studio %*" | Set-Content $studioPath

    # Add to user PATH if not already there
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$BIN_DIR*") {
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$BIN_DIR", "User")
    }

    $env:Path += ";$BIN_DIR"
}

# Main
Print-Banner

$arch = if ([Environment]::Is64BitOperatingSystem) { "x86_64" } else { "x86" }
Write-Host "  Platform: windows-$arch" -ForegroundColor White

$version = Get-LatestVersion
Write-Host "  Version: $version" -ForegroundColor White
Write-Host ""

if (Download-Binary -Version $version) {
    Add-ToPath

    Write-Host ""
    Write-Host "  [✓] SimPL installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Commands:" -ForegroundColor White
    Write-Host "    simpl run <file>      Run a SimPL file"
    Write-Host "    simpl repl            Interactive REPL"
    Write-Host "    simpl studio          SimPL Studio (TUI IDE)"
    Write-Host "    simpl install <pkg>   Install a package"
    Write-Host ""
    Write-Host "  Quick start:" -ForegroundColor White
    Write-Host "    simpl repl" -ForegroundColor Cyan
    Write-Host '    say "Hello!"' -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Note: Restart your terminal to use 'simpl' command" -ForegroundColor Yellow
} else {
    Write-Host "  Installation failed." -ForegroundColor Red
    exit 1
}
