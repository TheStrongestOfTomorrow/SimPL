#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# SimPL Quick Install Script
# Works on: Linux, macOS, Termux (Android)
# Usage:    curl -sSL https://raw.githubusercontent.com/TheStrongestOfTomorrow/SimPL/main/install.sh | bash
#           OR:  bash install.sh
# ═══════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════${RESET}"
echo -e "${CYAN}  ${BOLD}SimPL - Quick Installer${RESET}"
echo -e "${CYAN}═══════════════════════════════════════════════════${RESET}"
echo ""

# ── Detect platform ──────────────────────────────────────────
detect_platform() {
    local uname_out="$(uname -s)"
    case "${uname_out}" in
        Linux*)
            if [ -d "/data/data/com.termux" ] || echo "$PREFIX" | grep -qi "termux"; then
                echo "termux"
            else
                echo "linux"
            fi
            ;;
        Darwin*)  echo "macos" ;;
        MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
        *)        echo "unknown" ;;
    esac
}

PLATFORM=$(detect_platform)
echo -e "  Platform: ${BOLD}${PLATFORM}${RESET}"

# ── Check Python ─────────────────────────────────────────────
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PY_VERSION=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PY_MAJOR=$($cmd -c 'import sys; print(sys.version_info.major)')
        if [ "$PY_MAJOR" -ge 3 ]; then
            PYTHON_CMD="$cmd"
            echo -e "  Python:   ${GREEN}${PY_VERSION} ✓${RESET}"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "  ${RED}Python 3.8+ is required but not found!${RESET}"
    echo ""
    echo "  Install Python:"
    if [ "$PLATFORM" = "termux" ]; then
        echo "    pkg install python"
    elif [ "$PLATFORM" = "linux" ]; then
        echo "    sudo apt install python3    # Debian/Ubuntu"
        echo "    sudo dnf install python3    # Fedora"
    elif [ "$PLATFORM" = "macos" ]; then
        echo "    brew install python3"
    fi
    exit 1
fi

# ── Check Node.js (optional) ─────────────────────────────────
if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    echo -e "  Node.js:  ${GREEN}${NODE_VER} ✓${RESET} (NPM Bridge available)"
else
    echo -e "  Node.js:  ${DIM}Not found (optional, for NPM Bridge)${RESET}"
fi

# ── Clone or update ──────────────────────────────────────────
INSTALL_DIR="$HOME/.simpl"

if [ -d "$INSTALL_DIR" ]; then
    echo ""
    echo -e "  ${YELLOW}SimPL directory already exists at $INSTALL_DIR${RESET}"
    echo -e "  Updating..."
    cd "$INSTALL_DIR"
    git pull -q 2>/dev/null || echo -e "  ${DIM}(Could not update via git)${RESET}"
else
    echo ""
    echo -e "  Cloning SimPL repository..."
    git clone -q https://github.com/TheStrongestOfTomorrow/SimPL.git "$INSTALL_DIR"
fi

echo -e "  ${GREEN}✓${RESET} SimPL downloaded to $INSTALL_DIR"

# ── Create launcher ──────────────────────────────────────────
BIN_DIR=""
if [ "$PLATFORM" = "termux" ]; then
    BIN_DIR="$PREFIX/bin"
elif [ "$PLATFORM" = "macos" ]; then
    BIN_DIR="/usr/local/bin"
    mkdir -p "$BIN_DIR" 2>/dev/null || BIN_DIR="$HOME/.local/bin"
elif [ "$PLATFORM" = "linux" ]; then
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
fi

# Create the simpl launcher script
LAUNCHER="$BIN_DIR/simpl"
cat > "$LAUNCHER" << EOF
#!/usr/bin/env bash
# SimPL Launcher - Auto-generated
SIMPL_DIR="$INSTALL_DIR"

if [ \$# -eq 0 ]; then
    exec $PYTHON_CMD "\$SIMPL_DIR/simpl.py" --tui
else
    exec $PYTHON_CMD "\$SIMPL_DIR/simpl.py" "\$@"
fi
EOF
chmod +x "$LAUNCHER"

# Also create simpl-tui
TUI_LAUNCHER="$BIN_DIR/simpl-tui"
cat > "$TUI_LAUNCHER" << EOF
#!/usr/bin/env bash
exec $PYTHON_CMD "$INSTALL_DIR/simpl.py" --tui "\$@"
EOF
chmod +x "$TUI_LAUNCHER"

echo -e "  ${GREEN}✓${RESET} Created launcher: $LAUNCHER"

# ── PATH check ───────────────────────────────────────────────
if echo ":$PATH:" | grep -q ":$BIN_DIR:"; then
    echo -e "  ${GREEN}✓${RESET} $BIN_DIR is in PATH"
else
    echo -e "  ${YELLOW}⚠ $BIN_DIR is not in PATH${RESET}"
    SHELL_RC="$HOME/.bashrc"
    if echo "$SHELL" | grep -q "zsh"; then
        SHELL_RC="$HOME/.zshrc"
    fi
    echo "" >> "$SHELL_RC"
    echo "# SimPL" >> "$SHELL_RC"
    echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$SHELL_RC"
    echo -e "  Added $BIN_DIR to $SHELL_RC"
    echo -e "  Run: ${BOLD}source $SHELL_RC${RESET}"
fi

# ── Done ─────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════${RESET}"
echo -e "  ${GREEN}${BOLD}Installation complete!${RESET}"
echo ""
echo "  Usage:"
echo "    simpl                    Launch the TUI"
echo "    simpl run hello.simpl    Run a script"
echo "    simpl --repl             Interactive REPL"
echo "    simpl install super-math Install a package"
echo ""
echo "  Getting started:"
echo "    simpl                    # Launch TUI and explore!"
echo -e "${CYAN}═══════════════════════════════════════════════════${RESET}"
echo ""
