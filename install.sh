#!/bin/bash
# MAi-RAG-PA Universal Installer
# Supports: Linux (Debian/Ubuntu, Fedora/RHEL, Arch), macOS, Windows (WSL2)

set -e

# ============================================================================
# Constants
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

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# ============================================================================
# Utility Functions
# ============================================================================

log() {
    echo -e "${2:-$NC}$1${NC}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE" 2>/dev/null || true
}

error() {
    log "✗ $1" "$RED"
    exit 1
}

warn() {
    log "⚠ $1" "$YELLOW"
}

success() {
    log "✓ $1" "$GREEN"
}

info() {
    log "$1" "$BLUE"
}

# Cleanup function for interrupted installations
cleanup() {
    if [ $? -ne 0 ]; then
        echo ""
        warn "Installation was interrupted or failed."
        warn "Check log file: $LOG_FILE"
        warn "You can resume by running this script again."
    fi
}

trap cleanup EXIT

# ============================================================================
# Version Comparison
# ============================================================================

version_gt() {
    # Returns 0 if $1 > $2
    [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" != "$1" ]
}

version_ge() {
    # Returns 0 if $1 >= $2
    [ "$1" = "$2" ] || version_gt "$1" "$2"
}

# ============================================================================
# Validation Functions
# ============================================================================

check_internet() {
    info "Checking internet connectivity..."
    if ! ping -c 1 -W 5 8.8.8.8 &> /dev/null && \
       ! ping -c 1 -W 5 1.1.1.1 &> /dev/null; then
        error "No internet connection detected. Internet is required for installation."
    fi
    success "Internet connection verified"
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
    if ! command -v python3 &> /dev/null; then
        return 1
    fi
    
    local version
    version=$(python3 --version 2>&1 | awk '{print $2}')
    local major minor
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)
    
    local req_major req_minor
    req_major=$(echo "$MIN_PYTHON_VERSION" | cut -d. -f1)
    req_minor=$(echo "$MIN_PYTHON_VERSION" | cut -d. -f2)
    
    if [ "$major" -lt "$req_major" ] || ([ "$major" -eq "$req_major" ] && [ "$minor" -lt "$req_minor" ]); then
        warn "Python $version found, but $MIN_PYTHON_VERSION+ required"
        return 1
    fi
    
    success "Python $version detected"
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
    
    # Check if ollama is in PATH - check INSTALL_DIR first
    if ! command -v ollama &> /dev/null; then
        if [ -f "$INSTALL_DIR/ollama" ]; then
            export PATH="$INSTALL_DIR:$PATH"
        elif [ -f "$HOME/ollama" ]; then
            export PATH="$HOME:$PATH"
        else
            return 1
        fi
    fi
    
    # Portable version extraction using awk
    local version
    version=$(ollama --version 2>&1 | awk '/version is/ {print $NF}' || echo "0.0")
    
    if ! version_ge "$version" "$MIN_OLLAMA_VERSION"; then
        warn "Ollama $version found, but $MIN_OLLAMA_VERSION+ required"
        return 1
    fi
    
    success "Ollama $version detected"
    return 0
}

check_qdrant_version() {
    info "Checking Qdrant version..."
    
    # Check if qdrant binary exists in project root
    if [ ! -f "$INSTALL_DIR/qdrant" ] && [ ! -f "./qdrant" ]; then
        # Check if qdrant is in PATH
        if ! command -v qdrant &> /dev/null; then
            return 1
        fi
    fi
    
    local qdrant_path
    if [ -f "$INSTALL_DIR/qdrant" ]; then
        qdrant_path="$INSTALL_DIR/qdrant"
    elif [ -f "./qdrant" ]; then
        qdrant_path="./qdrant"
    else
        qdrant_path="qdrant"
    fi
    
    # Portable version extraction using grep -E (extended regex)
    local version
    version=$("$qdrant_path" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "0.0.0")
    
    if ! version_ge "$version" "$MIN_QDRANT_VERSION"; then
        warn "Qdrant $version found, but $MIN_QDRANT_VERSION+ required"
        return 1
    fi
    
    success "Qdrant $version detected"
    return 0
}

# ============================================================================
# Update Prompts
# ============================================================================

prompt_for_update() {
    local component="$1"
    local current_version="$2"
    local required_version="$3"
    
    echo ""
    warn "$component $current_version is installed, but $required_version+ is required."
    read -p "Update $component now? [Y/n]: " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        warn "Skipping $component update. Some features may not work correctly."
        return 1
    fi
    
    return 0
}

# ============================================================================
# OS Detection
# ============================================================================

detect_os() {
    info "Detecting operating system..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            # shellcheck source=/dev/null
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

# ============================================================================
# Dependency Installation
# ============================================================================

install_dependencies() {
    info "Installing system dependencies..."
    
    case $OS in
        "ubuntu"|"debian"|"linuxmint"|"pop"|"elementary"|"zorin")
            info "Installing dependencies for Debian/Ubuntu..."
            sudo apt update || error "Failed to update package lists"
            
            # Portable Node.js version check
            local node_version=0
            if command -v node &> /dev/null; then
                node_version=$(node --version 2>&1 | sed 's/v//' | cut -d. -f1)
            else
                # Check if Node.js is available in repos
                node_version=$(apt-cache policy nodejs 2>/dev/null | grep Candidate | awk '{print $2}' | cut -d. -f1 || echo "0")
            fi
            
            if [ "$node_version" -lt "$MIN_NODE_VERSION" ]; then
                info "Node.js in repository is too old. Installing NodeSource repository..."
                curl -fsSL https://deb.nodesource.com/setup_${MIN_NODE_VERSION}.x | sudo -E bash - || error "Failed to add NodeSource repository"
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
            if ! command -v brew &> /dev/null; then
                warn "Homebrew not found. Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || error "Failed to install Homebrew"
            fi
            brew install python node git || error "Failed to install dependencies"
            ;;
        "windows")
            error "Windows detected. Please use WSL2 for MAi-RAG-PA.\n   Install WSL2: https://docs.microsoft.com/windows/wsl/install"
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
    info "Installing Ollama..."
    
    # Detect architecture
    local arch
    arch=$(uname -m)
    case $arch in
        x86_64) arch="amd64" ;;
        aarch64|arm64) arch="arm64" ;;
        *) error "Unsupported architecture: $arch" ;;
    esac
    
    # Detect OS
    local os_type
    case $OS in
        "ubuntu"|"debian"|"linuxmint"|"pop"|"elementary"|"zorin"|"fedora"|"rhel"|"centos"|"rocky"|"alma"|"arch"|"manjaro"|"endeavouros"|"opensuse"|"sles")
            os_type="linux"
            ;;
        "macos")
            os_type="darwin"
            ;;
        *)
            error "Unsupported OS for Ollama installation: $OS"
            ;;
    esac
    
    # Download Ollama binary
    local ollama_url="https://ollama.com/download/ollama-${os_type}-${arch}"
    local ollama_dest="$INSTALL_DIR/ollama"
    
    info "Downloading Ollama for $os_type-$arch..."
    curl -fsSL "$ollama_url" -o "$ollama_dest" || error "Failed to download Ollama"
    chmod +x "$ollama_dest"
    
    # Verify the binary works
    if ! "$ollama_dest" --version &> /dev/null; then
        error "Downloaded Ollama binary is not executable or corrupted"
    fi
    
    # Backup shell configs before modification
    [ -f ~/.bashrc ] && cp ~/.bashrc ~/.bashrc.backup.$(date +%Y%m%d%H%M%S) 2>/dev/null || true
    [ -f ~/.zshrc ] && cp ~/.zshrc ~/.zshrc.backup.$(date +%Y%m%d%H%M%S) 2>/dev/null || true
    
    # Add to PATH if not already there
    if ! command -v ollama &> /dev/null; then
        info "Adding Ollama to PATH..."
        echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> ~/.bashrc
        echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> ~/.zshrc 2>/dev/null || true
        export PATH="$INSTALL_DIR:$PATH"
    fi
    
    success "Ollama installed to $ollama_dest"
    
    # Start Ollama service
    info "Starting Ollama service..."
    if command -v systemctl &> /dev/null && systemctl list-unit-files 2>/dev/null | grep -q ollama.service; then
        sudo systemctl start ollama || warn "Could not start Ollama via systemctl"
    else
        "$ollama_dest" serve &> /dev/null &
        sleep 2
    fi
    
    # Verify Ollama is running
    if curl -s http://localhost:11434/api/tags &> /dev/null; then
        success "Ollama service started successfully"
    else
        warn "Ollama service may not have started correctly"
    fi
}

# ============================================================================
# Qdrant Installation
# ============================================================================

install_qdrant() {
    info "Installing Qdrant..."
    
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
    
    # Get latest Qdrant version - portable extraction using grep and sed
    local latest_version
    latest_version=$(curl -fsSL https://api.github.com/repos/qdrant/qdrant/releases/latest | grep '"tag_name":' | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/' || echo "v1.17.0")
    
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
# Windows Batch Files
# ============================================================================

create_windows_batch_files() {
    if [[ "$OS" != "windows" ]]; then
        return
    fi
    
    info "Creating Windows batch files..."
    
    cat > start-windows.bat << 'EOF'
@echo off
echo ========================================
echo   MAi-RAG-PA Startup Script (Windows)
echo ========================================
echo.

cd /d "%~dp0"

if not exist "venv" (
    echo ERROR: Virtual environment not found.
    echo Please run first-launch-windows.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

set OLLAMA_URL=http://localhost:11434
set PYTHONPATH=%CD%

echo Starting Qdrant...
if exist "qdrant.exe" (
    start /B qdrant.exe
    timeout /t 3 /nobreak >nul
) else (
    echo WARNING: Qdrant not found. RAG features will be disabled.
)

echo Starting MAi-RAG-PA backend...
start /B python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo ========================================
echo   MAi-RAG-PA is starting...
echo   Web UI: http://localhost:8000
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

timeout /t 3 /nobreak >nul
start http://localhost:8000

cmd /k
EOF

    cat > stop-windows.bat << 'EOF'
@echo off
echo Stopping MAi-RAG-PA...

taskkill /F /IM uvicorn.exe 2>nul
taskkill /F /IM qdrant.exe 2>nul

echo MAi-RAG-PA stopped.
pause
EOF

    chmod +x start-windows.bat stop-windows.bat
    
    success "Windows batch files created"
}

# ============================================================================
# Desktop Launcher
# ============================================================================

create_desktop_launcher() {
    if [[ "$OS" == "macos" || "$OS" == "windows" || "$OS" == "bsd" ]]; then
        return
    fi
    
    info "Creating desktop launcher..."
    
    mkdir -p ~/.local/share/applications
    
    cat > ~/.local/share/applications/MAi-RAG-PA.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=MAi-RAG-PA
Comment=Offline AI Personal Assistant
Exec=$INSTALL_DIR/start.sh
Icon=$INSTALL_DIR/frontend/public/mai-rag-logo.png
Terminal=true
Categories=Utility;
Keywords=AI;Assistant;RAG;LLM;
EOF
    
    chmod +x ~/.local/share/applications/MAi-RAG-PA.desktop
    update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
    
    success "Desktop launcher created"
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
    echo -e "${BLUE}║   MAi-RAG-PA Installation Script       ║${NC}"
    echo -e "${BLUE}║   Offline AI Personal Assistant        ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
    echo ""
    info "Installation log: $LOG_FILE"
    echo ""
    
    check_internet
    check_disk_space
    detect_os
    echo ""
    
    if [ -d "$INSTALL_DIR" ]; then
        warn "MAi-RAG-PA already exists at $INSTALL_DIR"
        
        if [ -d "$INSTALL_DIR/.git" ]; then
            read -p "Update existing installation? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 0
            fi
            cd "$INSTALL_DIR" || error "Failed to change to installation directory"
            info "Pulling latest changes..."
            git pull || error "Failed to pull latest changes"
        else
            error "Directory exists but is not a git repository. Please remove it manually: rm -rf $INSTALL_DIR"
        fi
    else
        info "Downloading MAi-RAG-PA..."
        git clone "$GITHUB_REPO" "$INSTALL_DIR" || error "Failed to clone repository"
        cd "$INSTALL_DIR" || error "Failed to change to installation directory"
    fi
    
    # Verify required files exist after clone
    local required_files=("requirements.txt" "frontend/package.json" "start.sh" "stop.sh" "first_launch.py")
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error "Required file missing: $file"
        fi
    done
    success "All required files present"
    
    echo ""
    install_dependencies
    
    echo ""
    info "Setting up Python environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv || error "Failed to create virtual environment"
    fi
    
    source venv/bin/activate || error "Failed to activate virtual environment"
    
    # Verify activation
    if [ -z "$VIRTUAL_ENV" ]; then
        error "Virtual environment activation failed"
    fi
    
    info "Upgrading pip..."
    pip install --upgrade pip || warn "Failed to upgrade pip"
    
    info "Installing Python dependencies (this may take several minutes)..."
    pip install -r requirements.txt || error "Failed to install Python dependencies"
    
    # Verify critical Python packages
    info "Verifying Python package installation..."
    python -c "import fastapi, uvicorn, qdrant_client, sentence_transformers, spacy" || \
        error "Critical Python packages not installed correctly"
    success "Python packages verified"
    
    echo ""
    info "Downloading SpaCy English model..."
    python -m spacy download en_core_web_sm || warn "Failed to download SpaCy model"
    success "SpaCy model ready"
    
    echo ""
    info "Building frontend (this may take several minutes)..."
    cd frontend || error "Frontend directory not found"
    npm install || error "Failed to install npm dependencies"
    npm run build || error "Failed to build frontend"
    
    # Verify frontend build
    if [ ! -d "dist" ] && [ ! -d "build" ]; then
        error "Frontend build directory not found. Build may have failed."
    fi
    success "Frontend built successfully"
    cd ..
    
    if ! ask_installation_preference; then
        if check_ollama_version; then
            local current_version
            current_version=$(ollama --version 2>&1 | awk '/version is/ {print $NF}' || echo "0.0")
            if ! version_ge "$current_version" "$MIN_OLLAMA_VERSION"; then
                if prompt_for_update "Ollama" "$current_version" "$MIN_OLLAMA_VERSION"; then
                    install_ollama
                fi
            else
                success "Ollama is up to date"
            fi
        else
            install_ollama
        fi
        
        if check_qdrant_version; then
            local current_version
            current_version=$(./qdrant --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "0.0.0")
            if ! version_ge "$current_version" "$MIN_QDRANT_VERSION"; then
                if prompt_for_update "Qdrant" "$current_version" "$MIN_QDRANT_VERSION"; then
                    install_qdrant
                fi
            else
                success "Qdrant is up to date"
            fi
        else
            install_qdrant
        fi
    fi
    
    if [ -z "$(ollama list 2>/dev/null | grep -v NAME)" ]; then
        info "Pulling recommended model (qwen2.5-coder:7b)..."
        ollama pull qwen2.5-coder:7b || warn "Failed to pull model"
    fi
    
    echo ""
    create_desktop_launcher
    create_windows_batch_files
    
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
        if [[ "$OS" == "windows" ]]; then
            ./start-windows.bat
        else
            ./start.sh
        fi
    fi
}

main "$@"
