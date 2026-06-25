#!/bin/bash
# MAi-RAG Universal Installer
# Supports: Linux (Debian/Ubuntu, Fedora/RHEL, Arch), macOS, Windows (WSL2)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   MAi-RAG Installation Script          ║${NC}"
echo -e "${BLUE}║   Offline AI Personal Assistant        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            VER=$VERSION_ID
            echo -e "${GREEN}✓ Detected Linux: $PRETTY_NAME${NC}"
        else
            OS="unknown-linux"
            echo -e "${YELLOW}⚠ Unknown Linux distribution${NC}"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        VER=$(sw_vers -productVersion)
        echo -e "${GREEN}✓ Detected macOS: $VER${NC}"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        OS="windows"
        echo -e "${GREEN}✓ Detected Windows${NC}"
    elif [[ "$OSTYPE" == "freebsd"* || "$OSTYPE" == "openbsd"* || "$OSTYPE" == "netbsd"* ]]; then
        OS="bsd"
        echo -e "${GREEN}✓ Detected BSD: $OSTYPE${NC}"
    else
        OS="unknown"
        echo -e "${RED}✗ Unknown operating system: $OSTYPE${NC}"
        exit 1
    fi
}

# Install dependencies based on OS
install_dependencies() {
    case $OS in
        "ubuntu"|"debian"|"linuxmint"|"pop"|"elementary"|"zorin")
            echo -e "${BLUE}Installing dependencies for Debian/Ubuntu...${NC}"
            sudo apt update
            sudo apt install -y python3 python3-pip python3-venv nodejs npm git curl
            ;;
        "fedora"|"rhel"|"centos"|"rocky"|"alma")
            echo -e "${BLUE}Installing dependencies for Fedora/RHEL...${NC}"
            sudo dnf install -y python3 python3-pip nodejs npm git curl
            ;;
        "arch"|"manjaro"|"endeavouros")
            echo -e "${BLUE}Installing dependencies for Arch Linux...${NC}"
            sudo pacman -S --noconfirm python python-pip nodejs npm git curl
            ;;
        "opensuse"|"sles")
            echo -e "${BLUE}Installing dependencies for openSUSE...${NC}"
            sudo zypper install -y python3 python3-pip nodejs npm git curl
            ;;
        "macos")
            echo -e "${BLUE}Installing dependencies for macOS...${NC}"
            if ! command -v brew &> /dev/null; then
                echo -e "${YELLOW}Installing Homebrew...${NC}"
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            brew install python node git
            ;;
        "windows")
            echo -e "${RED}Windows detected. Please use WSL2 for MAi-RAG.${NC}"
            echo -e "${BLUE}Install WSL2: https://docs.microsoft.com/windows/wsl/install${NC}"
            exit 1
            ;;
        "bsd")
            echo -e "${BLUE}Installing dependencies for BSD...${NC}"
            sudo pkg install -y python3 node npm git curl
            ;;
        *)
            echo -e "${YELLOW}⚠ Unknown OS. Please install manually:${NC}"
            echo "  - Python 3.12+"
            echo "  - Node.js 18+"
            echo "  - Git"
            echo "  - curl"
            read -p "Press Enter to continue if dependencies are installed..."
            ;;
    esac
}

# Install Ollama
install_ollama() {
    if ! command -v ollama &> /dev/null; then
        echo -e "${BLUE}Installing Ollama...${NC}"
        curl -fsSL https://ollama.com/install.sh | sh
        echo -e "${GREEN}✓ Ollama installed${NC}"
    else
        echo -e "${GREEN}✓ Ollama already installed${NC}"
    fi
}

# Create Windows batch files
create_windows_batch_files() {
    if [[ "$OS" == "windows" ]]; then
        echo -e "${BLUE}Creating Windows batch files...${NC}"
        
        # Create start-windows.bat
        cat > start-windows.bat << 'EOF'
@echo off
echo ========================================
echo   MAi-RAG Startup Script (Windows)
echo ========================================
echo.

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv" (
    echo ERROR: Virtual environment not found.
    echo Please run first-launch-windows.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Set environment variables
set OLLAMA_URL=http://localhost:11434
set PYTHONPATH=%CD%

echo Starting Qdrant...
if exist "qdrant.exe" (
    start /B qdrant.exe
    timeout /t 3 /nobreak >nul
) else (
    echo WARNING: Qdrant not found. RAG features will be disabled.
)

echo Starting MAi-RAG backend...
start /B python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo ========================================
echo   MAi-RAG is starting...
echo   Web UI: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

REM Open browser after 3 seconds
timeout /t 3 /nobreak >nul
start http://localhost:8000

REM Keep window open
cmd /k
EOF

        # Create stop-windows.bat
        cat > stop-windows.bat << 'EOF'
@echo off
echo Stopping MAi-RAG...

taskkill /F /IM uvicorn.exe 2>nul
taskkill /F /IM qdrant.exe 2>nul
taskkill /F /FI "WINDOWTITLE eq MAi-RAG*" 2>nul

echo MAi-RAG stopped.
pause
EOF

        # Create first-launch-windows.bat
        cat > first-launch-windows.bat << 'EOF'
@echo off
echo ========================================
echo   MAi-RAG First Launch Setup (Windows)
echo ========================================
echo.

cd /d "%~dp0"

REM Check Python version
python --version 2>nul
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.12+
    pause
    exit /b 1
)

REM Create virtual environment
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt

REM Download SpaCy model
echo Downloading SpaCy English model...
python -m spacy download en_core_web_sm

REM Build frontend
echo Building frontend...
cd frontend
call npm install
call npm run build
cd ..

echo.
echo ========================================
echo   Setup Complete!
echo   Run start-windows.bat to start MAi-RAG
echo ========================================
echo.
pause
EOF

        chmod +x start-windows.bat stop-windows.bat first-launch-windows.bat
        
        echo -e "${GREEN}✓ Windows batch files created${NC}"
        echo -e "${GREEN}  - start-windows.bat (Start MAi-RAG)${NC}"
        echo -e "${GREEN}  - stop-windows.bat (Stop MAi-RAG)${NC}"
        echo -e "${GREEN}  - first-launch-windows.bat (First-time setup)${NC}"
    fi
}

# Main installation
main() {
    detect_os
    echo ""
    
    # Check if already installed
    INSTALL_DIR="$HOME/MAi-RAG"
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}⚠ MAi-RAG already exists at $INSTALL_DIR${NC}"
        read -p "Update existing installation? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        cd "$INSTALL_DIR"
        git pull
    else
        echo -e "${BLUE}📥 Downloading MAi-RAG...${NC}"
        git clone https://github.com/YOUR_USERNAME/MAi-RAG.git "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
    
    echo ""
    install_dependencies
    
    echo ""
    echo -e "${BLUE}🔧 Setting up Python environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Download SpaCy model
    echo ""
    echo -e "${BLUE}📥 Downloading SpaCy English model...${NC}"
    python -m spacy download en_core_web_sm
    echo -e "${GREEN}✓ SpaCy model downloaded${NC}"
    
    echo ""
    echo -e "${BLUE}🎨 Building frontend...${NC}"
    cd frontend
    npm install
    npm run build
    cd ..
    
    echo ""
    install_ollama
    
    # Pull recommended model if none exist
    if [ -z "$(ollama list 2>/dev/null | grep -v NAME)" ]; then
        echo -e "${BLUE}📥 Pulling recommended model (qwen2.5-coder:7b)...${NC}"
        ollama pull qwen2.5-coder:7b
    fi
    
    echo ""
    echo -e "${BLUE}🔧 Creating desktop launcher...${NC}"
    
    # Create desktop file (Linux only)
    if [[ "$OS" != "macos" && "$OS" != "windows" && "$OS" != "bsd" ]]; then
        mkdir -p ~/.local/share/applications
        cat > ~/.local/share/applications/mai-rag.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=MAi-RAG
Comment=Offline AI Personal Assistant
Exec=$INSTALL_DIR/start.sh
Icon=$INSTALL_DIR/frontend/public/mai-rag-logo.png
Terminal=true
Categories=Utility;
Keywords=AI;Assistant;RAG;LLM;
EOF
        chmod +x ~/.local/share/applications/mai-rag.desktop
        
        # Update desktop database
        update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
        
        echo -e "${GREEN}✓ Desktop launcher created${NC}"
        echo -e "${GREEN}  You can now find MAi-RAG in your application menu${NC}"
    fi
    
    # Create Windows batch files
    create_windows_batch_files
    
    chmod +x "$INSTALL_DIR/start.sh"
    chmod +x "$INSTALL_DIR/stop.sh"
    chmod +x "$INSTALL_DIR/first_launch.py"
    
    if [ -f "./qdrant" ]; then
        chmod +x ./qdrant
        echo -e "${GREEN}✓ Qdrant binary made executable${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✅ Installation Complete!            ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "📍 Installed to: ${BLUE}$INSTALL_DIR${NC}"
    echo ""
    
    if [[ "$OS" == "windows" ]]; then
        echo -e "🚀 To start MAi-RAG:"
        echo -e "   • Double-click ${BLUE}start-windows.bat${NC}"
        echo -e "   • Or run: ${BLUE}./start-windows.bat${NC}"
        echo ""
        echo -e "💡 To create a desktop shortcut:"
        echo -e "   1. Right-click on start-windows.bat"
        echo -e "   2. Select 'Send to' → 'Desktop (create shortcut)'"
        echo -e "   3. Right-click the shortcut → Properties"
        echo -e "   4. Click 'Change Icon' and select mai-rag-logo.png"
    else
        echo -e "🚀 To start MAi-RAG:"
        if [[ "$OS" != "macos" && "$OS" != "bsd" ]]; then
            echo -e "   • Click the 'MAi-RAG' icon in your application menu"
        fi
        echo -e "   • Or run: ${BLUE}./start.sh${NC}"
    fi
    echo ""
    echo -e "🌐 Web UI will open at: ${BLUE}http://localhost:8000${NC}"
    echo ""
    
    # Ask if user wants to start now
    read -p "Start MAi-RAG now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [[ "$OS" == "windows" ]]; then
            ./start-windows.bat
        else
            ./start.sh
        fi
    fi
}

main
