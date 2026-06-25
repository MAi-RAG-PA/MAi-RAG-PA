# MAi-RAG Installation Guide

Complete installation instructions for all supported platforms.

-----------------------------------------------------------------------------------

## Prerequisites & System Requirements

### Operating System Support

#### ✅ Fully Supported (Tested)

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

#### ⚠️ Partially Supported (May Require Manual Setup)

**BSD Variants:**
- FreeBSD 13+ (limited Ollama support)
- OpenBSD 7.3+ (limited Ollama support)
- Other Unix-like systems may require manual dependency installation

**Other Systems:**
- Haiku (R1/beta4+) - Limited, requires manual compilation
- OpenIndiana/illumos - Limited support
- Solaris 11+ - Not officially supported

#### ❌ Not Supported

- Windows native (without WSL2)
- Windows 3.1 / 98 / XP / 2000/ Vista / 7 / 8 / 8.1
- macOS 11 (Big Sur) and earlier
- Linux distributions older than listed above
- 32-bit systems (requires 64-bit)

### Hardware Requirements

| Component 	 | Minimum 			| Recommended 			| Notes 
|----------------|------------------------------|-------------------------------|-------------------------------------------
| **RAM** 	 | 12 GB   			| 16 GB+ 			| 16GB+ required for 14B+ models
| **Disk Space** | 15 GB   			| 30 GB+ 			| Plus model sizes (7B ≈ 4GB each)
| **CPU** 	 | Intel Core i3 / AMD Ryzen 3 	| Intel Core i5+ / AMD Ryzen 5+ | 64-bit processor (x86_64 or ARM64)
| **GPU** 	 | Optional 			| NVIDIA with 8GB+ VRAM 	| For faster inference with GPU-enabled Ollama
| **Browsers** 	 | Chrome 90+ / Edge 90+ / Firefox 88+ / Safari 14+ 		| Latest versions For best experience
----------------------------------------------------------------------------------------------------------------------------

### Software Requirements

- **Python**: 3.12 or higher
- **Node.js**: 18 or higher
- **Git**: Any recent version
- **Ollama**: Latest version (installed during setup)
- **Qdrant**: Included with MAi-RAG (no separate installation needed)
    To download & update/replace to a recent version of the single Binary file Go to: https://github.com/qdrant/qdrant/releases/

**Python packages** (installed automatically):
- Core: FastAPI, Uvicorn, Qdrant client, Sentence Transformers, SpaCy
- Document processing: python-docx, python-pptx, openpyxl, striprtf, odfpy, pylatexenc, docutils
- PDF processing: pdfplumber, PyMuPDF
- EPUB processing: ebooklib
- Voice recognition: faster-whisper, vosk
- Web: BeautifulSoup, frontmatter

### All document processing is handled automatically - no additional system packages required.

**Document Format Support:**
MAi-RAG supports 17 document formats for knowledge base ingestion:
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

curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/MAi-RAG/main/install.sh | bash

This automatically:

    ✅ Detects your operating system
    ✅ Installs all dependencies (Python, Node.js, Git)
    ✅ Downloads MAi-RAG to ~/MAi-RAG
    ✅ Sets up Python virtual environment
    ✅ Installs Python dependencies
    ✅ Builds the React frontend
    ✅ Installs Ollama if needed
    ✅ Pulls a recommended AI model (qwen2.5-coder:7b)
    ✅ Creates desktop launcher (Linux)
    ✅ Optionally starts MAi-RAG


### Method 2: Manual Download

    1. Go to GitHub Releases
    2. Download the latest .zip file
    3. Extract to your home directory (~/MAi-RAG)
    4. Open terminal and navigate to the directory:

       cd ~/MAi-RAG

    5. Run the installer:

       ./install.sh


### Method 3: Clone from GitHub

   # Clone the repository
     git clone https://github.com/YOUR_USERNAME/MAi-RAG.git ~/MAi-RAG
     cd ~/MAi-RAG

   # Run the installer
     ./install.sh


### Method 4: Manual Installation (Advanced)

   If you prefer to install dependencies manually:

   **Step 1: Install System Dependencies**

   - Linux (Debian/Ubuntu):
     sudo apt update
     sudo apt install -y python3 python3-pip python3-venv nodejs npm git curl

   - Linux (Fedora/RHEL):
     sudo dnf install -y python3 python3-pip nodejs npm git curl

   - macOS:
     brew install python node git


   **Step 2: Clone Repository**

   git clone https://github.com/YOUR_USERNAME/MAi-RAG.git ~/MAi-RAG
   cd ~/MAi-RAG

   **Step 3: Setup Python Environment**

   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt


   **Step 4: Build Frontend**
  
   cd frontend
   npm install
   npm run build
   cd ..


   **Step 5: Install Ollama**

   Linux:
   curl -fsSL https://ollama.com/install.sh | sh

   macOS:
   brew install ollama

   Windows (WSL2):
   curl -fsSL https://ollama.com/install.sh | sh


   **Step 6: Pull Your First Model**

   # Start Ollama in background
     ollama serve &

   # Pull recommended model or other model that suits your system specifications
     ollama pull qwen2.5-coder:7b

   See MAi-OLLAMA-MODELS.md for the full list of recommended models.


  **Step 7: First Time Start MAi-RAG**
   
  **Important Step, First-time setup:**

  **Linux/macOS:**
    cd ~/MAi-RAG
    python3 first_launch.py

  **Windows (Native - if not using WSL2):**
    cd %USERPROFILE%\MAi-RAG
    first-launch-windows.bat

   #The first_launch.py is for First-time setup - creates venv, installs dependencies, handles automated installation

   What it does:

    Creates virtual environment if missing
    Installs Python dependencies
    Builds frontend
    Starts all services

   When to use:

    First-time installation
    After deleting venv/ directory
    When dependencies are missing
    If start.sh fails due to missing dependencies


-----------------------------------------------------------------------------------


## Starting MAi-RAG

MAi-RAG provides 3 ways to start the application, depending on your needs:

  **Method 1: Desktop Launcher Icon (Linux - Recommended for Daily Use)**

  After installation, MAi-RAG appears in your application menu:

  1. Search for "MAi-RAG" in your application launcher
  2. Click the MAi-RAG icon
  3. Your default browser opens automatically to http://localhost:8000

  **What happens:**
   - Terminal window opens with colored status output
   - All services start automatically (Qdrant, backend)
   - Browser opens when ready
   - Press Ctrl+C in terminal to stop all services

  **If icon doesn't appear:**

   # Update desktop database
   update-desktop-database ~/.local/share/applications/

   # Verify .desktop file exists
   ls ~/.local/share/applications/MAi-RAG.desktop

  **Method 2: Terminal (Recommended for Daily Use)**

    cd ~/MAi-RAG
    ./start.sh

    The start.sh script:

    - Starts Qdrant vector database
    - Starts the watchdog process
    - Launches FastAPI backend on http://localhost:8000
    - Opens your default browser


  **Method 3: Advanced: Running Without Scripts**
    If you need to start components manually (for debugging):

    # 1. Change directory
    cd ~/MAi-RAG

    # 2. Start Qdrant
    ./qdrant &

    # 3. Start watchdog (optional)
    python3 watchdog.py &

    # 4. Activate virtual environment
    source venv/bin/activate

    # 5. Set environment variables
    export OLLAMA_URL="http://localhost:11434"
    export PYTHONPATH="$(pwd)"

    # 6. Start backend
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload


### macOS Users

  **Method 1: Terminal**
  cd ~/MAi-RAG
  ./start.sh

  **Method 2: Create Application Shortcut (Optional)**
    # Create a simple app bundle
    mkdir -p ~/Applications/MAi-RAG.app/Contents/MacOS
    cat > ~/Applications/MAi-RAG.app/Contents/MacOS/MAi-RAG << EOF
    #!/bin/bash
    cd ~/MAi-RAG
    ./start.sh
    EOF
    chmod +x ~/Applications/MAi-RAG.app/Contents/MacOS/MAi-RAG

  Now you can launch MAi-RAG from ~/Applications or Spotlight.


### Windows Users (WSL2)

  ** Method 1: Batch File (Recommended)**
     After installation, Windows-specific batch files are created:

     Start MAi-RAG:
      cd %USERPROFILE%\MAi-RAG
      start-windows.bat

     What it does:

     - Activates Python virtual environment
     - Starts Qdrant vector database
     - Starts FastAPI backend
     - Opens browser automatically

### Stop MAi-RAG:
    stop-windows.bat

  **Method 2: Create Desktop Shortcut**

     - Navigate to your MAi-RAG folder in File Explorer
     - Right-click start-windows.bat
     - Select "Send to" → "Desktop (create shortcut)"
     - Right-click the new shortcut → Properties
     - Click "Change Icon"
     - Browse to frontend\public\mai-rag-logo.png
     - Click OK to apply

    Now you can double-click the desktop icon to start MAi-RAG.

  **Method 3: WSL Terminal**
    cd ~/MAi-RAG
    ./start.sh

  Note: Windows users running through WSL2 have full Linux compatibility. All Linux instructions apply.

  First-Time Setup: first_launch.py (All Platforms)
  For initial installation or environment recreation:
  Linux/macOS:


-----------------------------------------------------------------------------------

### Stopping MAi-RAG

  **Method 1: Web UI**

    Click "Stop MAi-RAG" button in the header in the WebUI
  
  **Method 2: Linux/macOS Terminal**

    cd ~/MAi-RAG
    ./stop.sh

  **Windows:**
    stop-windows.bat

  **Method 3: Manual Process Kill**

  Linux/macOS Manual:

    pkill -f "uvicorn app.main:app"
    pkill -f "watchdog.py"
    pkill -f "./qdrant"
    pkill -f "ollama"

  Windows:
    taskkill /F /IM uvicorn.exe
    taskkill /F /IM qdrant.exe



  **Method 4: Ctrl+C
  If you started MAi-RAG with start.sh in the foreground, press Ctrl+C to stop all services gracefully.

-----------------------------------------------------------------------------------

### Updating MAi-RAG

  cd ~/MAi-RAG

  # Pull latest changes
    git pull

  # Activate virtual environment
    source venv/bin/activate

  # Update Python dependencies
    pip install -r requirements.txt

  # Rebuild frontend
    cd frontend
    npm install
    npm run build
    cd ..

  # Restart MAi-RAG
    ./stop.sh
    ./start.sh

-----------------------------------------------------------------------------------

### Accessing MAi-RAG from Other Devices

  Local Network Access (Same WiFi)

    1. Find your computer's IP address:

    Linux/macOS:
    ip addr show | grep "inet " | grep -v 127.0.0.1

    Windows (WSL2):
    hostname -I

        Look for something like 192.168.1.100

    2. On your tablet/phone (connected to same WiFi network):
       - Open browser
       - Navigate to http://192.168.1.XX:8000 (replace XX with your IP suffix)

    That's it! No additional configuration needed.

-----------------------------------------------------------------------------------

### SSH Tunnel (Remote Access)

For secure remote access or accessing from outside your network:

  **Step 1: Install SSH Client on Mobile Device**

    iOS:
      Termius
      Blink Shell

    Android:
      JuiceSSH
      Termius

  **Step 2: Create SSH Tunnel**

    From your mobile device's SSH client:
    ssh -L 8000:localhost:8000 username@192.168.1.XX

    Replace:

    - username with your computer's username
    - 192.168.1.XX with your computer's IP address

  **Step 3: Access in Browser**

    - Open browser on tablet/phone
    - Navigate to http://localhost:8000

     See: SSH-SETUP.md for detailed instructions.

-----------------------------------------------------------------------------------


### Troubleshooting

  **Installation Issues**

    **Issue: "Command not found: python3"**
    # Install Python
    sudo apt install python3 python3-pip python3-venv  # Debian/Ubuntu
    sudo dnf install python3 python3-pip               # Fedora/RHEL
    brew install python                                # macOS

    **Issue: "Command not found: node"**
    # Install Node.js
    sudo apt install nodejs npm                        # Debian/Ubuntu
    sudo dnf install nodejs npm                        # Fedora/RHEL
    brew install node                                  # macOS
    
    **Issue: "Permission denied" on start.sh**
    cd ~/MAi-RAG
    chmod +x start.sh stop.sh install.sh

    **Issue: Virtual environment creation fails**
    # Ensure python3-venv is installed
    sudo apt install python3-venv                      # Debian/Ubuntu
    sudo dnf install python3-virtualenv                # Fedora/RHEL

    **Issue: npm install fails**
    # Clear npm cache and retry
    cd frontend
    rm -rf node_modules package-lock.json
    npm install

### Runtime Issues

    **Issue: Desktop icon doesn't appear in application menu**
    # Update desktop database
    update-desktop-database ~/.local/share/applications/

    # Verify .desktop file is valid
    desktop-file-validate ~/.local/share/applications/MAi-RAG.desktop

    **Issue: Desktop icon image doesn't show**
    # Check icon file exists
    ls -lh ~/MAi-RAG/frontend/public/mai-rag-logo.png

    # Verify Icon path in .desktop file is correct
    grep "^Icon=" ~/.local/share/applications/MAi-RAG.desktop

    # Should be absolute path like:
    # Icon=/home/username/MAi-RAG/frontend/public/mai-rag-logo.png

    **Issue: start.sh says "Ollama is not running"**
    # Start Ollama
    ollama serve &

    # Verify it's running
    curl http://localhost:11434/api/tags

    # Then try start.sh again
    ./start.sh

    **Issue: MAi-RAG won't start**
    Check the following:

    1. Is Ollama running?
    curl http://localhost:11434/api/tags
    If this fails, start Ollama: ollama serve

    2. Verify Python version:
    python3 --version
    (Must be 3.12 or higher)

    3. Check Node.js version:
    node --version
    Must be 18 or higher

    4. Run System Doctor from Assistant Settings in the Web UI

    **Issue: start.sh says "Ollama is not running"**
    # Start Ollama
    ollama serve &

    # Verify it's running
    curl http://localhost:11434/api/tags

    # Then try start.sh again
    ./start.sh

    **Issue: start.sh says "Virtual environment not found"**
    # Run first_launch.py to create it
    python3 first_launch.py

    # OR create it manually
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

    **Issue: Qdrant fails to start**
    # Check if Qdrant binary exists
    ls -lh ./qdrant

    # Make it executable
    chmod +x ./qdrant

    # Check logs
    cat /tmp/qdrant.log

    # Try starting manually
    ./qdrant &

    **Issue: "Permission denied" on start.sh**
    chmod +x start.sh stop.sh

    **Issue: Backend won't start after git pull**
    # Dependencies may have changed
    python3 first_launch.py

    # OR manually update
    source venv/bin/activate
    pip install -r requirements.txt

    **Issue: Port 8000 already in use**
    # Find what's using the port
    lsof -i :8000

    # Kill the process
    pkill -f "uvicorn app.main:app"

    # Wait a moment, then try again
    sleep 2
    ./start.sh

    **Issue: Slow response times**
    - Use smaller model (7B instead of 14B or 32B)
    - Close RAM-intensive applications
    - Reduce context window size in Ollama
    - Check system resources in the Chat Console monitor

    **Issue: Models not appearing in dropdown**
    1. Verify Ollama is running:
    curl http://localhost:11434/api/tags

    2. Pull a model:
    ollama pull qwen2.5-coder:7b

    3. Restart MAi-RAG

    **Issue: Ollama connection refused**
    # Start Ollama
    ollama serve &

    # Verify it's running
    curl http://localhost:11434/api/tags

    **Issue: Qdrant not available**
    # Start Qdrant manually
    cd ~/MAi-RAG
    ./qdrant &

    # Verify it's running
    curl http://localhost:6333/

    **Issue: Voice transcription fails**
    1. Check microphone permissions in browser
    2. Ensure Vosk fallback model exists:
    ls ~/MAi-RAG/models/vosk-model-small-en-us-0.15/
    3. Check browser console for errors (F12 → Console tab)

    **Issue: File not saved to workspace**
    1. Check workspace directory exists and is writable:
       ls -ld ~/MAi-RAG/workspace/

    2. Use [FILE] prefix for explicit file creation:
       [FILE] Create test.txt with content: Hello World

    3. Check browser console for errors f12 console tab

    **Issue: Verification rejects valid content**
    Review app/agents/verifier.py rules and adjust heuristics for your use case.

### System Doctor
    For persistent issues, use the built-in System Doctor:

    1. Click Assistant Settings in the navigation menu
    2. Click System Doctor button
    3. Review the diagnostic report
    4. Apply suggested fixes
    5. Check the generated JSON report for detailed information

    The System Doctor checks:

    - Ollama connectivity and model count
    - Qdrant vector database status
    - SQLite database integrity
    - Workspace directory permissions
    - Frontend build existence
    - Disk space availability
    - Python dependency verification
    
### Uninstalling MAi-RAG

    To completely remove MAi-RAG:
    # Stop all services
    cd ~/MAi-RAG
    ./stop.sh

    # Remove MAi-RAG directory
    cd ~
    rm -rf ~/MAi-RAG

    # Optional: Remove Ollama
    sudo rm /usr/local/bin/ollama
    rm -rf ~/.ollama

    # Optional: Remove Ollama models
    rm -rf ~/.ollama/models

-----------------------------------------------------------------------------------

### Getting Help

    If you encounter issues not covered in this guide:

    1. Check the System Doctor - Run diagnostics from Assistant Settings
    2. Review logs - Check terminal output for error messages
    3. Search existing issues - GitHub Issues
    4. Create new issue - Provide detailed information about your problem
    5. Join discussions - GitHub Discussions

<p align="center">
  <strong>Need more help? <a href="mailto:MAi-RAG-PA@proton.me">Contact Support</a></strong>
</p>
