#!/usr/bin/env python3
"""
SimPL - Setup / Installation Script

Makes `simpl` available as a global command.
Supports: Linux, macOS, Windows, Termux (Android)
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path


# ── Configuration ──────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent.resolve()
BIN_NAME = "simpl"


def get_install_dir() -> Path:
    """Get the appropriate bin directory for the current platform."""
    plat = platform.system().lower()

    # Termux
    if 'termux' in os.environ.get('PREFIX', '').lower() or os.path.exists('/data/data/com.termux'):
        return Path(os.environ.get('PREFIX', '/data/data/com.termux/files/usr')) / 'bin'

    # Linux / macOS
    if plat in ('linux', 'darwin'):
        # Prefer ~/.local/bin if it exists or is in PATH
        local_bin = Path.home() / '.local' / 'bin'
        if str(local_bin) in os.environ.get('PATH', '') or local_bin.exists():
            return local_bin
        # Fall back to /usr/local/bin if writable
        usr_local = Path('/usr/local/bin')
        try:
            usr_local.mkdir(exist_ok=True)
            return usr_local
        except PermissionError:
            return local_bin

    # Windows
    if plat == 'windows':
        # Use %APPDATA%\SimPL or a Scripts dir
        appdata = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        simpl_dir = appdata / 'SimPL'
        simpl_dir.mkdir(parents=True, exist_ok=True)
        return simpl_dir

    # Fallback
    return Path.home() / '.local' / 'bin'


def get_simpl_source_dir() -> Path:
    """Find the SimPL source directory."""
    # If running from within the SimPL repo
    if (SCRIPT_DIR / 'simpl.py').exists():
        return SCRIPT_DIR
    # If installed via pip
    for site in sys.path:
        candidate = Path(site) / 'simpl'
        if candidate.exists():
            return candidate
    return SCRIPT_DIR


def create_launcher_script(install_dir: Path, source_dir: Path) -> Path:
    """Create the launcher script for the current platform."""
    plat = platform.system().lower()
    python_cmd = sys.executable

    if plat == 'windows':
        # Create a .bat launcher
        launcher_path = install_dir / f'{BIN_NAME}.bat'
        # Also create a simpl.cmd for PowerShell
        content = f'''@echo off
REM SimPL Launcher - Auto-generated
REM Source: {source_dir}
python "{source_dir / 'simpl.py'}" %*
'''
        with open(launcher_path, 'w') as f:
            f.write(content)

        # Also create .cmd version
        cmd_path = install_dir / f'{BIN_NAME}.cmd'
        with open(cmd_path, 'w') as f:
            f.write(content)

        return launcher_path
    else:
        # Create a shell script launcher (Linux, macOS, Termux)
        launcher_path = install_dir / BIN_NAME
        content = f'''#!/usr/bin/env bash
# SimPL Launcher - Auto-generated
# Source: {source_dir}
# This script makes 'simpl' available as a global command.

SIMPL_DIR="{source_dir}"
PYTHON_CMD="{python_cmd}"

# If no arguments, launch the TUI
if [ $# -eq 0 ]; then
    exec "$PYTHON_CMD" "$SIMPL_DIR/simpl.py" --tui
else
    exec "$PYTHON_CMD" "$SIMPL_DIR/simpl.py" "$@"
fi
'''
        with open(launcher_path, 'w') as f:
            f.write(content)

        # Make executable
        os.chmod(launcher_path, 0o755)
        return launcher_path


def create_tui_launcher(install_dir: Path, source_dir: Path) -> Path:
    """Create a TUI-only launcher."""
    plat = platform.system().lower()
    python_cmd = sys.executable

    if plat == 'windows':
        launcher_path = install_dir / f'{BIN_NAME}-tui.bat'
        content = f'''@echo off
REM SimPL TUI Launcher
python "{source_dir / 'simpl.py'}" --tui %*
'''
        with open(launcher_path, 'w') as f:
            f.write(content)
        return launcher_path
    else:
        launcher_path = install_dir / f'{BIN_NAME}-tui'
        content = f'''#!/usr/bin/env bash
# SimPL TUI Launcher
exec "{python_cmd}" "{source_dir / 'simpl.py'}" --tui "$@"
'''
        with open(launcher_path, 'w') as f:
            f.write(content)
        os.chmod(launcher_path, 0o755)
        return launcher_path


def uninstall():
    """Remove the simpl launcher scripts."""
    install_dir = get_install_dir()
    plat = platform.system().lower()
    removed = []

    if plat == 'windows':
        for name in [f'{BIN_NAME}.bat', f'{BIN_NAME}.cmd', f'{BIN_NAME}-tui.bat']:
            path = install_dir / name
            if path.exists():
                path.unlink()
                removed.append(str(path))
    else:
        for name in [BIN_NAME, f'{BIN_NAME}-tui']:
            path = install_dir / name
            if path.exists():
                path.unlink()
                removed.append(str(path))

    if removed:
        print(f"Removed: {', '.join(removed)}")
    else:
        print("No SimPL launcher scripts found.")


def install():
    """Install the simpl command globally."""
    print("=" * 50)
    print("  SimPL Installer v0.8.0")
    print("=" * 50)
    print()

    # Check Python version
    py_ver = sys.version_info
    if py_ver < (3, 8):
        print(f"Error: SimPL requires Python 3.8+. You have {py_ver.major}.{py_ver.minor}.")
        sys.exit(1)
    print(f"  Python: {py_ver.major}.{py_ver.minor}.{py_ver.micro} ✓ (Required)")

    # Check for curl (required for package management)
    try:
        result = subprocess.run(['curl', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            first_line = result.stdout.split('\n')[0]
            print(f"  curl:    {first_line.split()[1]} ✓ (Required)")
        else:
            print("  curl:    Not found! (Required for package management and HTTP)")
    except Exception:
        print("  curl:    Not found! (Required for package management and HTTP)")

    # Check for Node.js (optional)
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"  Node.js: {result.stdout.strip()} ✓ (NPM Bridge available)")
        else:
            print("  Node.js: Not found (optional, needed for NPM Bridge)")
    except Exception:
        print("  Node.js: Not found (optional, needed for NPM Bridge)")

    # Check for git (optional)
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"  git:     {result.stdout.strip().split()[-1]} ✓ (Updates)")
        else:
            print("  git:     Not found (optional, needed for auto-updates)")
    except Exception:
        print("  git:     Not found (optional, needed for auto-updates)")

    # Get directories
    source_dir = get_simpl_source_dir()
    install_dir = get_install_dir()

    print(f"\n  Source: {source_dir}")
    print(f"  Install: {install_dir}")

    # Create install directory
    install_dir.mkdir(parents=True, exist_ok=True)

    # Create launchers
    print("\n  Creating launchers...")
    launcher = create_launcher_script(install_dir, source_dir)
    print(f"  Created: {launcher}")

    tui_launcher = create_tui_launcher(install_dir, source_dir)
    print(f"  Created: {tui_launcher}")

    # Check PATH
    if str(install_dir) not in os.environ.get('PATH', ''):
        print(f"\n  ⚠️  Warning: {install_dir} is not in your PATH!")
        plat = platform.system().lower()
        if plat == 'windows':
            print(f"  Add it to PATH: System Properties > Environment Variables > Path > Add {install_dir}")
        else:
            shell_rc = Path.home() / '.bashrc'
            if os.environ.get('SHELL', '').endswith('zsh'):
                shell_rc = Path.home() / '.zshrc'
            print(f"  Run this command to add it:")
            print(f'    echo \'export PATH="{install_dir}:$PATH"\' >> {shell_rc}')
            print(f"    source {shell_rc}")
    else:
        print(f"\n  ✓ {install_dir} is in PATH")

    print()
    print("=" * 50)
    print("  Installation complete!")
    print()
    print("  Usage:")
    print("    simpl              # Launch TUI")
    print("    simpl run file.simpl    # Run a script")
    print("    simpl --repl      # Interactive REPL")
    print("    simpl install pkg # Install a package")
    print("=" * 50)


def main():
    """Entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ('--uninstall', '-u', 'uninstall'):
        uninstall()
    else:
        install()


if __name__ == '__main__':
    main()
