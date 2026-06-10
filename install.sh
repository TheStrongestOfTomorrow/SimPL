#!/usr/bin/env bash
#
# SimPL Installer - GitHub Only
# Install: curl -sSL https://raw.githubusercontent.com/TheStrongestOfTomorrow/SimPL/main/install.sh | bash
#
set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
RESET='\033[0m'

REPO="TheStrongestOfTomorrow/SimPL"
GITHUB_API="https://api.github.com/repos/$REPO"
INSTALL_DIR="$HOME/.simpl"
BIN_DIR="$HOME/.local/bin"

print_banner() {
    echo -e "${CYAN}"
    echo "  ____                  _ _____           "
    echo " / ___|  ___  _ __  __| |_   _| __ __ _  ___ "
    echo " \\___ \\ / _ \\| '_ \\/ _\` | | || '__/ _\` |/ _ \\"
    echo "  ___) | (_) | | | (_| | | || | | (_| |  __/"
    echo " |____/ \\___/|_|  \\__,_| |_||_|  \\__,_|\\___|"
    echo -e "                    ${BOLD}v1.0.0${RESET}"
    echo ""
}

info() { echo -e "${GREEN}[✓]${RESET} $1"; }
warn() { echo -e "${YELLOW}[!]${RESET} $1"; }
error() { echo -e "${RED}[✖]${RESET} $1"; }

detect_platform() {
    OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
    ARCH="$(uname -m)"

    case "$OS" in
        linux)
            OS="linux"
            ;;
        darwin)
            OS="macos"
            ;;
        *)
            # Check for Termux
            if [ -n "$TERMUX_VERSION" ]; then
                OS="linux"
            else
                error "Unsupported OS: $OS"
                exit 1
            fi
            ;;
    esac

    case "$ARCH" in
        x86_64|amd64)
            ARCH="x86_64"
            ;;
        aarch64|arm64)
            ARCH="arm64"
            ;;
        armv7l|armv7)
            ARCH="armv7"
            ;;
        *)
            error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac

    # Termux detection
    if [ -n "$TERMUX_VERSION" ]; then
        INSTALL_DIR="$HOME/.simpl"
        BIN_DIR="$HOME/.local/bin"
        OS="linux"
    fi
}

get_latest_version() {
    local version
    version=$(curl -sSL "$GITHUB_API/releases/latest" 2>/dev/null | grep '"tag_name"' | head -1 | sed -E 's/.*"([^"]+)".*/\1/')
    if [ -z "$version" ]; then
        version="v1.0.0"
    fi
    echo "$version"
}

download_binary() {
    local version="$1"
    local filename="simpl-${OS}-${ARCH}"

    # Map platform to release asset name
    local asset_name
    case "$OS-$ARCH" in
        linux-x86_64)  asset_name="simpl-linux-x86_64" ;;
        linux-arm64)   asset_name="simpl-linux-arm64" ;;
        linux-armv7)   asset_name="simpl-linux-armv7" ;;
        macos-x86_64)  asset_name="simpl-macos-x86_64" ;;
        macos-arm64)   asset_name="simpl-macos-arm64" ;;
        *)             asset_name="simpl-${OS}-${ARCH}" ;;
    esac

    local download_url="https://github.com/$REPO/releases/download/${version}/${asset_name}"

    echo -e "${CYAN}[↓]${RESET} Downloading SimPL ${version} for ${OS}-${ARCH}..."

    mkdir -p "$INSTALL_DIR"

    # Try downloading from GitHub Releases
    if curl -sSL -f -o "$INSTALL_DIR/simpl" "$download_url" 2>/dev/null; then
        chmod +x "$INSTALL_DIR/simpl"
        info "Downloaded successfully"
        return 0
    fi

    # Fallback: build from source if Rust is available
    warn "Pre-built binary not available for ${OS}-${ARCH}"
    warn "Attempting to build from source..."

    if command -v cargo &>/dev/null; then
        build_from_source "$version"
        return 0
    fi

    error "No pre-built binary available and Rust/Cargo not found."
    echo ""
    echo -e "  Install Rust first:  ${CYAN}curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh${RESET}"
    echo -e "  Then re-run:         ${CYAN}curl -sSL https://raw.githubusercontent.com/TheStrongestOfTomorrow/SimPL/main/install.sh | bash${RESET}"
    exit 1
}

build_from_source() {
    local version="$1"
    echo -e "${CYAN}[⚒]${RESET} Building SimPL from source..."

    local tmp_dir
    tmp_dir=$(mktemp -d)
    cd "$tmp_dir"

    git clone "https://github.com/$REPO.git" simpl-src 2>/dev/null || {
        error "Failed to clone repository"
        rm -rf "$tmp_dir"
        exit 1
    }

    cd simpl-src
    cargo build --release 2>/dev/null || {
        error "Build failed"
        rm -rf "$tmp_dir"
        exit 1
    }

    cp "target/release/simpl" "$INSTALL_DIR/simpl"
    chmod +x "$INSTALL_DIR/simpl"

    rm -rf "$tmp_dir"
    info "Built successfully from source"
}

create_wrapper() {
    mkdir -p "$BIN_DIR"

    # Create wrapper script
    cat > "$BIN_DIR/simpl" << 'WRAPPER'
#!/usr/bin/env bash
exec "$HOME/.simpl/simpl" "$@"
WRAPPER
    chmod +x "$BIN_DIR/simpl"

    # Also create simpl-studio alias
    cat > "$BIN_DIR/simpl-studio" << 'WRAPPER'
#!/usr/bin/env bash
exec "$HOME/.simpl/simpl" studio "$@"
WRAPPER
    chmod +x "$BIN_DIR/simpl-studio"
}

add_to_path() {
    local shell_rc=""

    if [ -n "$BASH_VERSION" ]; then
        shell_rc="$HOME/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        shell_rc="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
        shell_rc="$HOME/.bashrc"
    elif [ -f "$HOME/.zshrc" ]; then
        shell_rc="$HOME/.zshrc"
    fi

    # Termux
    if [ -n "$TERMUX_VERSION" ]; then
        shell_rc="$HOME/.bashrc"
    fi

    if [ -n "$shell_rc" ]; then
        if ! grep -q '.local/bin' "$shell_rc" 2>/dev/null; then
            echo '' >> "$shell_rc"
            echo '# SimPL - added by installer' >> "$shell_rc"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$shell_rc"
        fi
    fi

    # Ensure PATH for current session
    export PATH="$BIN_DIR:$PATH"
}

# Main installation
main() {
    print_banner

    detect_platform
    echo -e "  Platform: ${BOLD}${OS}-${ARCH}${RESET}"
    echo ""

    # Get latest version
    VERSION=$(get_latest_version)
    echo -e "  Version: ${BOLD}${VERSION}${RESET}"
    echo ""

    # Download or build
    download_binary "$VERSION"

    # Create wrapper scripts
    create_wrapper

    # Add to PATH
    add_to_path

    # Verify installation
    if command -v simpl &>/dev/null; then
        echo ""
        info "SimPL installed successfully!"
        echo ""
        echo -e "  ${BOLD}Commands:${RESET}"
        echo -e "    simpl run <file>      Run a SimPL file"
        echo -e "    simpl repl            Interactive REPL"
        echo -e "    simpl studio          SimPL Studio (TUI IDE)"
        echo -e "    simpl install <pkg>   Install a package"
        echo -e "    simpl update          Update packages"
        echo -e "    simpl list            List packages"
        echo ""
        echo -e "  ${BOLD}Quick start:${RESET}"
        echo -e "    ${CYAN}simpl repl${RESET}           # Open interactive REPL"
        echo -e '    ${CYAN}say "Hello!"${RESET}        # In REPL, print a value'
        echo ""

        # Try running simpl --version
        "$INSTALL_DIR/simpl" --version 2>/dev/null || true

        if [ -n "$TERMUX_VERSION" ]; then
            echo -e "  ${YELLOW}Note: Run 'source ~/.bashrc' or restart your terminal${RESET}"
        else
            echo -e "  ${YELLOW}Note: Run 'source ~/.bashrc' (or ~/.zshrc) or restart your terminal${RESET}"
        fi
    else
        error "Installation verification failed"
        echo "  Try running: $INSTALL_DIR/simpl --version"
        exit 1
    fi
}

main "$@"
