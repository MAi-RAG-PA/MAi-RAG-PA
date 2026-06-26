<p align="center">
  <img src="MAi-RAG.png" alt="MAi-RAG-PA Personal Assistant" width="150">
</p>

<h1 align="center">MAi-RAG-PA</h1>
<h3 align="center">Your Offline Privacy, Self-Healing, Personal Assistant</h3>

<p align="center">
  <strong>MAi-RAG-PA (Memory-Augmented Intelligence with Retrieval-Augmented Generation - Personal Assistant)</strong> is a privacy-focused personal AI assistant that runs entirely on your local machine. No cloud. No subscriptions. No data leaving your computer.
</p>

<p align="center">
  <a href="README.md">Home</a> •
  <a href="MAi-README.md">Full Documentation</a> •
  <a href="MAi-INSTALLATION.md">Installation</a> •
  <a href="MAi-OLLAMA-MODELS.md">Models</a> •
  <a href="MAi-SSH-SETUP.md">SSH & LAN</a> •
  <a href="MAi-LICENCE-LEGAL-NOTICE.md">License</a>
</p>

<p align="center">
  <strong>Version 1.0 | Effective Date: June 2026</strong><br />
  <strong>Copyright © 2026 MAi-RAG-PA. All Rights Reserved.</strong>
</p>

<h3 align="center">MAi-RAG-PA Installation Guide</h3>

<p align="center">Complete installation instructions for all supported platforms.</p>

-----------------------------------------------------------------------------------

## Prerequisites (Install BEFORE MAi-RAG-PA)

 **IMPORTANT**: The following software must be installed and running BEFORE installing MAi-RAG-PA:

### Required Prerequisites

   1. **Ollama** (v0.30 or higher)
   - Download: https://ollama.com/download
   - Must be running: `ollama serve`
   - Verify: `curl http://localhost:11434/api/tags`

   2. **Qdrant** (v1.17 or higher)
   - Download: https://github.com/qdrant/qdrant/releases
   - Must be running: `./qdrant`
   - Verify: `curl http://localhost:6333/`

   3. **Python** (3.12 or higher)
   - Download: https://www.python.org/downloads/
   - Verify: `python3 --version`

   4. **Node.js** (18 or higher)
   - Download: https://nodejs.org/
   - Verify: `node --version`

   5. **Git** (any recent version)
   - Download: https://git-scm.com/downloads
   - Verify: `git --version`

### Installation Order

   # 1. Install prerequisites (see links above)

   # 2. Start Ollama:

    ```bash
    ollama serve &
    ```

   # 3. Start Qdrant:

    ```bash
    ./qdrant &
    ```

   # 4. Install MAi-RAG-PA (see methods below)

### Operating System Support

#### Fully Supported (Tested)

   **Linux Distributions:**
   - **Debian-based**: Ubuntu 22.04+, Debian 12+, Linux Mint 21+, Rhino Linux, Pop!_OS 22.04+, Elementary OS 7+, Zorin OS 17+
   - **RPM-based**: Fedora 38+, RHEL 9+, CentOS Stream 9+, Rocky Linux 9+, AlmaLinux 9+
   - **Arch-based**: Arch Linux, Manjaro 23+, EndeavourOS
   - **SUSE-based**: openSUSE Leap 15.5+, openSUSE Tumbleweed, SLES 15+

   **macOS:**
   - macOS 12 (Monterey) and later
   - macOS 13 (Ventura)
   - macOS 14 (Sonoma)
   - macOS 15 (Sequoia)
   - Apple Silicon (M1/M2/M3/M4) fully supported

   **Windows (via WSL2):**
   - Windows 10 (version 2004+, Build 19041+)
   - Windows 11 (all versions)
   - Requires WSL2 with Ubuntu 22.04+

#### Partially Supported (May Require Manual Setup)

   **BSD Variants:**
   - FreeBSD 13+ (limited Ollama support)
   - OpenBSD 7.3+ (limited Ollama support)
   - Other Unix-like systems may require manual dependency installation

   **Other Systems:**
   - Haiku (R1/beta4+) - Limited, requires manual compilation
   - OpenIndiana/illumos - Limited support
   - Solaris 11+ - Not officially supported

#### Not Supported

   - Windows native (without WSL2)
   - Windows 3.1 / 98 / XP / 2000/ Vista / 7 / 8 / 8.1
   - macOS 11 (Big Sur) and earlier
   - Linux distributions older than listed above
   - 32-bit systems (requires 64-bit)

### Hardware Requirements

| Component 	 | Minimum 						| Recommended 			| Notes 					|
|----------------|------------------------------------------------------|-------------------------------|-----------------------------------------------|
| **RAM** 	 | 12 GB   						| 16 GB+ 			| 16GB+ required for 14B+ models		|
| **Disk Space** | 15 GB   						| 30 GB+ 			| Plus model sizes (7B ≈ 4GB each)		|
| **CPU** 	 | Intel Core i3 / AMD Ryzen 3 				| Intel Core i5+ / AMD Ryzen 5+ | 64-bit processor (x86_64 or ARM64)		|
| **GPU** 	 | Optional 						| NVIDIA with 8GB+ VRAM 	| For faster inference with GPU-enabled Ollama	|
| **Browsers** 	 | Chrome 90+ / Edge 90+ / Firefox 88+ / Safari 14+	| Vivaldi, Opera, Safari	| Latest versions For best experience		|


### Software Requirements

   **Prerequisites (MUST be installed BEFORE MAi-RAG-PA):**
   - **Ollama**: v0.30 or higher - Download from https://ollama.com/download
   - **Qdrant**: v1.17 or higher - Download from https://github.com/qdrant/qdrant/releases
   - **Python**: 3.12 or higher - Download from https://www.python.org/downloads/
   - **Node.js**: 18 or higher - Download from https://nodejs.org/
   - **Git**: Any recent version - Download from https://git-scm.com/downloads

   **Installation Order:**
   1. Install all prerequisites listed above
   2. Start Ollama: `ollama serve`
   3. Start Qdrant: `./qdrant`
   4. Install MAi-RAG-PA using one of the methods below

   **Python packages** (installed automatically):
   - Core: FastAPI, Uvicorn, Qdrant client, Sentence Transformers, SpaCy
   - Document processing: python-docx, python-pptx, openpyxl, striprtf, odfpy, pylatexenc, docutils
   - PDF processing: pdfplumber, PyMuPDF
   - EPUB processing: ebooklib
   - Voice recognition: faster-whisper, vosk
   - Web: BeautifulSoup, frontmatter

### All document processing is handled automatically - no additional system packages required.

   **Document Format Support:**
    MAi-RAG-PA supports 17 document formats for knowledge base ingestion:
   - PDF, EPUB, DOCX, TXT, RTF, ODT
   - HTML, HTM, MD (Markdown)
   - CSV, TSV, JSON, XML
   - PPTX, XLSX
   - TEX (LaTeX), RST (reStructuredText)

### Network Requirements

   - **Initial Setup**: Internet connection required for downloading dependencies
   - **Daily Use**: No internet required (fully offline operation)

-----------------------------------------------------------------------------------

## Installation Methods


### Method 1: One-Line Quick Installer (Recommended for Non-Technical Users)

   **Linux/macOS:**

    ```bash
    curl -fsSL https://github.com/MAi-RAG-PA/MAi-RAG-PA/raw/main/install.sh | bash
    ```

   **This automatically:**
   - Detects your operating system
   - Sets up Python virtual environment
   - Installs Python dependencies
   - Builds the React frontend
   - Pulls a recommended AI model (qwen2.5-coder:7b)
   - Creates desktop launcher (Linux)
   - Optionally starts MAi-RAG-PA

-----------------------------------------------------------------------------------

### Method 2: Manual Download

   1. Go to <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/releases">GitHub Releases</a>
   2. Download the latest .zip file
   3. Extract to your home directory (~/MAi-RAG-PA)
   4. Open terminal and navigate to the directory:

    ```bash
    cd ~/MAi-RAG-PA
    ```
    5. Run the installer:

    ```bash
    ./install.sh
    ```

-----------------------------------------------------------------------------------

### Method 3: Clone from GitHub

# Clone the repository

    ```bash
    git clone https://github.com/MAi-RAG-PA/MAi-RAG-PA.git ~/MAi-RAG-PA
    cd ~/MAi-RAG-PA
    ```

# Run the installer

    ```bash
    ./install.sh
    ```

-----------------------------------------------------------------------------------

### Method 4: Manual Installation (Advanced)

   If you prefer to install dependencies manually:

   **Step 1: Install System Dependencies**

   - Linux (Debian/Ubuntu):

    ```bash
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv nodejs npm git curl
    ```

   - Linux (Fedora/RHEL):

    ```bash
    sudo dnf install -y python3 python3-pip nodejs npm git curl
    ```

   - macOS:

    ```bash
    brew install python node git
    ```

   **Step 2: Clone Repository**

    ```bash
    git clone https://github.com/MAi-RAG-PA/MAi-RAG-PA.git ~/MAi-RAG-PA
    cd ~/MAi-RAG-PA
    ```

   **Step 3: Setup Python Environment**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

   **Step 4: Build Frontend**
 
    ```bash
    cd frontend
    npm install
    npm run build
    cd ..
    ```

   **Step 5: First Time Start MAi-RAG-PA**

    ```bash
    cd ~/MAi-RAG-PA
    python3 first_launch.py
    ```

   **The first_launch.py script:**
   - Creates virtual environment if missing
   - Installs Python dependencies
   - Builds frontend
   - Starts all services

   **When to use first_launch.py:**
   - First-time installation
   - After deleting venv/ directory by mistake
   - When dependencies are missing
   - If start.sh fails due to missing dependencies

-----------------------------------------------------------------------------------

## Starting MAi-RAG-PA

### MAi-RAG-PA provides 3 ways to start the application, depending on your needs:

   **Method 1: Desktop Launcher Icon (Linux - Recommended for Daily Use)**

   **After installation, MAi-RAG-PA appears in your application menu:
   1. Search for "MAi-RAG-PA" in your application launcher
   2. Click the MAi-RAG-PA icon
   3. Your default browser opens automatically to http://localhost:8000

   **What happens:**
   - Terminal window opens with colored status output
   - All services start automatically (Qdrant, backend)
   - Browser opens when ready
   - Press Ctrl+C in terminal to stop all services

   **If icon doesn't appear:**

# Update desktop database

    ```bash
    update-desktop-database ~/.local/share/applications/
    ```

# Verify .desktop file exists

    ```bash
    ls ~/.local/share/applications/MAi-RAG-PA.desktop
    ```

   **Method 2: Terminal (Recommended for Daily Use)**

    ```bash
    cd ~/MAi-RAG-PA
    ./start.sh
    ```

   **The start.sh script:**
   - Starts Qdrant vector database
   - Starts the watchdog process
   - Launches FastAPI backend on http://localhost:8000
   - Opens your default browser

   **Method 3: Advanced - Running Without Scripts**

   **If you need to start components manually (for debugging):**

# 1. Change directory:

    ```bash
    cd ~/MAi-RAG-PA
    ```

# 2. Start Qdrant:

    ```bash
    ./qdrant &
    ```

# 3. Start watchdog (optional):

    ```bash
    python3 watchdog.py &
    ```

# 4. Activate virtual environment:

    ```bash
    source venv/bin/activate
    ```

# 5. Set environment variables:

    ```bash
    export OLLAMA_URL="http://localhost:11434"
    export PYTHONPATH="$(pwd)"
    ```

# 6. Start backend:

    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

-----------------------------------------------------------------------------------

## Platform-Specific Instructions

 ### macOS Users

   **Method 1: Terminal**

    ```bash
    cd ~/MAi-RAG-PA
    ./start.sh
    ```

   **Method 2: Create Application Shortcut (Optional)**

# Create a simple app bundle

    ```bash
    mkdir -p ~/Applications/MAi-RAG-PA.app/Contents/MacOS
    cat > ~/Applications/MAi-RAG-PA.app/Contents/MacOS/MAi-RAG-PA << EOF
    #!/bin/bash
    cd ~/MAi-RAG-PA
    ./start.sh
    EOF
    chmod +x ~/Applications/MAi-RAG-PA.app/Contents/MacOS/MAi-RAG-PA
    ```
  **Now you can launch MAi-RAG-PA from ~/Applications or Spotlight.**

-----------------------------------------------------------------------------------

### Windows Users (WSL2)

   ** Method 1: Batch File (Recommended)**
    After installation, Windows-specific batch files are created:

   **Start MAi-RAG-PA:**

    ```cmd
    cd %USERPROFILE%\MAi-RAG-PA
    start-windows.bat
    ```

   **What it does:**
   - Activates Python virtual environment
   - Starts Qdrant vector database
   - Starts FastAPI backend
   - Opens browser automatically

### Stop MAi-RAG-PA:

    ```cmd
    stop-windows.bat
    ```

   **Method 2: Create Desktop Shortcut**
   1. Navigate to your MAi-RAG-PA folder in File Explorer
   2. Right-click start-windows.bat
   3. Select "Send to" → "Desktop (create shortcut)"
   4. Right-click the new shortcut → Properties
   5. Click "Change Icon"
   6. Browse to frontend\public\mai-rag-logo.png
   7. Click OK to apply

   **Now you can double-click the desktop icon to start MAi-RAG-PA.**

   **Method 3: WSL Terminal**

    ```bash
    cd ~/MAi-RAG-PA
    ./start.sh
    ```

  **Note: Windows users running through WSL2 have full Linux compatibility. All Linux instructions apply.**

-----------------------------------------------------------------------------------

### Stopping MAi-RAG-PA

   **Method 1: Web UI**

    Click "Stop MAi-RAG-PA" button in the header in the WebUI
  
   **Method 2: Linux/macOS Terminal**

    ```bash
    cd ~/MAi-RAG-PA
    ./stop.sh
    ```

   **Method 3: Windows**

    ```cmd
    stop-windows.bat
    ```

   **Method 4: Manual Process Kill**

   **Linux/macOS Manual:**

    ```bash
    pkill -f "uvicorn app.main:app"
    pkill -f "watchdog.py"
    pkill -f "./qdrant"
    pkill -f "ollama"
    ```

   **Windows:**

    ```cmd
    taskkill /F /IM uvicorn.exe
    taskkill /F /IM qdrant.exe
    ```

   **Method 5: Ctrl+C**
   
    If you started MAi-RAG-PA with start.sh in the foreground, press Ctrl+C to stop all services gracefully.

-----------------------------------------------------------------------------------

### Updating MAi-RAG-PA

    ```bash
    cd ~/MAi-RAG-PA
    ```

# Pull latest changes:

    ```bash
    git pull
    ```

# Activate virtual environment:

    ```bash
    source venv/bin/activate
    ```

# Update Python dependencies:

    ```bash
    pip install -r requirements.txt
    ```

# Rebuild frontend:

    ```bash
    cd frontend
    npm install
    npm run build
    cd ..
    ```

# Restart MAi-RAG-PA:

    ```bash
    ./stop.sh
    ./start.sh
    ```

-----------------------------------------------------------------------------------

### Accessing MAi-RAG-PA from Other Devices

   **Local Network Access (Same WiFi Network)**

    1. Find your computer's IP address that MAi-RAG-PA is running on:

   **Linux/macOS:**

    ```bash
    ip addr show | grep "inet " | grep -v 127.0.0.1
    ```

   **Windows (WSL2):**

    ```cmd
    hostname -I
    ```

   Look for something like 192.168.1.100

    2. On your tablet/phone (connected to same WiFi network):
    - Open browser
    - Navigate to http://192.168.1.XX:8000 (replace XX with your computer's IP address suffix that MAi-RAG-PA is running on)

    **That's it! No additional configuration needed.**

-----------------------------------------------------------------------------------

### SSH Tunnel (Remote Access)

### For secure remote access or accessing from outside your network:

   **Step 1: Install SSH Client on Mobile Device**

   **iOS:**
    Termius
    Blink Shell

   **Android:**
    JuiceSSH
    Termius

   **Step 2: Create SSH Tunnel**

   **From your mobile device's SSH client:**

    ```bash
    ssh -L 8000:localhost:8000 username@192.168.1.XX
    ```

   **Replace:**
   - username with your computer's username
   - 192.168.1.XX with your computer's IP address

   **Step 3: Access in Browser**
   - Open browser on tablet/phone
   - Navigate to http://localhost:8000

     See: <a href="MAi-SSH-SETUP.md">SSH & LAN</a> for more detailed instructions.

-----------------------------------------------------------------------------------


### Troubleshooting

   **Installation Issues**

   **Issue: "Command not found: python3"**
# Install Python

    ```bash
    sudo apt install python3 python3-pip python3-venv  # Debian/Ubuntu
    sudo dnf install python3 python3-pip               # Fedora/RHEL
    brew install python                                # macOS
    ```

   **Issue: "Command not found: node"**
# Install Node.js

    ```bash
    sudo apt install nodejs npm                        # Debian/Ubuntu
    sudo dnf install nodejs npm                        # Fedora/RHEL
    brew install node                                  # macOS
    ```
    
   **Issue: "Permission denied" on start.sh**

    ```bash
    cd ~/MAi-RAG-PA
    chmod +x start.sh stop.sh install.sh
    ```

   **Issue: Virtual environment creation fails**
# Ensure python3-venv is installed

    ```bash
    sudo apt install python3-venv                      # Debian/Ubuntu
    sudo dnf install python3-virtualenv                # Fedora/RHEL
    ```


   **Issue: npm install fails**
# Clear npm cache and retry

    ```bash
    cd frontend
    rm -rf node_modules package-lock.json
    npm install
    ```

-----------------------------------------------------------------------------------

### Runtime Issues

   **Issue: Desktop icon doesn't appear in application menu**

# Update desktop database:

    ```bash
    update-desktop-database ~/.local/share/applications/
    ```

# Verify .desktop file is valid:

    ```bash
    desktop-file-validate ~/.local/share/applications/MAi-RAG-PA.desktop
    ```

   **Issue: Desktop icon image doesn't show**

# Check icon file exists:

    ```bash
    ls -lh ~/MAi-RAG-PA/frontend/public/mai-rag-logo.png
    ```

# Verify Icon path in .desktop file is correct:

    ```bash
    grep "^Icon=" ~/.local/share/applications/MAi-RAG-PA.desktop
    ```

# Should be absolute path like:
# Icon=/home/username/MAi-RAG-PA/frontend/public/mai-rag-logo.png


   **Issue: start.sh says "Ollama is not running"**

# Start Ollama:

    ```bash
    ollama serve &
    ```

# Verify it's running:

    ```bash
    curl http://localhost:11434/api/tags
    ```

# Then try start.sh again

    ```bash
    ./start.sh
    ```

   **Issue: MAi-RAG-PA won't start**

# Check the following:

   **1. Is Ollama running?**

    ```bash
    curl http://localhost:11434/api/tags
    ```
    If this fails, start Ollama: 

    ```bash
    ollama serve
    ```

   **2. Verify Python version:**

    ```bash
    python3 --version
    ```
    (Must be 3.12 or higher)


   **3. Check Node.js version:**

    ```bash
    node --version
    ```
    (Must be 18 or higher)


   **4. Run System Doctor from Assistant Settings in the MAi-RAG-PA WebUI**


   **Issue: start.sh says "Virtual environment not found"**

# Run first_launch.py to create it:

    ```bash
    python3 first_launch.py
    ```

# OR create it manually:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

   **Issue: Qdrant fails to start**

# Check if Qdrant binary exists:

    ```bash
    ls -lh ./qdrant
    ```

# Make it executable:

    ```bash
    chmod +x ./qdrant
    ```

# Check logs:

    ```bash
    cat /tmp/qdrant.log
    ```

# Try starting manually:

    ```bash
    ./qdrant &
    ```

   **Issue: Backend won't start after git pull**

# Dependencies may have changed:

    ```bash
    python3 first_launch.py
    ```

# OR manually update:

    ```bash
    source venv/bin/activate
    pip install -r requirements.txt
    ```

   **Issue: Port 8000 already in use**

# Find what's using the port:

    ```bash
    lsof -i :8000
    ```

# Kill the process:

    ```bash
    pkill -f "uvicorn app.main:app"
    ```

# Wait a moment, then try again:

    ```bash
    sleep 2
    ./start.sh
    ```

   **Issue: Slow response times**

   - Use smaller model (7B instead of 14B or 32B)
   - Close RAM-intensive applications
   - Reduce context window size in Ollama
   - Check system resources in the Chat Console monitor

   **Issue: Models not appearing in dropdown**

   1. Verify Ollama is running:

    ```bash
    curl http://localhost:11434/api/tags
    ```

   2. Pull a model:

    ```bash
    ollama pull qwen2.5-coder:7b
    ```

   3. Restart MAi-RAG-PA:

    ```bash
    ./stop.sh && ./start.sh
    ```

   **Issue: Ollama connection refused**
# Start Ollama:

    ```bash
    ollama serve &
    ```

# Verify it's running:

    ```bash
    curl http://localhost:11434/api/tags
    ```

   **Issue: Qdrant not available**

# Start Qdrant manually:

    ```bash
    cd ~/MAi-RAG-PA
    ./qdrant &
    ```

# Verify it's running

    ```bash
    curl http://localhost:6333/
    ```

   **Issue: Voice transcription fails**

   1. Check microphone permissions in browser
   2. Ensure Vosk fallback model exists:

    ```bash
    ls ~/MAi-RAG-PA/models/vosk-model-small-en-us-0.15/
    ```

   3. Check browser console for errors (F12 → Console tab)

   **Issue: File not saved to workspace**

   1. Check workspace directory exists and is writable:

    ```bash
    ls -ld ~/MAi-RAG-PA/workspace/
    ```

   2. Use [FILE] prefix for explicit file creation:
   [FILE] Create test.txt with content: Hello World

   3. Check browser console for errors (F12 → Console tab)

   **Issue: Verification rejects valid content**
   Review app/agents/verifier.py rules and adjust heuristics for your use case.

### System Doctor
   
   **For persistent issues, use the built-in System Doctor:**
   1. Click Assistant Settings in the navigation menu
   2. Click System Doctor button
   3. Review the diagnostic report
   4. Apply suggested fixes
   5. Check the generated JSON report for detailed information

   **The System Doctor checks:**
   - Ollama connectivity and model count
   - Qdrant vector database status
   - SQLite database integrity
   - Workspace directory permissions
   - Frontend build existence
   - Disk space availability
   - Python dependency verification
    
### Uninstalling MAi-RAG-PA

   **To completely remove MAi-RAG-PA:**

# Stop all services

    ```bash
    cd ~/MAi-RAG-PA
    ./stop.sh
    ```

# Remove MAi-RAG-PA directory:

    ```bash
    cd ~
    rm -rf ~/MAi-RAG-PA
    ```

# Optional: Remove Ollama:

    ```bash
    sudo rm /usr/local/bin/ollama
    rm -rf ~/.ollama
    ```

# Optional: Remove Ollama models:

    ```bash
    rm -rf ~/.ollama/models
    ```

-----------------------------------------------------------------------------------

### Getting Help

   **If you encounter issues not covered in this guide:**

   1. Check the System Doctor - Run diagnostics from Assistant Settings
   2. Review logs - Check terminal output for error messages
   3. Search existing issues - GitHub Issues
   4. Create new issue - Provide detailed information about your problem
   5. Join discussions - GitHub Discussions

   **Documentation:**

   <a href="MAi-README.md">Full Documentation</a> Complete feature overview and usage guide<br />
   <a href="MAi-INSTALLATION.md">Installation</a> Step-by-step setup for all platforms, System requirements, starting/stopping<br />
   <a href="MAi-OLLAMA-MODELS.md">Model Recommendations</a> Choosing the right AI model for your needs<br />
   <a href="MAi-SSH-SETUP.md">SSH & LAN</a> Access the system remotely from other devices via SSH or on the same network<br />
   <a href="MAi-LICENCE-LEGAL-NOTICE.md">Terms of use and commercial licensing</a>

   **Support & Contact:**

   **Issues**: <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/issues">GitHub Issues</a>
   **Discussions**: <a href="https://github.com/MAi-RAG-PA/MAi-RAG-PA/discussions">GitHub Discussions</a>
   **Email**: MAi-RAG-PA@proton.me

-----------------------------------------------------------------------------------

## 💝 Support MAi-RAG-PA

MAi-RAG-PA is a labor of love developed over thousands of hours. If this software brings value to your life or work, **donations are deeply appreciated** and help fund continued development.

MAi-RAG-PA is free for personal use. If you find it valuable, donations are greatly appreciated:

- **PayPal**: <a href="https://www.paypal.com/ncp/payment/GSTCK29MSGCH4">Grateful for your Contributions</a>

Every donation helps keep MAi-RAG-PA free and continuously improving.

**Commercial Licensing**: For business deployments or enterprise support, please contact: MAi-RAG-PA@proton.me

-----------------------------------------------------------------------------------

<p align="center">
  <strong>MAi-RAG-PA — Your Personal Assistant, Your Data, Your Machine, No Subscriptions!</strong>
</p>

<p align="center">
  Version 1.0.0 | Released June 2026
</p>