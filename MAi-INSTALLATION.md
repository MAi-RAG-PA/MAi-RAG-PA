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

## System Requirements

### Hardware Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| **RAM** | 12 GB | 16 GB+ | 16GB+ required for 14B+ models |
| **Disk Space** | 15 GB | 30 GB+ | Plus model sizes (7B ≈ 4GB each) |
| **CPU** | Intel Core i3 / AMD Ryzen 3 | Intel Core i5+ / AMD Ryzen 5+ | 64-bit processor (x86_64 or ARM64) |
| **GPU** | Optional | NVIDIA with 8GB+ VRAM | For faster inference with GPU-enabled Ollama |
| **Browsers** | Chrome 90+ / Edge 90+ / Firefox 88+ / Safari 14+ | Latest versions | For best experience |

### Required Software Versions

| Software | Minimum Version | Recommended | Check Command |
|----------|----------------|-------------|---------------|
| **Python** | 3.12+ | 3.12+ | `python3 --version` |
| **Node.js** | 20+ (LTS) | 20+ | `node --version` |
| **Git** | 2.0+ | Latest | `git --version` |
| **Ollama** | 0.30+ | Latest | `ollama --version` |
| **Qdrant** | 1.17+ | Latest | `./qdrant --version` |

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

### All database document processing is handled automatically - no additional system packages required.

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
- Windows 3.1 / 98 / XP / 2000 / Vista / 7 / 8 / 8.1
- macOS 11 (Big Sur) and earlier
- Linux distributions older than listed above
- 32-bit systems (requires 64-bit)

-----------------------------------------------------------------------------------

## Installation Methods

### Method 1: One-Line Quick Installer (Recommended for Non-Technical Users)

**Linux/macOS:**

The installer will automatically handle most dependencies and guide you through the setup process.

**One-Line Installer:**

```bash
curl -fsSL https://github.com/MAi-RAG-PA/MAi-RAG-PA/raw/main/install.sh | bash
```

**What the installer does:**
- Detects your operating system
- Installs system dependencies (Python 3.12+, Node.js 20+, Git)
- Downloads MAi-RAG-PA to ~/MAi-RAG-PA
- Sets up Python virtual environment
- Installs Python dependencies
- Builds the React frontend
- Asks if you want to install Ollama & Qdrant automatically or manually
- Pulls a recommended AI model (qwen2.5-coder:7b)
- Creates desktop launcher (Linux)
- Optionally starts MAi-RAG-PA

**Installation Process:**
1. **System Dependencies**: Python, Node.js, and Git are installed automatically
2. **Ollama & Qdrant**: You'll be asked whether to install these automatically or manually
   - Automatic: Downloads and installs Ollama and Qdrant binaries
   - Manual: You install them yourself using provided instructions
3. **Version Checking**: If dependencies are already installed, the script checks versions and offers to update outdated components
4. **Final Setup**: Desktop launcher created, ready to start

-----------------------------------------------------------------------------------

### Method 2: Manual Download

1. Go to [GitHub Releases](https://github.com/MAi-RAG-PA/MAi-RAG-PA/releases)
2. Download the latest .zip file
3. Extract to your home directory (~/MAi-RAG-PA)
4. Open terminal and navigate to the directory:

    cd ~/MAi-RAG-PA

5. Run the installer:

    ./install.sh

-----------------------------------------------------------------------------------

### Method 3: Clone from GitHub

**Clone the repository:**

    git clone https://github.com/MAi-RAG-PA/MAi-RAG-PA.git ~/MAi-RAG-PA
    cd ~/MAi-RAG-PA

**Run the installer:**

    ./install.sh

-----------------------------------------------------------------------------------

### Method 4: Manual Installation (Advanced)

**If you prefer to install dependencies manually or need more control:**

**Step 1: Install System Dependencies**

**Linux (Debian/Ubuntu):**

    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv nodejs npm git curl

**Linux (Fedora/RHEL):**

    sudo dnf install -y python3 python3-pip nodejs npm git curl

**macOS:**

    brew install python node git

**Step 2: Clone Repository**

    git clone https://github.com/MAi-RAG-PA/MAi-RAG-PA.git ~/MAi-RAG-PA
    cd ~/MAi-RAG-PA

**Step 3: Setup Python Environment**

    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

**Step 4: Install Ollama**

**Option A: System-wide installation (recommended)**

    curl -fsSL https://ollama.com/install.sh | sh

**Option B: Binary in home directory**

**Download binary:**

    curl -fsSL https://ollama.com/download/ollama-linux-amd64 -o ~/ollama
    chmod +x ~/ollama

**Add to PATH:**

    echo 'export PATH="$HOME:$PATH"' >> ~/.bashrc
    source ~/.bashrc

**Step 5: Install Qdrant**

**Download the latest release:**

**For Linux x86_64:**

    wget https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-unknown-linux-gnu.tar.gz
    tar -xzf qdrant-x86_64-unknown-linux-gnu.tar.gz
    mv qdrant ~/MAi-RAG-PA/
    chmod +x ~/MAi-RAG-PA/qdrant

**For macOS (Apple Silicon - M1/M2/M3/M4):**

    wget https://github.com/qdrant/qdrant/releases/latest/download/qdrant-aarch64-apple-darwin.tar.gz
    tar -xzf qdrant-aarch64-apple-darwin.tar.gz
    mv qdrant ~/MAi-RAG-PA/
    chmod +x ~/MAi-RAG-PA/qdrant

**For macOS (Intel):**

    wget https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-apple-darwin.tar.gz
    tar -xzf qdrant-x86_64-apple-darwin.tar.gz
    mv qdrant ~/MAi-RAG-PA/
    chmod +x ~/MAi-RAG-PA/qdrant

**Check your Mac's architecture:**

    uname -m
    # Returns: arm64 (Apple Silicon) or x86_64 (Intel)

**Step 6: Build Frontend**

    cd frontend
    npm install
    npm run build
    cd ..

**Step 7: First Time Start MAi-RAG-PA**

    cd ~/MAi-RAG-PA
    python3 first_launch.py

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

## Updating Dependencies

### Update Ollama

**System-wide installation:**

    curl -fsSL https://ollama.com/install.sh | sh

**Binary in home directory:**

    curl -fsSL https://ollama.com/download/ollama-linux-amd64 -o ~/ollama
    chmod +x ~/ollama

### Update Qdrant

    cd ~/MAi-RAG-PA
    wget https://github.com/qdrant/qdrant/releases/latest/download/qdrant-x86_64-unknown-linux-gnu.tar.gz
    tar -xzf qdrant-x86_64-unknown-linux-gnu.tar.gz
    mv qdrant ./
    chmod +x ./qdrant

-----------------------------------------------------------------------------------

## Environment Variables

**MAi-RAG-PA uses environment variables for configuration. These can be set in your shell profile or in a .env file.**

### Core Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| OLLAMA_URL | http://localhost:11434 | Ollama API endpoint |
| QDRANT_URL | http://localhost:6333 | Qdrant API endpoint |
| MAI_PORT | 8000 | Web UI port |
| MAI_HOST | 0.0.0.0 | Bind address (0.0.0.0 = all interfaces) |
| PYTHONPATH | ~/MAi-RAG-PA | Python module path |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| MAI_LOG_LEVEL | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| MAI_MAX_WORKERS | 4 | Number of worker threads |
| MAI_CONTEXT_WINDOW | 4096 | Default context window size |
| MAI_TEMPERATURE | 0.7 | Default model temperature |
| MAI_AUTO_SAVE | true | Auto-save workspace files |
| MAI_BACKUP_DIR | ~/MAi-RAG-PA-Backups | Backup directory location |

### Setting Environment Variables

**Method 1: Shell Profile (Recommended)**

**Add to ~/.bashrc or ~/.zshrc:**

    # MAi-RAG-PA Configuration
    export OLLAMA_URL="http://localhost:11434"
    export QDRANT_URL="http://localhost:6333"
    export MAI_PORT="8000"
    export MAI_HOST="0.0.0.0"
    export MAI_LOG_LEVEL="INFO"

**Then reload:**

    source ~/.bashrc  # or source ~/.zshrc

**Method 2: .env File (Already Created)**

**Create ~/MAi-RAG-PA/.env:**

    OLLAMA_URL=http://localhost:11434
    QDRANT_URL=http://localhost:6333
    MAI_PORT=8000
    MAI_HOST=0.0.0.0
    MAI_LOG_LEVEL=INFO
    MAI_MAX_WORKERS=4

-----------------------------------------------------------------------------------

## Configuration Files

### Configuration File Locations

| File | Location | Purpose |
|------|----------|---------|
| **System Prompt** | ~/MAi-RAG-PA/config/system_prompt.txt | Default AI system prompt |
| **App Config** | ~/MAi-RAG-PA/config/config.yaml | Application settings |
| **Model Config** | ~/MAi-RAG-PA/config/models.yaml | Model preferences and settings |
| **API Keys** | ~/MAi-RAG-PA/config/api_keys.env | External API keys (if used) |
| **User Preferences** | ~/MAi-RAG-PA/config/user_prefs.json | User-specific settings |

### Editing Configuration

**Edit System Prompt:**

    nano ~/MAi-RAG-PA/config/system_prompt.txt

**Edit App Config:**

    nano ~/MAi-RAG-PA/config/config.yaml

**Reset to Defaults:**

    # Backup current config
    cp ~/MAi-RAG-PA/config/config.yaml ~/MAi-RAG-PA/config/config.yaml.backup

    # Reset (will recreate on next start)
    rm ~/MAi-RAG-PA/config/config.yaml
    ~/MAi-RAG-PA/start.sh

-----------------------------------------------------------------------------------

## Multiple Instances Warning

**Running multiple instances of MAi-RAG-PA on the same machine is NOT recommended.**

### Why Multiple Instances Cause Problems

1. **Port Conflicts**: Multiple instances will try to bind to the same ports (8000, 11434, 6333)
2. **Database Locks**: SQLite doesn't handle concurrent writes well from multiple processes
3. **Resource Overload**: Each instance consumes significant RAM and CPU
4. **Qdrant Conflicts**: Multiple Qdrant instances will conflict on port 6333
5. **Data Corruption**: Concurrent access to the same database can corrupt data

### If You Must Run Multiple Instances

If you absolutely need multiple instances (not recommended), you must:

1. **Use Different Ports:**

    # Instance 1
    MAI_PORT=8000 OLLAMA_URL=http://localhost:11434 QDRANT_URL=http://localhost:6333 ./start.sh

    # Instance 2 (different ports)
    MAI_PORT=8001 OLLAMA_URL=http://localhost:11435 QDRANT_URL=http://localhost:6334 ./start.sh

2. **Use Separate Data Directories:**

    # Create separate directories
    mkdir ~/MAi-RAG-PA-instance2
    cp -r ~/MAi-RAG-PA/* ~/MAi-RAG-PA-instance2/

    # Edit config to use different paths
    nano ~/MAi-RAG-PA-instance2/config/config.yaml

3. **Monitor Resources:**

    # Monitor RAM usage
    watch -n 1 'free -h'

    # Monitor CPU usage
    htop

**Recommendation**: Use a single instance and leverage the multi-threaded chat system instead.

-----------------------------------------------------------------------------------

## Starting MAi-RAG-PA

**MAi-RAG-PA provides 3 ways to start the application, depending on your needs:**

### Method 1: Desktop Launcher Icon (Linux - Recommended for Daily Use)

**After installation, MAi-RAG-PA appears in your application menu:**
1. Search for "MAi-RAG-PA" in your application launcher
2. Click the MAi-RAG-PA icon
3. Your default browser opens automatically to http://localhost:8000

**What happens:**
- Terminal window opens with colored status output
- All services start automatically (Qdrant, backend)
- Browser opens when ready
- Press Ctrl+C in terminal to stop all services

**If icon doesn't appear:**

**Update desktop database:**

    update-desktop-database ~/.local/share/applications/

**Verify .desktop file exists:**

    ls ~/.local/share/applications/MAi-RAG-PA.desktop

### Method 2: Terminal (Recommended for Daily Use)

    cd ~/MAi-RAG-PA
    ./start.sh

**The start.sh script:**
- Starts Qdrant vector database
- Starts the watchdog process
- Launches FastAPI backend on http://localhost:8000
- Opens your default browser

### Method 3: Advanced - Running Without Scripts

**If you need to start components manually (for debugging):**

1. **Change directory:**

    cd ~/MAi-RAG-PA

2. **Start Qdrant:**

    ./qdrant &

3. **Start watchdog (optional):**

    python3 watchdog.py &

4. **Activate virtual environment:**

    source venv/bin/activate

5. **Set environment variables:**

    export OLLAMA_URL="http://localhost:11434"
    export PYTHONPATH="$(pwd)"

6. **Start backend:**

    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

-----------------------------------------------------------------------------------

## Platform-Specific Instructions

### macOS Users

**Method 1: Terminal**

    cd ~/MAi-RAG-PA
    ./start.sh

**Method 2: Create Application Shortcut (Optional)**

**Create a simple app bundle:**

    mkdir -p ~/Applications/MAi-RAG-PA.app/Contents/MacOS
    cat > ~/Applications/MAi-RAG-PA.app/Contents/MacOS/MAi-RAG-PA << EOF
    #!/bin/bash
    cd ~/MAi-RAG-PA
    ./start.sh
    EOF
    chmod +x ~/Applications/MAi-RAG-PA.app/Contents/MacOS/MAi-RAG-PA

**Now you can launch MAi-RAG-PA from ~/Applications or Spotlight.**

-----------------------------------------------------------------------------------

### Windows Users (WSL2)

**Method 1: Batch File (Recommended)**

After installation, Windows-specific batch files are created:

**Start MAi-RAG-PA:**

    cd %USERPROFILE%\MAi-RAG-PA
    start-windows.bat

**What it does:**
- Activates Python virtual environment
- Starts Qdrant vector database
- Starts FastAPI backend
- Opens browser automatically

**Stop MAi-RAG-PA:**

    stop-windows.bat

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

    cd ~/MAi-RAG-PA
    ./start.sh

**Note: Windows users running through WSL2 have full Linux compatibility. All Linux instructions apply.**

-----------------------------------------------------------------------------------

## Stopping MAi-RAG-PA

### Method 1: Web UI

**Click "Stop MAi-RAG-PA" button in the header in the WebUI**

### Method 2: Linux/macOS Terminal

    cd ~/MAi-RAG-PA
    ./stop.sh

### Method 3: Windows

    stop-windows.bat

### Method 4: Manual Process Kill

**Linux/macOS Manual:**

    pkill -f "uvicorn app.main:app"
    pkill -f "watchdog.py"
    pkill -f "./qdrant"
    pkill -f "ollama"

**Windows:**

    taskkill /F /IM uvicorn.exe
    taskkill /F /IM qdrant.exe

### Method 5: Ctrl+C

If you started MAi-RAG-PA with start.sh in the foreground, press Ctrl+C to stop all services gracefully.

-----------------------------------------------------------------------------------

## Updating MAi-RAG-PA

    cd ~/MAi-RAG-PA

**Pull latest changes:**

    git pull

**Activate virtual environment:**

    source venv/bin/activate

**Update Python dependencies:**

    pip install -r requirements.txt

**Rebuild frontend:**

    cd frontend
    npm install
    npm run build
    cd ..

**Restart MAi-RAG-PA:**

    ./stop.sh
    ./start.sh

-----------------------------------------------------------------------------------

## Firewall Configuration

**MAi-RAG-PA requires specific ports to be open for full functionality. Configure your firewall according to your needs:**

### Required Ports

| Port | Service | Protocol | Purpose | Required For |
|------|---------|----------|---------|--------------|
| 8000 | MAi-RAG-PA Web UI | TCP | Web interface access | LAN/Remote access |
| 8001 | Watchdog Service | TCP | Start/Stop control | Web UI control buttons |
| 11434 | Ollama | TCP | LLM inference API | Local operation |
| 6333 | Qdrant | TCP | Vector database API | RAG features |
| 22 | SSH | TCP | Remote access | SSH tunnel (optional) |

### UFW (Ubuntu/Debian)

**Allow MAi-RAG-PA web interface (LAN access):**

    sudo ufw allow 8000/tcp
    
**Allow Watchdog service (for WebUI control buttons)**

    sudo ufw allow 8001/tcp
**Allow Ollama (only needed if accessing from other machines):**

    sudo ufw allow 11434/tcp

**Allow Qdrant (only needed if accessing from other machines):**

    sudo ufw allow 6333/tcp

**Allow SSH (for remote access):**

    sudo ufw allow 22/tcp

**Enable firewall if not already enabled:**

    sudo ufw enable

**Check status:**

    sudo ufw status

### Firewalld (Fedora/RHEL/CentOS)

**Allow MAi-RAG-PA web interface:**

    sudo firewall-cmd --permanent --add-port=8000/tcp

**Allow Ollama:**

    sudo firewall-cmd --permanent --add-port=11434/tcp

**Allow Qdrant:**

    sudo firewall-cmd --permanent --add-port=6333/tcp

**Allow SSH:**

    sudo firewall-cmd --permanent --add-service=ssh

**Reload firewall:**

    sudo firewall-cmd --reload

**Check status:**

    sudo firewall-cmd --list-all

### Security Recommendation

**For local-only use, you can restrict access to localhost:**

**Only allow local connections (more secure):**

    sudo ufw allow from 127.0.0.1 to any port 8000
    sudo ufw allow from 127.0.0.1 to any port 11434
    sudo ufw allow from 127.0.0.1 to any port 6333

-----------------------------------------------------------------------------------

## Accessing MAi-RAG-PA from Other Devices

### Local Network Access (Same WiFi Network)

1. **Find your computer's IP address that MAi-RAG-PA is running on:**

**Linux/macOS:**

    ip addr show | grep "inet " | grep -v 127.0.0.1

**Windows (WSL2):**

    hostname -I

**Look for something like 192.168.1.100**

2. **On your tablet/phone (connected to same WiFi network):**
   - Open browser
   - Navigate to http://192.168.1.XX:8000 (replace XX with your computer's IP address suffix that MAi-RAG-PA is running on)

**That's it! No additional configuration needed.**

-----------------------------------------------------------------------------------

## HTTPS/SSL for Remote Access

**For secure remote access over the internet, you should use HTTPS instead of HTTP.**

**For detailed HTTPS/SSL setup instructions, see [MAi-SSH-SETUP.md](MAi-SSH-SETUP.md)**

### Quick Overview

**Option 1: SSH Tunnel (Recommended)**
- Most secure method
- No certificate management needed
- Encrypted connection
- See SSH Tunnel section below

**Option 2: Reverse Proxy with SSL**
- Use Nginx or Apache as reverse proxy
- Obtain SSL certificate from Let's Encrypt
- Requires domain name
- More complex setup

**Option 3: Self-Signed Certificate**
- Quick setup for testing
- Browser will show security warning
- Not recommended for production

**Security Warning**: Never expose MAi-RAG-PA directly to the internet over HTTP. Always use SSH tunnel or HTTPS.

-----------------------------------------------------------------------------------

## SSH Tunnel (Remote Access)

**For secure remote access or accessing from outside your network:**

**Step 1: Install SSH Client on Mobile Device**

**iOS:**
- Termius
- Blink Shell

**Android:**
- JuiceSSH
- Termius

**Step 2: Create SSH Tunnel**

**From your mobile device's SSH client:**

    ssh -L 8000:localhost:8000 username@192.168.1.XX

**Replace:**
- username with your computer's username
- 192.168.1.XX with your computer's IP address

**Step 3: Access in Browser**
- Open browser on tablet/phone
- Navigate to http://localhost:8000

**See: [SSH & LAN](MAi-SSH-SETUP.md) for more detailed instructions.**

-----------------------------------------------------------------------------------

## Model Storage

### Where Ollama Models Are Stored

**Linux/macOS:**

    ~/.ollama/models/

**Windows:**

    %USERPROFILE%\.ollama\models\

### Model Storage Structure

    ~/.ollama/models/
    ├── blobs/           # Model weights (large files)
    │   ├── sha256-abc...
    │   ├── sha256-def...
    │   └── ...
    └── manifests/       # Model metadata
        └── registry.ollama.ai/
            └── library/
                └── qwen2.5-coder/
                    └── 7b

### Model Sizes (Approximate)

| Model | Quantization | Size | RAM Required |
|-------|--------------|------|--------------|
| qwen2.5-coder:1.5b | q4_k_m | 1.1 GB | 2 GB |
| llama3.2:3b | q4_k_m | 2.0 GB | 4 GB |
| qwen2.5-coder:7b | q4_k_m | 4.4 GB | 8 GB |
| qwen2.5-coder:14b | q4_k_m | 8.9 GB | 16 GB |
| qwen2.5-coder:32b | q4_k_m | 20.2 GB | 32 GB |
| llama3.3:70b | q4_k_m | 41.5 GB | 64 GB |

### Managing Models

**List Installed Models:**

    ollama list

**Download a Model:**

    ollama pull qwen2.5-coder:7b

**Remove a Model:**

    ollama rm qwen2.5-coder:7b

**Check Disk Usage:**

    # Linux/macOS
    du -sh ~/.ollama/models/

    # Windows (PowerShell)
    Get-ChildItem -Path "$env:USERPROFILE\.ollama\models" -Recurse | Measure-Object -Property Length -Sum

### Backup Models

    # Backup all models
    tar -czf ollama-models-backup.tar.gz ~/.ollama/models/

    # Restore models
    tar -xzf ollama-models-backup.tar.gz -C ~/

---

## Performance Tuning

### Optimizing for Low-RAM Systems (8-12GB)

**1. Use Smaller Models:**

    # Recommended models for low-RAM systems
    ollama pull qwen2.5-coder:1.5b  # 1GB RAM
    ollama pull llama3.2:3b         # 2GB RAM
    ollama pull granite3.1-moe:3b   # 2GB RAM

**2. Reduce Context Window:**

Edit `~/MAi-RAG-PA/config/config.yaml`:

    context_window: 2048  # Reduce from 4096

**3. Limit Concurrent Operations:**

    export MAI_MAX_WORKERS=2  # Reduce from 4

**4. Use Swap Space:**

    # Create 4GB swap file
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile

    # Make permanent
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

### GPU Acceleration Setup

**1. Check GPU Availability:**

    nvidia-smi

**2. Install NVIDIA Drivers:**

    # Ubuntu/Debian
    sudo apt install nvidia-driver-535

    # Fedora
    sudo dnf install akmod-nvidia

**3. Configure Ollama for GPU:**

    # Ollama automatically uses GPU if available
    # Check GPU usage
    ollama ps

**4. Verify GPU Usage:**

    # Monitor GPU usage
    watch -n 1 nvidia-smi

### Context Window Tuning

**Recommended Context Windows by Model Size:**

| Model Size | Min RAM | Recommended Context | Max Context |
|------------|---------|---------------------|-------------|
| 1.5B | 2GB | 2048 | 4096 |
| 3B | 4GB | 2048 | 4096 |
| 7B | 8GB | 4096 | 8192 |
| 14B | 16GB | 4096 | 8192 |
| 32B | 32GB | 4096 | 16384 |

### Model Quantization Options

Ollama supports different quantization levels:

**Available Quantizations:**
- `q4_k_m` - 4-bit (default, good balance)
- `q5_k_m` - 5-bit (better quality, slower)
- `q8_0` - 8-bit (best quality, slowest)
- `f16` - 16-bit (full precision, very slow)

**Use Specific Quantization:**

    # Pull specific quantization
    ollama pull qwen2.5-coder:7b-q5_k_m

    # Check available quantizations
    ollama list

**Performance Comparison:**

| Quantization | Speed | Quality | RAM Usage |
|--------------|-------|---------|-----------|
| q4_k_m | Fast | Good | Low |
| q5_k_m | Medium | Better | Medium |
| q8_0 | Slow | Best | High |
| f16 | Very Slow | Perfect | Very High |

-----------------------------------------------------------------------------------

## Common Error Messages

### Error: "Port 8000 already in use"

**Cause**: Another process is using port 8000

**Solution:**

    # Find what's using the port
    lsof -i :8000

    # Kill the process
    pkill -f "uvicorn app.main:app"

    # Or use a different port
    export MAI_PORT=8001
    ./start.sh

### Error: "Ollama connection refused"

**Cause**: Ollama is not running

**Solution:**

    # Start Ollama
    ollama serve &

    # Verify it's running
    curl http://localhost:11434/api/tags

    # If using systemd
    sudo systemctl start ollama

### Error: "Qdrant connection refused"

**Cause**: Qdrant is not running

**Solution:**

    # Start Qdrant
    cd ~/MAi-RAG-PA
    ./qdrant &

    # Verify it's running
    curl http://localhost:6333/

    # Check logs
    cat qdrant.log

### Error: "ModuleNotFoundError: No module named 'fastapi'"

**Cause**: Python dependencies not installed

**Solution:**

    # Activate virtual environment
    source venv/bin/activate

    # Install dependencies
    pip install -r requirements.txt

    # Or run first_launch.py
    python3 first_launch.py

### Error: "Permission denied: './start.sh'"

**Cause**: Script is not executable

**Solution:**

    chmod +x start.sh stop.sh install.sh
    chmod +x qdrant

### Error: "CUDA out of memory"

**Cause**: GPU doesn't have enough VRAM for the model

**Solution:**

    # Use a smaller model
    ollama pull qwen2.5-coder:7b  # Instead of 14b or 32b

    # Or use CPU-only mode
    export OLLAMA_NUM_GPU=0

### Error: "Database is locked"

**Cause**: Multiple processes trying to write to SQLite database

**Solution:**

    # Stop all MAi-RAG-PA instances
    ./stop.sh
    pkill -f "uvicorn app.main:app"

    # Wait a few seconds
    sleep 3

    # Start again
    ./start.sh

-----------------------------------------------------------------------------------

## Service Management (systemd)

### Create systemd Service

**Create service file:**

    sudo nano /etc/systemd/system/mai-rag.service

**Add content:**

    [Unit]
    Description=MAi-RAG-PA Personal Assistant
    After=network.target ollama.service

    [Service]
    Type=simple
    User=YOUR_USERNAME
    WorkingDirectory=/home/YOUR_USERNAME/MAi-RAG-PA
    Environment="PATH=/home/YOUR_USERNAME/MAi-RAG-PA/venv/bin:/usr/local/bin:/usr/bin:/bin"
    Environment="OLLAMA_URL=http://localhost:11434"
    Environment="QDRANT_URL=http://localhost:6333"
    ExecStart=/home/YOUR_USERNAME/MAi-RAG-PA/start.sh
    ExecStop=/home/YOUR_USERNAME/MAi-RAG-PA/stop.sh
    Restart=on-failure
    RestartSec=10

    [Install]
    WantedBy=multi-user.target

**Replace YOUR_USERNAME with your actual username.**

### Enable and Start Service

    # Reload systemd
    sudo systemctl daemon-reload

    # Enable service (start on boot)
    sudo systemctl enable mai-rag

    # Start service
    sudo systemctl start mai-rag

    # Check status
    sudo systemctl status mai-rag

### Service Commands

    # Start
    sudo systemctl start mai-rag

    # Stop
    sudo systemctl stop mai-rag

    # Restart
    sudo systemctl restart mai-rag

    # Enable (start on boot)
    sudo systemctl enable mai-rag

    # Disable (don't start on boot)
    sudo systemctl disable mai-rag

    # Check status
    sudo systemctl status mai-rag

    # View logs
    sudo journalctl -u mai-rag -f

    # View last 100 log lines
    sudo journalctl -u mai-rag -n 100

### Auto-Start on Boot (Alternative: crontab)

**If you prefer not to use systemd:**

    # Edit crontab
    crontab -e

    # Add this line to start on boot
    @reboot /home/YOUR_USERNAME/MAi-RAG-PA/start.sh >> /home/YOUR_USERNAME/MAi-RAG-PA/startup.log 2>&1

-----------------------------------------------------------------------------------

## Troubleshooting

### Installation Issues

**Issue: "Command not found: python3"**

**Install Python:**

    sudo apt install python3 python3-pip python3-venv  # Debian/Ubuntu
    sudo dnf install python3 python3-pip               # Fedora/RHEL
    brew install python                                # macOS

**Issue: "Command not found: node"**

**Install Node.js:**

    sudo apt install nodejs npm                        # Debian/Ubuntu
    sudo dnf install nodejs npm                        # Fedora/RHEL
    brew install node                                  # macOS

**Issue: "Permission denied" on start.sh**

    cd ~/MAi-RAG-PA
    chmod +x start.sh stop.sh install.sh

**Issue: Virtual environment creation fails**

**Ensure python3-venv is installed:**

    sudo apt install python3-venv                      # Debian/Ubuntu
    sudo dnf install python3-virtualenv                # Fedora/RHEL

**Issue: npm install fails**

**Clear npm cache and retry:**

    cd frontend
    rm -rf node_modules package-lock.json
    npm install

-----------------------------------------------------------------------------------

### Runtime Issues

**Issue: Desktop icon doesn't appear in application menu**

**Update desktop database:**

    update-desktop-database ~/.local/share/applications/

**Verify .desktop file is valid:**

    desktop-file-validate ~/.local/share/applications/MAi-RAG-PA.desktop

**Issue: Desktop icon image doesn't show**

**Check icon file exists:**

    ls -lh ~/MAi-RAG-PA/frontend/public/mai-rag-logo.png

**Verify Icon path in .desktop file is correct:**

    grep "^Icon=" ~/.local/share/applications/MAi-RAG-PA.desktop

**Should be absolute path like:**
**Icon=/home/username/MAi-RAG-PA/frontend/public/mai-rag-logo.png**

**Issue: start.sh says "Ollama is not running"**

**Start Ollama:**

    ollama serve &

**Verify it's running:**

    curl http://localhost:11434/api/tags

**Then try start.sh again:**

    ./start.sh

**Issue: MAi-RAG-PA won't start**

**Check the following:**

**1. Is Ollama running?**

    curl http://localhost:11434/api/tags

**If this fails, start Ollama:**

    ollama serve

**2. Verify Python version:**

    python3 --version

**(Must be 3.12 or higher)**

**3. Check Node.js version:**

    node --version

**(Must be 20 or higher)**

**4. Run System Doctor from Assistant Settings in the MAi-RAG-PA WebUI**

**Issue: start.sh says "Virtual environment not found"**

**Run first_launch.py to create it:**

    python3 first_launch.py

**OR create it manually:**

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

**Issue: Qdrant fails to start**

**Check if Qdrant binary exists:**

    ls -lh ./qdrant

**Make it executable:**

    chmod +x ./qdrant

**Check logs:**

    cat ~/MAi-RAG-PA/qdrant.log

**Try starting manually:**

    ./qdrant &

**Issue: Backend won't start after git pull**

**Dependencies may have changed:**

    python3 first_launch.py

**OR manually update:**

    source venv/bin/activate
    pip install -r requirements.txt

**Issue: Port 8000 already in use**

**Find what's using the port:**

    lsof -i :8000

**Kill the process:**

    pkill -f "uvicorn app.main:app"

**Wait a moment, then try again:**

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

3. Restart MAi-RAG-PA:

    ./stop.sh && ./start.sh

**Issue: Ollama connection refused**

**Start Ollama:**

    ollama serve &

**Verify it's running:**

    curl http://localhost:11434/api/tags

**Issue: Qdrant not available**

**Start Qdrant manually:**

    cd ~/MAi-RAG-PA
    ./qdrant &

**Verify it's running:**

    curl http://localhost:6333/

**Issue: Voice transcription fails**

1. Check microphone permissions in browser
2. Ensure Vosk fallback model exists:

    ls ~/MAi-RAG-PA/models/vosk-model-small-en-us-0.15/

3. Check browser console for errors (F12 → Console tab)

**Issue: File not saved to workspace**

1. Check workspace directory exists and is writable:

    ls -ld ~/MAi-RAG-PA/workspace/

2. Use [FILE] prefix for explicit file creation:
   [FILE] Create test.txt with content: Hello World

3. Check browser console for errors (F12 → Console tab)

**Issue: Verification rejects valid content**

Review app/agents/verifier.py rules and adjust heuristics for your use case.

-----------------------------------------------------------------------------------

## System Doctor

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

-----------------------------------------------------------------------------------

## Data Backup and Restore

### What to Back Up

**MAi-RAG-PA stores important data in several locations:**

| Data Type | Location | Description |
|-----------|----------|-------------|
| SQLite Database | ~/MAi-RAG-PA/data/mai.db | Chat history, calendar, tasks, user preferences |
| Qdrant Collections | ~/MAi-RAG-PA/qdrant_storage/ | Vector embeddings for RAG knowledge base |
| Configuration | ~/MAi-RAG-PA/config/ | System prompts, settings, API keys |
| Workspace | ~/MAi-RAG-PA/workspace/ | Generated files, notes, documents |
| Ollama Models | ~/.ollama/models/ | Downloaded AI models (large, optional) |

### Backup Script

**Create a backup script at ~/MAi-RAG-PA/backup.sh:**

    #!/bin/bash
    # MAi-RAG-PA Backup Script

    BACKUP_DIR="$HOME/MAi-RAG-PA-Backups"
    DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_NAME="mai-rag-backup_$DATE"

    echo "Starting MAi-RAG-PA backup..."

    # Create backup directory
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

    # Stop MAi-RAG-PA to ensure data consistency
    echo "Stopping MAi-RAG-PA..."
    ~/MAi-RAG-PA/stop.sh
    sleep 3

    # Backup SQLite database
    echo "Backing up database..."
    cp ~/MAi-RAG-PA/data/mai.db "$BACKUP_DIR/$BACKUP_NAME/"

    # Backup Qdrant storage
    echo "Backing up Qdrant collections..."
    cp -r ~/MAi-RAG-PA/qdrant_storage "$BACKUP_DIR/$BACKUP_NAME/"

    # Backup configuration
    echo "Backing up configuration..."
    cp -r ~/MAi-RAG-PA/config "$BACKUP_DIR/$BACKUP_NAME/"

    # Backup workspace
    echo "Backing up workspace..."
    cp -r ~/MAi-RAG-PA/workspace "$BACKUP_DIR/$BACKUP_NAME/"

    # Restart MAi-RAG-PA
    echo "Restarting MAi-RAG-PA..."
    ~/MAi-RAG-PA/start.sh &

    # Create compressed archive
    echo "Creating compressed archive..."
    cd "$BACKUP_DIR"
    tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
    rm -rf "$BACKUP_NAME"

    echo "Backup complete: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
    echo "Size: $(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)"

**Make it executable:**

    chmod +x ~/MAi-RAG-PA/backup.sh

### Automated Backups (Cron)

**Set up automatic daily backups:**

**Edit crontab:**

    crontab -e

**Add this line for daily backup at 2 AM:**

    0 2 * * * /home/YOUR_USERNAME/MAi-RAG-PA/backup.sh >> /home/YOUR_USERNAME/MAi-RAG-PA/backups.log 2>&1

### Restore from Backup

    #!/bin/bash
    # MAi-RAG-PA Restore Script

    BACKUP_FILE="$1"

    if [ -z "$BACKUP_FILE" ]; then
        echo "Usage: ./restore.sh <backup-file.tar.gz>"
        exit 1
    fi

    echo "Stopping MAi-RAG-PA..."
    ~/MAi-RAG-PA/stop.sh
    sleep 3

    echo "Extracting backup..."
    tar -xzf "$BACKUP_FILE" -C /tmp/

    BACKUP_DIR=$(basename "$BACKUP_FILE" .tar.gz)

    echo "Restoring database..."
    cp /tmp/$BACKUP_DIR/mai.db ~/MAi-RAG-PA/data/

    echo "Restoring Qdrant collections..."
    rm -rf ~/MAi-RAG-PA/qdrant_storage
    cp -r /tmp/$BACKUP_DIR/qdrant_storage ~/MAi-RAG-PA/

    echo "Restoring configuration..."
    rm -rf ~/MAi-RAG-PA/config
    cp -r /tmp/$BACKUP_DIR/config ~/MAi-RAG-PA/

    echo "Restoring workspace..."
    rm -rf ~/MAi-RAG-PA/workspace
    cp -r /tmp/$BACKUP_DIR/workspace ~/MAi-RAG-PA/

    # Cleanup
    rm -rf /tmp/$BACKUP_DIR

    echo "Restore complete. Starting MAi-RAG-PA..."
    ~/MAi-RAG-PA/start.sh

-----------------------------------------------------------------------------------

## Desktop Launcher Removal

### Remove Desktop Launcher (Linux)

**Method 1: Manual Removal:**

    # Remove .desktop file
    rm ~/.local/share/applications/MAi-RAG-PA.desktop

    # Update desktop database
    update-desktop-database ~/.local/share/applications/

    # Verify removal
    ls ~/.local/share/applications/ | grep MAi

**Method 2: Using Script:**

    #!/bin/bash
    # Remove MAi-RAG-PA desktop launcher

    DESKTOP_FILE="$HOME/.local/share/applications/MAi-RAG-PA.desktop"

    if [ -f "$DESKTOP_FILE" ]; then
        echo "Removing desktop launcher..."
        rm "$DESKTOP_FILE"
        update-desktop-database ~/.local/share/applications/ 2>/dev/null
        echo "Desktop launcher removed."
    else
        echo "Desktop launcher not found."
    fi

### Remove Desktop Shortcut (Windows)

**Manual Removal:**
1. Right-click desktop shortcut
2. Select "Delete"
3. Empty Recycle Bin

**PowerShell:**

    Remove-Item "$env:USERPROFILE\Desktop\MAi-RAG-PA.lnk" -Force

### Remove Application Menu Entry (macOS)

    # Remove from Applications
    rm -rf ~/Applications/MAi-RAG-PA.app

    # Or if installed system-wide
    sudo rm -rf /Applications/MAi-RAG-PA.app

-----------------------------------------------------------------------------------

## Uninstalling MAi-RAG-PA

**To completely remove MAi-RAG-PA:**

**Stop all services:**

    cd ~/MAi-RAG-PA
    ./stop.sh

**Remove desktop launcher:**

    rm ~/.local/share/applications/MAi-RAG-PA.desktop
    update-desktop-database ~/.local/share/applications/

**Remove MAi-RAG-PA directory:**

    cd ~
    rm -rf ~/MAi-RAG-PA

**Optional: Remove Ollama:**

    sudo rm /usr/local/bin/ollama
    rm -rf ~/.ollama

**Optional: Remove Ollama models:**

    rm -rf ~/.ollama/models

-----------------------------------------------------------------------------------

## Getting Help

**If you encounter issues not covered in this guide:**

1. Check the System Doctor - Run diagnostics from Assistant Settings
2. Review logs - Check terminal output for error messages
3. Search existing issues - [GitHub Issues](https://github.com/MAi-RAG-PA/MAi-RAG-PA/issues)
4. Create new issue - Provide detailed information about your problem
5. Join discussions - [GitHub Discussions](https://github.com/MAi-RAG-PA/MAi-RAG-PA/discussions)

-----------------------------------------------------------------------------------

## Documentation

<a href="MAi-README.md">Full Documentation</a> Complete feature overview and usage guide<br />
<a href="MAi-INSTALLATION.md">Installation</a> Step-by-step setup for all platforms, System requirements, starting/stopping<br />
<a href="MAi-OLLAMA-MODELS.md">Model Recommendations</a> Choosing the right AI model for your needs<br />
<a href="MAi-SSH-SETUP.md">SSH & LAN</a> Access the system remotely from other devices via SSH or on the same network<br />
<a href="MAi-LICENCE-LEGAL-NOTICE.md">Terms of use and commercial licensing</a>

## Support & Contact

**Issues**: [GitHub Issues](https://github.com/MAi-RAG-PA/MAi-RAG-PA/issues)
**Discussions**: [GitHub Discussions](https://github.com/MAi-RAG-PA/MAi-RAG-PA/discussions)
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
