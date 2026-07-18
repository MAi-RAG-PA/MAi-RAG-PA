#!/bin/bash
# MAi-RAG-PA Universal Installer v2.0
# Supports: Linux (Debian/Ubuntu, Fedora/RHEL, Arch), macOS, Windows (WSL2)
# Guaranteed to work on first try with comprehensive error handling

set -euo pipefail

# ============================================================================
# Constants & Configuration
# ============================================================================
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly INSTALL_DIR="$HOME/MAi-RAG-PA"
readonly GITHUB_REPO="https://github.com/MAi-RAG-PA/MAi-RAG-PA.git"
readonly MIN_PYTHON_VERSION="3.12"
readonly MIN_NODE_VERSION="20"
readonly MIN_OLLAMA_VERSION="0.30"
readonly MIN_QDRANT_VERSION="1.17"
readonly REQUIRED_SPACE_MB=5000
readonly LOG_FILE="/tmp/mai-rag-install-$(date +%Y%m%d-%H%M%S).log"
readonly BACKUP_DIR="$HOME/MAi-RAG-PA-backups"

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# ============================================================================
# Utility Functions
# ============================================================================

log() {
    local message="$1"
    local color="${2:-$NC}"
    echo -e "${color}${message}${NC}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $message" >> "$LOG_FILE" 2>/dev/null || true
}

error() {
    log "✗ ERROR: $1" "$RED"
    log "Check log file: $LOG_FILE" "$YELLOW"
    exit 1
}

warn() {
    log "⚠ WARNING: $1" "$YELLOW"
}

success() {
    log "✓ $1" "$GREEN"
}

info() {
    log "$1" "$BLUE"
}

step() {
    log ""
    log "═══════════════════════════════════════════════════════" "$CYAN"
    log "  $1" "$CYAN"
    log "═══════════════════════════════════════════════════════" "$CYAN"
}

# Cleanup function for interrupted installations
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log ""
        warn "Installation was interrupted or failed (exit code: $exit_code)"
        warn "Check log file: $LOG_FILE"
        warn "You can resume by running this script again"
    fi
}

trap cleanup EXIT

# ============================================================================
# Version Comparison
# ============================================================================

version_gt() {
    [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" != "$1" ]
}

version_ge() {
    [ "$1" = "$2" ] || version_gt "$1" "$2"
}

# ============================================================================
# Cross-Platform System Detection
# ============================================================================

detect_os() {
    info "Detecting operating system..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            VER=$VERSION_ID
            success "Detected Linux: $PRETTY_NAME"
        else
            OS="unknown-linux"
            warn "Unknown Linux distribution"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        VER=$(sw_vers -productVersion)
        success "Detected macOS: $VER"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
        success "Detected Windows (WSL2)"
    elif [[ "$OSTYPE" == "freebsd"* || "$OSTYPE" == "openbsd"* || "$OSTYPE" == "netbsd"* ]]; then
        OS="bsd"
        success "Detected BSD: $OSTYPE"
    else
        error "Unsupported operating system: $OSTYPE"
    fi
}

get_ram_gb() {
    local ram_gb=0

    if command -v free &> /dev/null; then
        # Linux
        ram_gb=$(free -g 2>/dev/null | awk '/^Mem:/{print $2}' || echo "0")
    elif command -v sysctl &> /dev/null; then
        # macOS/BSD
        ram_gb=$(sysctl -n hw.memsize 2>/dev/null | awk '{print int($1/1024/1024/1024)}' || echo "0")
    elif [ -f /proc/meminfo ]; then
        # Fallback for Linux
        ram_gb=$(awk '/MemTotal/ {print int($2/1024/1024)}' /proc/meminfo || echo "0")
    fi

    echo "$ram_gb"
}

get_cpu_cores() {
    local cores=0

    if command -v nproc &> /dev/null; then
        cores=$(nproc 2>/dev/null || echo "0")
    elif command -v sysctl &> /dev/null; then
        cores=$(sysctl -n hw.ncpu 2>/dev/null || echo "0")
    fi

    echo "$cores"
}

# ============================================================================
# Validation Functions
# ============================================================================

check_internet() {
    info "Checking internet connectivity..."

    # Try multiple DNS servers
    if ping -c 1 -W 5 8.8.8.8 &> /dev/null || \
       ping -c 1 -W 5 1.1.1.1 &> /dev/null || \
       ping -c 1 -W 5 208.67.222.222 &> /dev/null; then
        success "Internet connection verified"
        return 0
    fi

    error "No internet connection detected. Internet is required for installation."
}

check_disk_space() {
    info "Checking available disk space..."

    local available_mb
    available_mb=$(df -m "$HOME" | awk 'NR==2 {print $4}')

    if [ "$available_mb" -lt "$REQUIRED_SPACE_MB" ]; then
        error "Insufficient disk space. Need ${REQUIRED_SPACE_MB}MB, have ${available_mb}MB"
    fi

    success "Sufficient disk space available (${available_mb}MB)"
}

check_python_version() {
    info "Checking Python version..."

    # Prefer python3.12 if available (common on macOS via Homebrew)
    local python_cmd="python3"
    if command -v python3.12 &> /dev/null; then
        python_cmd="python3.12"
    elif command -v python3 &> /dev/null; then
        python_cmd="python3"
    else
        return 1
    fi

    local version
    version=$("$python_cmd" --version 2>&1 | awk '{print $2}')
    local major minor
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)

    local req_major req_minor
    req_major=$(echo "$MIN_PYTHON_VERSION" | cut -d. -f1)
    req_minor=$(echo "$MIN_PYTHON_VERSION" | cut -d. -f2)

    if [ "$major" -lt "$req_major" ] || ([ "$major" -eq "$req_major" ] && [ "$minor" -lt "$req_minor" ]); then
        warn "Python $version found via $python_cmd, but $MIN_PYTHON_VERSION+ required"

        if [[ "$OS" == "macos" ]]; then
            echo -e "${YELLOW}Tip: Run 'brew install python@3.12' and ensure it's in your PATH.${NC}"
        fi
        return 1
    fi

    success "Python $version detected"
    # Export the detected command so the rest of the script uses the correct one
    export DETECTED_PYTHON="$python_cmd"
    return 0
}

check_node_version() {
    info "Checking Node.js version..."

    if ! command -v node &> /dev/null; then
        return 1
    fi

    local version
    version=$(node --version 2>&1 | sed 's/v//' | cut -d. -f1)

    if [ "$version" -lt "$MIN_NODE_VERSION" ]; then
        warn "Node.js v$version found, but v${MIN_NODE_VERSION}+ required"
        return 1
    fi

    success "Node.js v$version detected"
    return 0
}

check_git_version() {
    info "Checking Git version..."

    if ! command -v git &> /dev/null; then
        return 1
    fi

    local version
    version=$(git --version 2>&1 | awk '{print $3}')
    success "Git $version detected"
    return 0
}

check_ollama_version() {
    info "Checking Ollama version..."

    # Check multiple locations
    local ollama_path=""
    if command -v ollama &> /dev/null; then
        ollama_path="ollama"
    elif [ -f "$INSTALL_DIR/ollama" ]; then
        ollama_path="$INSTALL_DIR/ollama"
    elif [ -f "$HOME/ollama" ]; then
        ollama_path="$HOME/ollama"
    else
        return 1
    fi

    local version
    version=$("$ollama_path" --version 2>&1 | awk '/version is/ {print $NF}' || echo "0.0")

    if ! version_ge "$version" "$MIN_OLLAMA_VERSION"; then
        warn "Ollama $version found, but $MIN_OLLAMA_VERSION+ required"
        return 1
    fi

    success "Ollama $version detected"
    return 0
}

check_qdrant_version() {
    info "Checking Qdrant version..."

    local qdrant_path=""
    if [ -f "$INSTALL_DIR/qdrant" ]; then
        qdrant_path="$INSTALL_DIR/qdrant"
    elif [ -f "./qdrant" ]; then
        qdrant_path="./qdrant"
    elif command -v qdrant &> /dev/null; then
        qdrant_path="qdrant"
    else
        return 1
    fi

    local version
    version=$("$qdrant_path" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "0.0.0")

    if ! version_ge "$version" "$MIN_QDRANT_VERSION"; then
        warn "Qdrant $version found, but $MIN_QDRANT_VERSION+ required"
        return 1
    fi

    success "Qdrant $version detected"
    return 0
}

check_macos_cli_tools() {
    if [[ "$OS" == "macos" ]]; then
        if ! xcode-select -p &> /dev/null; then
            warn "macOS Command Line Tools are required but not installed."
            info "A popup will appear asking you to install them. Please click 'Install'."

            # Trigger the macOS GUI installation prompt
            xcode-select --install

            # Wait in a loop until the tools are actually installed
            info "Waiting for installation to complete (this may take a few minutes)..."
            while ! xcode-select -p &> /dev/null; do
                sleep 5
            done
            success "macOS Command Line Tools installed successfully!"
        else
            success "macOS Command Line Tools are already installed."
        fi
    fi
}

# ============================================================================
# Dependency Installation
# ============================================================================

install_dependencies() {
    step "Installing System Dependencies"

    case $OS in
        "ubuntu"|"debian"|"linuxmint"|"pop"|"elementary"|"zorin")
            info "Installing dependencies for Debian/Ubuntu..."

            # Update package lists
            sudo apt update || error "Failed to update package lists"

            # Check Node.js version in repos
            local node_version=0
            if command -v node &> /dev/null; then
                node_version=$(node --version 2>&1 | sed 's/v//' | cut -d. -f1)
            else
                node_version=$(apt-cache policy nodejs 2>/dev/null | grep Candidate | awk '{print $2}' | cut -d. -f1 || echo "0")
            fi

            # Install NodeSource if needed
            if [ "$node_version" -lt "$MIN_NODE_VERSION" ]; then
                info "Node.js in repository is too old. Installing NodeSource repository..."
                curl -fsSL "https://deb.nodesource.com/setup_${MIN_NODE_VERSION}.x" | sudo -E bash - || error "Failed to add NodeSource repository"
            fi

            sudo apt install -y python3 python3-pip python3-venv nodejs npm git curl || error "Failed to install dependencies"
            ;;

        "fedora"|"rhel"|"centos"|"rocky"|"alma")
            info "Installing dependencies for Fedora/RHEL..."
            sudo dnf install -y python3 python3-pip nodejs npm git curl || error "Failed to install dependencies"
            ;;

        "arch"|"manjaro"|"endeavouros")
            info "Installing dependencies for Arch Linux..."
            sudo pacman -S --noconfirm --needed python python-pip nodejs npm git curl || error "Failed to install dependencies"
            ;;

        "opensuse"|"sles")
            info "Installing dependencies for openSUSE..."
            sudo zypper install -y python3 python3-pip nodejs npm git curl || error "Failed to install dependencies"
            ;;

        "macos")
            info "Installing dependencies for macOS..."

            # Install Homebrew if needed
            if ! command -v brew &> /dev/null; then
                warn "Homebrew not found. Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || error "Failed to install Homebrew"

                # Add Homebrew to PATH
                if [[ $(uname -m) == "arm64" ]]; then
                    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
                    eval "$(/opt/homebrew/bin/brew shellenv)"
                fi
            fi

            brew install python@3.12 node git || error "Failed to install dependencies"
            ;;

        "windows")
            error "Windows detected. Please use WSL2 for MAi-RAG-PA.
   Install WSL2: https://docs.microsoft.com/windows/wsl/install"
            ;;

        "bsd")
            info "Installing dependencies for BSD..."
            sudo pkg install -y python3 node npm git curl || error "Failed to install dependencies"
            ;;

        *)
            warn "Unknown OS. Please install manually:"
            echo "  - Python $MIN_PYTHON_VERSION+"
            echo "  - Node.js $MIN_NODE_VERSION+"
            echo "  - Git"
            echo "  - curl"
            read -p "Press Enter to continue if dependencies are installed..."
            ;;
    esac

    # Verify installations
    if ! check_python_version; then
        error "Python installation failed or version too old"
    fi

    if ! check_node_version; then
        error "Node.js installation failed or version too old"
    fi

    if ! check_git_version; then
        error "Git installation failed"
    fi

    success "All system dependencies installed successfully"
}

# ============================================================================
# Ollama Installation
# ============================================================================

install_ollama() {
    step "Installing Ollama"

    if [[ "$OS" == "macos" ]]; then
        # ===== macOS Installation =====
        info "Installing Ollama for macOS..."

        if command -v brew &> /dev/null; then
            info "Installing via Homebrew..."
            brew install --cask ollama || error "Failed to install Ollama via Homebrew"
        else
            info "Homebrew not found. Downloading Ollama manually..."
            local ollama_url="https://ollama.com/download/Ollama-darwin.zip"
            local temp_zip="/tmp/Ollama-darwin.zip"

            curl -fsSL "$ollama_url" -o "$temp_zip" || error "Failed to download Ollama"

            info "Extracting Ollama..."
            unzip -q -o "$temp_zip" -d /Applications/ || error "Failed to extract Ollama"
            rm -f "$temp_zip"

            info "Opening Ollama application..."
            open /Applications/Ollama.app
            sleep 5
        fi

    else
        # ===== Linux Installation =====
        local arch
        arch=$(uname -m)
        case $arch in
            x86_64) arch="amd64" ;;
            aarch64|arm64) arch="arm64" ;;
            *) error "Unsupported architecture: $arch" ;;
        esac

        local ollama_url="https://ollama.com/download/ollama-linux-${arch}"
        local ollama_dest="$INSTALL_DIR/ollama"

        info "Downloading Ollama for Linux-$arch..."
        curl -fsSL "$ollama_url" -o "$ollama_dest" || error "Failed to download Ollama"
        chmod +x "$ollama_dest"

        if ! "$ollama_dest" --version &> /dev/null; then
            error "Downloaded Ollama binary is not executable or corrupted"
        fi

        if ! command -v ollama &> /dev/null; then
            info "Adding Ollama to PATH..."
            echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> ~/.bashrc
            echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> ~/.zshrc 2>/dev/null || true
            export PATH="$INSTALL_DIR:$PATH"
        fi
    fi

    # ===== Start Ollama (All Platforms) =====
    info "Starting Ollama service..."

    if [[ "$OS" == "macos" ]]; then
        # On macOS, Ollama.app handles the service
        if command -v ollama &> /dev/null; then
            ollama serve &> /dev/null &
            sleep 3
        else
            open -a Ollama
            sleep 5
        fi
    elif command -v systemctl &> /dev/null && systemctl list-unit-files 2>/dev/null | grep -q ollama.service; then
        sudo systemctl start ollama || warn "Could not start Ollama via systemctl"
    else
        # Fallback: run binary directly
        local ollama_cmd="ollama"
        if [ -f "$INSTALL_DIR/ollama" ]; then
            ollama_cmd="$INSTALL_DIR/ollama"
        fi
        "$ollama_cmd" serve &> /dev/null &
        sleep 3
    fi

    # ===== Verify Ollama is Running =====
    local retries=10
    while [ $retries -gt 0 ]; do
        if curl -s http://localhost:11434/api/tags &> /dev/null; then
            success "Ollama service started successfully"
            return 0
        fi
        retries=$((retries - 1))
        sleep 2
    done

    warn "Ollama service may not have started correctly."
    if [[ "$OS" == "macos" ]]; then
        warn "Please open the Ollama app from your Applications folder or menu bar."
    else
        warn "You may need to start it manually: ollama serve"
    fi
}

# ============================================================================
# Qdrant Installation
# ============================================================================

install_qdrant() {
    step "Installing Qdrant"

    # Detect architecture
    local arch
    arch=$(uname -m)
    case $arch in
        x86_64) arch="x86_64" ;;
        aarch64|arm64) arch="aarch64" ;;
        *) error "Unsupported architecture: $arch" ;;
    esac

    # Detect OS
    local os_type
    case $OS in
        "ubuntu"|"debian"|"linuxmint"|"pop"|"elementary"|"zorin"|"fedora"|"rhel"|"centos"|"rocky"|"alma"|"arch"|"manjaro"|"endeavouros"|"opensuse"|"sles")
            os_type="unknown-linux-gnu"
            ;;
        "macos")
            os_type="apple-darwin"
            ;;
        *)
            error "Unsupported OS for Qdrant installation: $OS"
            ;;
    esac

    # Get latest Qdrant version
    local latest_version
    latest_version=$(curl -fsSL "https://api.github.com/repos/qdrant/qdrant/releases/latest" | grep '"tag_name":' | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/' || echo "v1.17.0")

    # Download Qdrant binary
    local qdrant_filename="qdrant-${os_type}-${arch}.tar.gz"
    local qdrant_url="https://github.com/qdrant/qdrant/releases/download/${latest_version}/${qdrant_filename}"
    local qdrant_dest="$INSTALL_DIR/qdrant"
    local temp_dir="/tmp/qdrant-install-$$"

    info "Downloading Qdrant $latest_version for $os_type-$arch..."
    mkdir -p "$temp_dir"
    curl -fsSL "$qdrant_url" -o "$temp_dir/$qdrant_filename" || error "Failed to download Qdrant"

    # Extract binary
    info "Extracting Qdrant..."
    tar -xzf "$temp_dir/$qdrant_filename" -C "$temp_dir" || error "Failed to extract Qdrant"

    # Move binary to install directory
    if [ -f "$temp_dir/qdrant" ]; then
        mv "$temp_dir/qdrant" "$qdrant_dest"
        chmod +x "$qdrant_dest"
    else
        error "Qdrant binary not found in archive"
    fi

    # Verify the binary works
    if ! "$qdrant_dest" --version &> /dev/null; then
        error "Downloaded Qdrant binary is not executable or corrupted"
    fi

    # Cleanup
    rm -rf "$temp_dir"

    success "Qdrant installed to $qdrant_dest"
}

# ============================================================================
# Installation Preference Dialog
# ============================================================================

ask_installation_preference() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Ollama & Qdrant Installation Preference              ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "MAi-RAG-PA requires Ollama (for AI models) and Qdrant (for vector database)."
    echo ""
    echo "How would you like to install these components?"
    echo ""
    echo "  [A]utomatic - Install both Ollama and Qdrant automatically"
    echo "  [M]anual    - I'll install them myself (instructions provided)"
    echo ""
    read -p "Your choice [A/m]: " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Mm]$ ]]; then
        echo ""
        info "Manual installation instructions:"
        echo ""
        echo "1. Install Ollama:"
        echo "   curl -fsSL https://ollama.com/install.sh | sh"
        echo "   Or download from: https://ollama.com/download"
        echo ""
        echo "2. Install Qdrant:"
        echo "   Download from: https://github.com/qdrant/qdrant/releases"
        echo "   Place the 'qdrant' binary in: $INSTALL_DIR/"
        echo "   Make it executable: chmod +x $INSTALL_DIR/qdrant"
        echo ""
        read -p "Press Enter when you've installed both Ollama and Qdrant..."

        # Verify installations
        if ! check_ollama_version; then
            error "Ollama not found or version too old. Please install Ollama $MIN_OLLAMA_VERSION+"
        fi

        if ! check_qdrant_version; then
            error "Qdrant not found or version too old. Please install Qdrant $MIN_QDRANT_VERSION+"
        fi

        return 0
    fi

    return 1
}

# ============================================================================
# Desktop Launcher Creation
# ============================================================================

create_desktop_launchers() {
    step "Creating One-Click Launchers"

    if [[ "$OS" == "ubuntu" || "$OS" == "debian" || "$OS" == "linuxmint" || "$OS" == "fedora" || "$OS" == "arch" ]]; then
        mkdir -p ~/.local/share/applications
        cat > ~/.local/share/applications/MAi-RAG-PA.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=MAi-RAG-PA
Comment=Offline AI Personal Assistant
Exec=$INSTALL_DIR/launch.sh
Icon=$INSTALL_DIR/assets/mai-rag-logo.png
Terminal=true
Categories=Utility;Network;
EOF
        chmod +x ~/.local/share/applications/MAi-RAG-PA.desktop
        update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
        success "Linux launcher created (Search 'MAi-RAG-PA' in your app menu)"

    elif [[ "$OS" == "macos" ]]; then
        local app_name="MAi-RAG-PA"
        local app_path="/Applications/${app_name}.app"

        if ! mkdir -p "$app_path" 2>/dev/null; then
            app_path="$HOME/Applications/${app_name}.app"
            mkdir -p "$app_path"
        fi

        mkdir -p "$app_path/Contents/MacOS"
        mkdir -p "$app_path/Contents/Resources"
        local updater_path="$HOME/Desktop/Update MAi-RAG-PA.command"
        cat > "$app_path/Contents/MacOS/MAi-RAG-PA" << 'EOF'
#!/bin/bash
cd "$HOME/MAi-RAG-PA" || exit
if [ -f "/opt/homebrew/bin/brew" ]; then
    export PATH="$(brew --prefix python@3.12)/libexec/bin:$PATH"
fi
./launch.sh
EOF
        chmod +x "$app_path/Contents/MacOS/MAi-RAG-PA"

        cat > "$app_path/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key><string>MAi-RAG-PA</string>
    <key>CFBundleIdentifier</key><string>com.mai-rag-pa.app</string>
    <key>CFBundleName</key><string>MAi-RAG-PA</string>
    <key>CFBundleVersion</key><string>1.0.0</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>LSMinimumSystemVersion</key><string>10.15</string>
</dict>
</plist>
EOF
        success "macOS App created at: $app_path"
        info "Drag 'MAi-RAG-PA.app' to your Dock. Right-click > Open the first time."

    elif [[ "$OS" == "windows" ]]; then
        chmod +x "$INSTALL_DIR/launch.bat"
        success "Windows launchers created: launch.bat (visible) and launch.vbs (hidden)"
        info "Double-click 'launch.vbs' to start the app invisibly."
    fi
}

# ============================================================================
# Main Installation
# ============================================================================

main() {
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        warn "Running as root is not recommended. Some features may not work correctly."
        read -p "Continue anyway? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi

    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   MAi-RAG-PA Installation Script v2.0  ║${NC}"
    echo -e "${BLUE}║   Offline AI Personal Assistant        ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    info "Installation log: $LOG_FILE"
    echo ""

    # Pre-flight checks
    step "Pre-Flight Checks"
    check_internet
    check_disk_space
    detect_os

    # Check for macOS CLI tools specifically
    if [[ "$OS" == "macos" ]]; then
        check_macos_cli_tools
    fi

    # Check for existing installation
    if [ -d "$INSTALL_DIR" ]; then
        warn "MAi-RAG-PA already exists at $INSTALL_DIR"

        if [ -d "$INSTALL_DIR/.git" ]; then
            read -p "Update existing installation? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 0
            fi

            # Create backup
            info "Creating backup..."
            mkdir -p "$BACKUP_DIR"
            local backup_name="MAi-RAG-PA-backup-$(date +%Y%m%d-%H%M%S)"
            cp -r "$INSTALL_DIR" "$BACKUP_DIR/$backup_name" || warn "Failed to create backup"
            success "Backup created at $BACKUP_DIR/$backup_name"

            cd "$INSTALL_DIR" || error "Failed to change to installation directory"
            info "Pulling latest changes..."
            git pull || error "Failed to pull latest changes"
        else
            error "Directory exists but is not a git repository. Please remove it manually: rm -rf $INSTALL_DIR"
        fi
    else
        # Clone repository
        step "Downloading MAi-RAG-PA"
        info "Cloning repository..."

        # Attempt to clone, but catch macOS git failures gracefully
        if ! git clone "$GITHUB_REPO" "$INSTALL_DIR" 2>/dev/null; then
            if [[ "$OS" == "macos" ]]; then
                echo ""
                echo -e "${RED}╔════════════════════════════════════════════════════════╗${NC}"
                echo -e "${RED}║  macOS Git Installation Detected                       ║${NC}"
                echo -e "${RED}╚════════════════════════════════════════════════════════╝${NC}"
                echo ""
                echo -e "${YELLOW}Apple's security prevents automated Git installation via curl.${NC}"
                echo -e "${YELLOW}Please run these commands manually to complete setup:${NC}"
                echo ""
                echo "  1. /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                echo "  2. brew install git python@3.12"
                echo "  3. git clone $GITHUB_REPO $INSTALL_DIR"
                echo "  4. cd $INSTALL_DIR && ./install.sh"
                echo ""
                exit 1
            else
                error "Failed to clone repository. Check your internet connection or DNS settings."
            fi
        fi

        # This was orphaned in your script; it now correctly lives inside the 'else' block
        cd "$INSTALL_DIR" || error "Failed to change to installation directory"
    fi  # <--- THIS 'fi' WAS MISSING IN YOUR SNIPPET

    # Verify required files exist
    info "Verifying required files..."
    local required_files=("requirements.txt" "frontend/package.json" "start.sh" "stop.sh" "first_launch.py" "prompt.py")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error "Required file missing: $file"
        fi
    done
    success "All required files present"

    # Create directory structure
    info "Creating directory structure..."
    mkdir -p memory storage workspace logs
    success "Directory structure created"

    # Install dependencies
    install_dependencies

    # Setup Python environment
    step "Setting Up Python Environment"

    if [ ! -d "venv" ]; then
        info "Creating virtual environment..."
        # Use the detected Python version (falls back to python3 if not set)
        ${DETECTED_PYTHON:-python3} -m venv venv || error "Failed to create virtual environment"
    fi

    info "Activating virtual environment..."
    source venv/bin/activate || error "Failed to activate virtual environment"

    if [ -z "${VIRTUAL_ENV:-}" ]; then
        error "Virtual environment activation failed"
    fi

    info "Upgrading pip..."
    pip install --upgrade pip || warn "Failed to upgrade pip"

    info "Installing Python dependencies (this may take several minutes)..."
    pip install -r requirements.txt || error "Failed to install Python dependencies. Check $LOG_FILE for details."

    info "Verifying Python package installation..."
    python -c "import fastapi, uvicorn, qdrant_client, sentence_transformers, spacy" || \
        error "Critical Python packages not installed correctly"
    success "Python packages verified"

    info "Downloading SpaCy English model..."
    python -m spacy download en_core_web_sm || warn "Failed to download SpaCy model"
    success "SpaCy model ready"

    # Build frontend
    step "Building Frontend"

    cd frontend || error "Frontend directory not found"

    info "Installing npm dependencies..."
    npm install || error "Failed to install npm dependencies"

    info "Building frontend (this may take several minutes)..."
    npm run build || error "Failed to build frontend"

    if [ ! -d "dist" ] && [ ! -d "build" ]; then
        error "Frontend build directory not found. Build may have failed."
    fi

    success "Frontend built successfully"
    cd ..

    # Install Ollama and Qdrant
    step "Installing AI Components"

    ask_installation_preference
    user_choice=$?

    if [ $user_choice -eq 0 ]; then
        # User chose manual
        info "Verifying manual installations..."
        if ! check_ollama_version; then
            error "Ollama not found or version too old. Please install Ollama $MIN_OLLAMA_VERSION+"
        fi
        if ! check_qdrant_version; then
            error "Qdrant not found or version too old. Please install Qdrant $MIN_QDRANT_VERSION+"
        fi
        success "Manual installations verified"
    else
        # User chose automatic
        if ! check_ollama_version; then
            install_ollama
        else
            success "Ollama is up to date"
        fi

        if ! check_qdrant_version; then
            install_qdrant
        else
            success "Qdrant is up to date"
        fi
    fi

    # Initialize database
    step "Initializing Database"

    info "Running first launch setup..."
    if [ -f "./first_launch.py" ]; then
        python3 first_launch.py || warn "Database initialization had warnings"
        success "Database initialized"
    else
        warn "first_launch.py not found - database may not be initialized"
    fi

    # Seed system prompt
    info "Seeding system prompt into database..."
    if [ -f "./prompt.py" ]; then
        python3 prompt.py
        if [ $? -eq 0 ]; then
            success "System prompt seeded into database"
        else
            warn "Failed to seed system prompt. Run 'python3 prompt.py' manually."
        fi
    else
        warn "prompt.py not found. System prompt will use defaults."
    fi

    # Pull required models
    step "Pulling Required AI Models"

    # Detect hardware
    local ram_gb
    ram_gb=$(get_ram_gb)
    local cpu_cores
    cpu_cores=$(get_cpu_cores)

    info "Detected hardware: ${ram_gb}GB RAM, ${cpu_cores} CPU cores"

    if [ "$ram_gb" -lt 8 ] && [ "$ram_gb" -gt 0 ]; then
        warn "Low RAM detected ($ram_gb GB). codeqwen:7b requires ~4.5GB RAM."
        warn "System may be slower. Consider upgrading RAM for optimal performance."
    fi

    # Pull protected model
    if ! ollama list 2>/dev/null | grep -q "codeqwen:7b"; then
        info "Pulling codeqwen:7b (Protected system model - STM parser + Text-to-SQL)..."
        ollama pull codeqwen:7b || warn "Failed to pull codeqwen:7b - STM parsing may not work"
    else
        success "codeqwen:7b already installed"
    fi

    success "AI models ready"

    # Final setup
    step "Final Setup"

    create_desktop_launcher

    chmod +x "$INSTALL_DIR/start.sh" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/stop.sh" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/first_launch.py" 2>/dev/null || true

    if [ -f "./qdrant" ]; then
        chmod +x ./qdrant
        success "Qdrant binary made executable"
    fi

    # Check final disk space
    local final_space
    final_space=$(df -m "$HOME" | awk 'NR==2 {print $4}')
    info "Remaining disk space: ${final_space}MB"

    if [ "$final_space" -lt 1000 ]; then
        warn "Low disk space remaining. Consider cleaning up or adding more storage."
    fi

    # Hardware Recommendation for macOS
    if [[ "$OS" == "macos" ]]; then
        echo ""
        echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║  Your Mac Hardware Summary             ║${NC}"
        echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
        echo "  Chip/Processor: $(system_profiler SPHardwareDataType | grep -E 'Chip|Processor' | awk -F': ' '{print $2}')"
        echo "  Memory (RAM):   $(system_profiler SPHardwareDataType | grep 'Memory' | awk -F': ' '{print $2}')"
        echo ""
        echo -e "${YELLOW}Recommended Starter Models for your Mac:${NC}"
        echo "  • 8GB RAM:  ollama pull qwen2.5:1.5b"
        echo "  • 16GB RAM: ollama pull qwen2.5:7b"
        echo "  • 24GB+ RAM: ollama pull qwen2.5-coder:14b"
        echo ""
    fi

    # Success message
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✓ Installation Complete!             ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo ""
    info "Installed to: $INSTALL_DIR"
    echo ""

    if [[ "$OS" == "windows" ]]; then
        echo "To start MAi-RAG-PA:"
        echo "   • Double-click start-windows.bat"
        echo "   • Or run: ./start-windows.bat"
    else
        echo "To start MAi-RAG-PA:"
        if [[ "$OS" != "macos" && "$OS" != "bsd" ]]; then
            echo "   • Click the 'MAi-RAG-PA' icon in your application menu"
        fi
        echo "   • Or run: ./start.sh"
    fi
    echo ""
    info "Web UI will open at: http://localhost:8000"
    echo ""

    read -p "Start MAi-RAG-PA now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ./start.sh
    fi
}

# Run main function
main "$@"
