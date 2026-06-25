#!/usr/bin/env python3
"""
MAi-RAG Smart Launcher
Checks and installs dependencies, then starts the app
"""
import os
import sys
import subprocess
import time
import urllib.request
import json
import signal
import socket
from pathlib import Path

# Set offline mode for HuggingFace to prevent unnecessary downloads
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

PROJECT_ROOT = Path(__file__).parent.resolve()
VENV_PATH = PROJECT_ROOT / "venv"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
WATCHDOG_SCRIPT = PROJECT_ROOT / "watchdog.py"

class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def log(message, color=Colors.NC):
    print(f"{color}{message}{Colors.NC}")

def check_python_version():
    """Check if Python 3.10+ is available."""
    if sys.version_info < (3, 10):
        log(f"❌ Python 3.10+ required. You have {sys.version_info.major}.{sys.version_info.minor}", Colors.RED)
        log("   Download from: https://www.python.org/downloads/", Colors.BLUE)
        return False
    log(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected", Colors.GREEN)
    return True

def create_venv():
    """Create virtual environment if it doesn't exist."""
    if VENV_PATH.exists():
        log("✅ Virtual environment exists", Colors.GREEN)
        return True
    
    log("📦 Creating virtual environment...", Colors.YELLOW)
    try:
        subprocess.run([sys.executable, "-m", "venv", str(VENV_PATH)], check=True)
        log("✅ Virtual environment created", Colors.GREEN)
        return True
    except Exception as e:
        log(f"❌ Failed to create venv: {e}", Colors.RED)
        return False

def install_dependencies():
    """Install requirements if needed."""
    log("📦 Checking dependencies...", Colors.YELLOW)
    
    if sys.platform == "win32":
        venv_python = VENV_PATH / "Scripts" / "python.exe"
    else:
        venv_python = VENV_PATH / "bin" / "python"
    
    if not venv_python.exists():
        log(f"❌ Virtual environment Python not found at {venv_python}", Colors.RED)
        return False
    
    try:
        result = subprocess.run(
            [str(venv_python), "-c", "import fastapi, uvicorn, qdrant_client"],
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0:
            log("✅ Dependencies already installed", Colors.GREEN)
            return True
    except:
        pass
    
    log("📦 Installing dependencies (this may take several minutes)...", Colors.YELLOW)
    try:
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
            check=True
        )
        log("✅ Dependencies installed", Colors.GREEN)
        return True
    except Exception as e:
        log(f"❌ Failed to install dependencies: {e}", Colors.RED)
        return False

def setup_spacy_model():
    """Download SpaCy English model if not present."""
    log("📦 Checking SpaCy model...", Colors.YELLOW)
    
    if sys.platform == "win32":
        venv_python = VENV_PATH / "Scripts" / "python.exe"
    else:
        venv_python = VENV_PATH / "bin" / "python"
    
    # Check if model is already installed
    try:
        result = subprocess.run(
            [str(venv_python), "-c", "import spacy; spacy.load('en_core_web_sm')"],
            capture_output=True,
            timeout=10
        )
        if result.returncode == 0:
            log("✅ SpaCy model already installed", Colors.GREEN)
            return True
    except:
        pass
    
    # Download the model
    log("📥 Downloading SpaCy English model (en_core_web_sm)...", Colors.YELLOW)
    try:
        subprocess.run(
            [str(venv_python), "-m", "spacy", "download", "en_core_web_sm"],
            check=True
        )
        log("✅ SpaCy model downloaded successfully", Colors.GREEN)
        return True
    except Exception as e:
        log(f"❌ Failed to download SpaCy model: {e}", Colors.RED)
        log("   You can manually install it with: python -m spacy download en_core_web_sm", Colors.YELLOW)
        return False

def cleanup_existing_processes():
    """Kill existing processes to prevent port conflicts."""
    log("🧹 Checking for existing processes...", Colors.YELLOW)
    
    processes_to_check = [
        ("uvicorn", 8000),
        ("qdrant", 6333),
        ("watchdog.py", 8001),
    ]
    
    for proc_name, port in processes_to_check:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                log(f"   ⚠️  Port {port} ({proc_name}) is in use", Colors.YELLOW)
                user_input = input(f"   Kill existing {proc_name} process? (y/n): ").strip().lower()
                
                if user_input == 'y':
                    if sys.platform == "win32":
                        subprocess.run(['taskkill', '/F', '/IM', f'{proc_name}*'], capture_output=True)
                    else:
                        subprocess.run(['pkill', '-9', '-f', proc_name], capture_output=True)
                    log(f"   ✅ Killed {proc_name}", Colors.GREEN)
                    time.sleep(1)
                else:
                    log(f"   ⚠️  Skipping {proc_name} - may cause conflicts", Colors.YELLOW)
        except Exception as e:
            log(f"   Error checking {proc_name}: {e}", Colors.RED)

def check_ollama():
    """Check if Ollama is running."""
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            models = data.get("models", [])
            log(f"✅ Ollama is running with {len(models)} models", Colors.GREEN)
            return True
    except:
        log("❌ Ollama is not running", Colors.RED)
        log("   Please start Ollama first: ollama serve", Colors.YELLOW)
        return False

def start_watchdog():
    """Start the watchdog mini-server for WebUI Start/Stop buttons."""
    if not WATCHDOG_SCRIPT.exists():
        log("⚠️  watchdog.py not found. WebUI Start/Stop buttons will not work.", Colors.YELLOW)
        return None
    
    log("🐶 Starting Watchdog mini-server...", Colors.YELLOW)
    
    try:
        if sys.platform == "win32":
            process = subprocess.Popen(
                [sys.executable, str(WATCHDOG_SCRIPT)],
                cwd=str(PROJECT_ROOT),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            process = subprocess.Popen(
                [sys.executable, str(WATCHDOG_SCRIPT)],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
        
        log(f"   Watchdog started (PID: {process.pid})", Colors.BLUE)
        
        # Wait for watchdog to be ready
        for i in range(10):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', 8001))
                sock.close()
                
                if result == 0:
                    log("✅ Watchdog is ready on port 8001", Colors.GREEN)
                    return process
            except:
                pass
            time.sleep(0.5)
        
        log("⚠️  Watchdog may not be ready yet, continuing...", Colors.YELLOW)
        return process
        
    except Exception as e:
        log(f"❌ Failed to start watchdog: {e}", Colors.RED)
        return None

def start_qdrant():
    """Start Qdrant if not running."""
    try:
        req = urllib.request.Request("http://127.0.0.1:6333/", method="GET")
        with urllib.request.urlopen(req, timeout=3) as response:
            log("✅ Qdrant is already running", Colors.GREEN)
            return None
    except:
        pass
    
    qdrant_binary = PROJECT_ROOT / "qdrant"
    
    if not qdrant_binary.exists():
        log("⚠️  Qdrant binary not found. RAG features will be disabled.", Colors.YELLOW)
        return None
    
    if sys.platform != "win32":
        import stat
        st = os.stat(str(qdrant_binary))
        os.chmod(str(qdrant_binary), st.st_mode | stat.S_IEXEC)
    
    log(f"🚀 Starting Qdrant from: {qdrant_binary}", Colors.YELLOW)
    
    qdrant_log = PROJECT_ROOT / "qdrant.log"
    log_file = open(qdrant_log, 'w')
    
    try:
        if sys.platform == "win32":
            process = subprocess.Popen(
                [str(qdrant_binary)],
                cwd=str(PROJECT_ROOT),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=log_file,
                stderr=subprocess.STDOUT
            )
        else:
            process = subprocess.Popen(
                [str(qdrant_binary)],
                cwd=str(PROJECT_ROOT),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        
        log(f"   Qdrant process started (PID: {process.pid})", Colors.BLUE)
        
        for i in range(20):
            if process.poll() is not None:
                log(f"❌ Qdrant process exited with code: {process.returncode}", Colors.RED)
                log_file.close()
                return None
            
            endpoints = ["http://127.0.0.1:6333/", "http://localhost:6333/"]
            for endpoint in endpoints:
                try:
                    req = urllib.request.Request(endpoint, method="GET")
                    with urllib.request.urlopen(req, timeout=2) as response:
                        log(f"✅ Qdrant is ready", Colors.GREEN)
                        log_file.close()
                        return process
                except:
                    continue
            
            time.sleep(1)
            if i % 5 == 0 and i > 0:
                log(f"   Waiting for Qdrant... ({i}s)", Colors.YELLOW)
        
        log("❌ Qdrant failed to respond after 20 seconds", Colors.RED)
        process.terminate()
        log_file.close()
        return None
        
    except Exception as e:
        log(f"❌ Failed to start Qdrant: {e}", Colors.RED)
        log_file.close()
        return None

def start_backend(qdrant_process, watchdog_process):
    """Start the FastAPI backend."""
    log("🚀 Starting MAi-RAG backend...", Colors.YELLOW)
    
    if sys.platform == "win32":
        venv_python = VENV_PATH / "Scripts" / "python.exe"
    else:
        venv_python = VENV_PATH / "bin" / "python"
    
    os.environ["PYTHONPATH"] = str(PROJECT_ROOT)
    os.environ["OLLAMA_URL"] = "http://127.0.0.1:11434"
    
    print()
    log("=" * 50, Colors.GREEN)
    log("  MAi-RAG is starting...", Colors.GREEN)
    log("  Web UI: http://localhost:8000", Colors.GREEN)
    log("=" * 50, Colors.GREEN)
    print()
    
    def cleanup(signum, frame):
        print()
        log("🛑 Shutting down...", Colors.YELLOW)
        if qdrant_process:
            qdrant_process.terminate()
        if watchdog_process:
            watchdog_process.terminate()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        subprocess.run([
            str(venv_python), "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ], cwd=str(PROJECT_ROOT))
    except KeyboardInterrupt:
        cleanup(None, None)

def main():
    print()
    log("=" * 50, Colors.GREEN)
    log("  MAi-RAG Smart Launcher", Colors.GREEN)
    log("=" * 50, Colors.GREEN)
    print()
    
    # Clean up existing processes
    cleanup_existing_processes()
    
    # Step 1: Check Python
    if not check_python_version():
        sys.exit(1)
    
    # Step 2: Create venv
    if not create_venv():
        sys.exit(1)
    
    # Step 3: Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Step 4: Setup SpaCy model
    setup_spacy_model()
    
    # Step 5: Check Ollama
    if not check_ollama():
        sys.exit(1)
    
    # Step 6: Start Watchdog (for WebUI Start/Stop buttons)
    watchdog_process = start_watchdog()
    
    # Step 7: Start Qdrant
    qdrant_process = start_qdrant()
    
    # Step 8: Start backend
    start_backend(qdrant_process, watchdog_process)

if __name__ == "__main__":
    main()
