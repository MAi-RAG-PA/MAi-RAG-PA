#!/usr/bin/env python3
"""
MAi-RAG-PA Smart Launcher
Checks and installs dependencies, builds frontend, then starts the app
"""
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Set offline mode for HuggingFace to prevent unnecessary downloads
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# ============================================================================
# Constants
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.resolve()
VENV_PATH = PROJECT_ROOT / "venv"
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
WATCHDOG_SCRIPT = PROJECT_ROOT / "watchdog.py"
QDRANT_BINARY = PROJECT_ROOT / "qdrant"
QDRANT_LOG = PROJECT_ROOT / "qdrant.log"
APP_MAIN = PROJECT_ROOT / "app" / "main.py"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"
PACKAGE_JSON = FRONTEND_DIR / "package.json"

OLLAMA_URL = "http://127.0.0.1:11434"
QDRANT_URL = "http://127.0.0.1:6333"
BACKEND_PORT = 8000
BACKEND_HOST = "0.0.0.0"  # Change to "127.0.0.1" for local-only access
WATCHDOG_PORT = 8001

MIN_PYTHON_VERSION = (3, 12)
MIN_NODE_VERSION = 20
PIP_INSTALL_TIMEOUT = 600  # 10 minutes
NPM_INSTALL_TIMEOUT = 300  # 5 minutes
SHUTDOWN_WAIT_TIME = 2  # seconds


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"


def log(message, color=Colors.NC):
    """Print a colored log message."""
    print(f"{color}{message}{Colors.NC}")


def validate_required_files():
    """Validate that all required files exist before starting."""
    log("Validating required files...", Colors.YELLOW)

    required_files = {
        REQUIREMENTS_FILE: "Python requirements file",
        APP_MAIN: "Main application file",
        WATCHDOG_SCRIPT: "Watchdog script",
        PACKAGE_JSON: "Frontend package.json",
    }

    required_dirs = {
        FRONTEND_DIR: "Frontend directory",
    }

    missing = []

    for file_path, description in required_files.items():
        if not file_path.exists():
            missing.append(f"{description}: {file_path}")

    for dir_path, description in required_dirs.items():
        if not dir_path.exists() or not dir_path.is_dir():
            missing.append(f"{description}: {dir_path}")

    if missing:
        log("Required files are missing:", Colors.RED)
        for msg in missing:
            log(f"   {msg}", Colors.RED)
        log("   Please ensure you have cloned the repository correctly.", Colors.YELLOW)
        return False

    log("All required files present", Colors.GREEN)
    return True


def check_python_version():
    """Check if Python 3.12+ is available."""
    if sys.version_info < MIN_PYTHON_VERSION:
        log(
            f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ required. "
            f"You have {sys.version_info.major}.{sys.version_info.minor}",
            Colors.RED,
        )
        log("   Download from: https://www.python.org/downloads/", Colors.BLUE)
        return False
    log(
        f"Python {sys.version_info.major}.{sys.version_info.minor} detected",
        Colors.GREEN,
    )
    return True


def check_node_version():
    """Check if Node.js 20+ is available."""
    node_path = shutil.which("node")
    if not node_path:
        log("Node.js not found. Frontend cannot be built.", Colors.RED)
        log("   Install Node.js 20+ from: https://nodejs.org/", Colors.BLUE)
        return False

    try:
        result = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=5
        )
        version_str = result.stdout.strip().lstrip("v")
        major_version = int(version_str.split(".")[0])

        if major_version < MIN_NODE_VERSION:
            log(
                f"Node.js v{major_version} found, but v{MIN_NODE_VERSION}+ required",
                Colors.RED,
            )
            log("   Update Node.js from: https://nodejs.org/", Colors.BLUE)
            return False

        log(f"Node.js v{version_str} detected", Colors.GREEN)
        return True
    except Exception as e:
        log(f"Error checking Node.js version: {e}", Colors.RED)
        return False


def get_venv_python():
    """Get the path to the virtual environment Python executable."""
    if sys.platform == "win32":
        return VENV_PATH / "Scripts" / "python.exe"
    return VENV_PATH / "bin" / "python"


def create_venv():
    """Create virtual environment if it doesn't exist."""
    if VENV_PATH.exists():
        log("Virtual environment exists", Colors.GREEN)
        return True

    log("Creating virtual environment...", Colors.YELLOW)
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(VENV_PATH)], check=True, timeout=120
        )
        log("Virtual environment created", Colors.GREEN)
        return True
    except subprocess.TimeoutExpired:
        log("Virtual environment creation timed out", Colors.RED)
        return False
    except subprocess.CalledProcessError as e:
        log(f"Failed to create venv: {e}", Colors.RED)
        return False
    except Exception as e:
        log(f"Unexpected error creating venv: {e}", Colors.RED)
        return False


def install_dependencies():
    """Install requirements if needed."""
    log("Checking dependencies...", Colors.YELLOW)

    venv_python = get_venv_python()

    if not venv_python.exists():
        log(f"Virtual environment Python not found at {venv_python}", Colors.RED)
        return False

    # Check if core dependencies are already installed
    try:
        result = subprocess.run(
            [str(venv_python), "-c", "import fastapi, uvicorn, qdrant_client"],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            log("Dependencies already installed", Colors.GREEN)
            return True
    except subprocess.TimeoutExpired:
        log("Dependency check timed out, will attempt install", Colors.YELLOW)
    except Exception as e:
        log(f"Dependency check failed: {e}, will attempt install", Colors.YELLOW)

    log("Installing dependencies (this may take several minutes)...", Colors.YELLOW)
    try:
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
            check=True,
            timeout=PIP_INSTALL_TIMEOUT,
        )
        log("Dependencies installed", Colors.GREEN)

        # Verify critical packages
        log("Verifying critical packages...", Colors.YELLOW)
        result = subprocess.run(
            [
                str(venv_python),
                "-c",
                "import fastapi, uvicorn, qdrant_client, sentence_transformers, spacy",
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            log(
                "Warning: Some critical packages may not be installed correctly",
                Colors.YELLOW,
            )
        else:
            log("Critical packages verified", Colors.GREEN)

        return True
    except subprocess.TimeoutExpired:
        log(f"Installation timed out after {PIP_INSTALL_TIMEOUT} seconds", Colors.RED)
        return False
    except subprocess.CalledProcessError as e:
        log(f"Failed to install dependencies: {e}", Colors.RED)
        return False
    except Exception as e:
        log(f"Unexpected error installing dependencies: {e}", Colors.RED)
        return False


def setup_spacy_model():
    """Download SpaCy English model if not present."""
    log("Checking SpaCy model...", Colors.YELLOW)

    venv_python = get_venv_python()

    # Check if model is already installed
    try:
        result = subprocess.run(
            [str(venv_python), "-c", "import spacy; spacy.load('en_core_web_sm')"],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            log("SpaCy model already installed", Colors.GREEN)
            return True
    except subprocess.TimeoutExpired:
        log("SpaCy check timed out, will attempt download", Colors.YELLOW)
    except Exception as e:
        log(f"SpaCy check failed: {e}, will attempt download", Colors.YELLOW)

    # Download the model
    log("Downloading SpaCy English model (en_core_web_sm)...", Colors.YELLOW)
    try:
        subprocess.run(
            [str(venv_python), "-m", "spacy", "download", "en_core_web_sm"],
            check=True,
            timeout=300,  # 5 minutes
        )
        log("SpaCy model downloaded successfully", Colors.GREEN)
        return True
    except subprocess.TimeoutExpired:
        log("SpaCy model download timed out", Colors.RED)
        log(
            "   You can manually install it with: python -m spacy download en_core_web_sm",
            Colors.YELLOW,
        )
        return False
    except subprocess.CalledProcessError as e:
        log(f"Failed to download SpaCy model: {e}", Colors.RED)
        log(
            "   You can manually install it with: python -m spacy download en_core_web_sm",
            Colors.YELLOW,
        )
        return False
    except Exception as e:
        log(f"Unexpected error downloading SpaCy model: {e}", Colors.RED)
        return False


def build_frontend():
    """Build the React frontend if not already built."""
    log("Checking frontend build...", Colors.YELLOW)

    # Check if frontend is already built
    if FRONTEND_DIST.exists() and any(FRONTEND_DIST.iterdir()):
        log("Frontend already built", Colors.GREEN)
        return True

    # Check for node
    if not check_node_version():
        log("Frontend build skipped - Node.js not available", Colors.YELLOW)
        log("   Web UI will not be available until frontend is built", Colors.YELLOW)
        return False

    # Check for npm
    npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
    if not shutil.which(npm_cmd):
        log("npm not found. Cannot build frontend.", Colors.RED)
        return False

    log("Building frontend (this may take several minutes)...", Colors.YELLOW)

    try:
        # Install npm dependencies
        log("   Installing npm dependencies...", Colors.BLUE)
        subprocess.run(
            [npm_cmd, "install"],
            cwd=str(FRONTEND_DIR),
            check=True,
            timeout=NPM_INSTALL_TIMEOUT,
        )

        # Build frontend
        log("   Building frontend...", Colors.BLUE)
        subprocess.run(
            [npm_cmd, "run", "build"],
            cwd=str(FRONTEND_DIR),
            check=True,
            timeout=NPM_INSTALL_TIMEOUT,
        )

        # Verify build
        if not FRONTEND_DIST.exists():
            log("Frontend build completed but dist directory not found", Colors.RED)
            return False

        log("Frontend built successfully", Colors.GREEN)
        return True

    except subprocess.TimeoutExpired:
        log("Frontend build timed out", Colors.RED)
        return False
    except subprocess.CalledProcessError as e:
        log(f"Failed to build frontend: {e}", Colors.RED)
        return False
    except Exception as e:
        log(f"Unexpected error building frontend: {e}", Colors.RED)
        return False


def is_port_in_use(port):
    """Check if a port is currently in use."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", port))
            return result == 0
    except Exception:
        return False


def graceful_kill(process_name):
    """Attempt graceful process termination, then force kill if needed."""
    try:
        if sys.platform == "win32":
            # Try graceful first
            subprocess.run(
                ["taskkill", "/IM", f"{process_name}*"], capture_output=True, timeout=5
            )
            time.sleep(SHUTDOWN_WAIT_TIME)
            # Force kill if still running
            subprocess.run(
                ["taskkill", "/F", "/IM", f"{process_name}*"],
                capture_output=True,
                timeout=5,
            )
        else:
            # Try graceful first (SIGTERM)
            subprocess.run(
                ["pkill", "-f", process_name], capture_output=True, timeout=5
            )
            time.sleep(SHUTDOWN_WAIT_TIME)
            # Force kill if still running (SIGKILL)
            subprocess.run(
                ["pkill", "-9", "-f", process_name], capture_output=True, timeout=5
            )
        return True
    except subprocess.TimeoutExpired:
        log(f"Kill command timed out for {process_name}", Colors.YELLOW)
        return False
    except Exception as e:
        log(f"Error killing {process_name}: {e}", Colors.YELLOW)
        return False


def cleanup_existing_processes():
    """Kill existing processes to prevent port conflicts."""
    log("Checking for existing processes...", Colors.YELLOW)

    processes_to_check = [
        ("uvicorn", BACKEND_PORT),
        ("qdrant", 6333),
        ("watchdog.py", WATCHDOG_PORT),
    ]

    for proc_name, port in processes_to_check:
        try:
            if is_port_in_use(port):
                log(f"Port {port} ({proc_name}) is in use", Colors.YELLOW)
                user_input = (
                    input(f"   Kill existing {proc_name} process? (y/n): ")
                    .strip()
                    .lower()
                )

                if user_input == "y":
                    if graceful_kill(proc_name):
                        log(f"Killed {proc_name}", Colors.GREEN)
                    else:
                        log(f"May not have fully killed {proc_name}", Colors.YELLOW)
                else:
                    log(f"Skipping {proc_name} - may cause conflicts", Colors.YELLOW)
        except Exception as e:
            log(f"Error checking {proc_name}: {e}", Colors.YELLOW)


def check_ollama():
    """Check if Ollama is running and has models."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            models = data.get("models", [])
            log(f"Ollama is running with {len(models)} models", Colors.GREEN)

            if len(models) == 0:
                log("Warning: No models found in Ollama", Colors.YELLOW)
                log("   Pull a model with: ollama pull qwen2.5-coder:7b", Colors.YELLOW)

            return True
    except urllib.error.URLError:
        log("Ollama is not running", Colors.RED)
        log("   Please start Ollama first: ollama serve", Colors.YELLOW)
        return False
    except json.JSONDecodeError as e:
        log(f"Invalid response from Ollama: {e}", Colors.RED)
        return False
    except Exception as e:
        log(f"Error checking Ollama: {e}", Colors.RED)
        return False


def start_watchdog():
    """Start the watchdog mini-server for WebUI Start/Stop buttons."""
    if not WATCHDOG_SCRIPT.exists():
        log(
            "watchdog.py not found. WebUI Start/Stop buttons will not work.",
            Colors.YELLOW,
        )
        return None

    log("Starting Watchdog mini-server...", Colors.YELLOW)

    try:
        if sys.platform == "win32":
            process = subprocess.Popen(
                [sys.executable, str(WATCHDOG_SCRIPT)],
                cwd=str(PROJECT_ROOT),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            process = subprocess.Popen(
                [sys.executable, str(WATCHDOG_SCRIPT)],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        log(f"   Watchdog started (PID: {process.pid})", Colors.BLUE)

        # Wait for watchdog to be ready
        for i in range(10):
            if is_port_in_use(WATCHDOG_PORT):
                log("Watchdog is ready on port 8001", Colors.GREEN)
                return process
            time.sleep(0.5)

        log("Watchdog may not be ready yet, continuing...", Colors.YELLOW)
        return process

    except Exception as e:
        log(f"Failed to start watchdog: {e}", Colors.RED)
        return None


def start_qdrant(max_retries=2):
    """Start Qdrant if not running, with retry logic."""
    # Check if already running
    try:
        req = urllib.request.Request(f"{QDRANT_URL}/", method="GET")
        with urllib.request.urlopen(req, timeout=3) as response:
            log("Qdrant is already running", Colors.GREEN)
            return None
    except Exception:
        pass  # Not running, continue to start it

    if not QDRANT_BINARY.exists():
        log("Qdrant binary not found. RAG features will not work.", Colors.RED)
        log("   Download from: https://github.com/qdrant/qdrant/releases", Colors.BLUE)
        user_input = input("   Continue without Qdrant? (y/n): ").strip().lower()
        if user_input != "y":
            return False
        log(
            "   Continuing without Qdrant - RAG features will be disabled",
            Colors.YELLOW,
        )
        return None

    # Make executable on Unix
    if sys.platform != "win32":
        import stat

        st = os.stat(str(QDRANT_BINARY))
        os.chmod(str(QDRANT_BINARY), st.st_mode | stat.S_IEXEC)

    for attempt in range(max_retries + 1):
        if attempt > 0:
            log(
                f"Retrying Qdrant startup (attempt {attempt + 1}/{max_retries + 1})...",
                Colors.YELLOW,
            )
            time.sleep(2)

        log(f"Starting Qdrant from: {QDRANT_BINARY}", Colors.YELLOW)

        try:
            with open(QDRANT_LOG, "w") as log_file:
                if sys.platform == "win32":
                    process = subprocess.Popen(
                        [str(QDRANT_BINARY)],
                        cwd=str(PROJECT_ROOT),
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                    )
                else:
                    process = subprocess.Popen(
                        [str(QDRANT_BINARY)],
                        cwd=str(PROJECT_ROOT),
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )

                log(f"   Qdrant process started (PID: {process.pid})", Colors.BLUE)

                for i in range(20):
                    if process.poll() is not None:
                        log(
                            f"Qdrant process exited with code: {process.returncode}",
                            Colors.RED,
                        )
                        log(f"   Check log file: {QDRANT_LOG}", Colors.YELLOW)
                        break

                    if is_port_in_use(6333):
                        log("Qdrant is ready", Colors.GREEN)
                        return process

                    time.sleep(1)
                    if i % 5 == 0 and i > 0:
                        log(f"   Waiting for Qdrant... ({i}s)", Colors.YELLOW)
                else:
                    log("Qdrant failed to respond after 20 seconds", Colors.RED)
                    process.terminate()
                    continue

                if process.poll() is None and is_port_in_use(6333):
                    return process

        except Exception as e:
            log(f"Failed to start Qdrant: {e}", Colors.RED)
            if attempt == max_retries:
                return None

    log("Qdrant failed to start after all retries", Colors.RED)
    return None


def verify_backend_ready(max_wait=30):
    """Verify that the backend is actually responding."""
    log("Verifying backend is responding...", Colors.YELLOW)

    for i in range(max_wait):
        try:
            req = urllib.request.Request(
                f"http://127.0.0.1:{BACKEND_PORT}/health", method="GET"
            )
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    log("Backend is ready and responding", Colors.GREEN)
                    return True
        except Exception:
            pass

        time.sleep(1)
        if i % 5 == 0 and i > 0:
            log(f"   Waiting for backend... ({i}s)", Colors.YELLOW)

    log("Backend did not respond within timeout", Colors.YELLOW)
    return False


def start_backend(qdrant_process, watchdog_process):
    """Start the FastAPI backend."""
    log("Starting MAi-RAG-PA backend...", Colors.YELLOW)

    venv_python = get_venv_python()

    os.environ["PYTHONPATH"] = str(PROJECT_ROOT)
    os.environ["OLLAMA_URL"] = OLLAMA_URL

    print()
    log("=" * 50, Colors.GREEN)
    log("  MAi-RAG-PA is starting...", Colors.GREEN)
    log(f"  Web UI: http://localhost:{BACKEND_PORT}", Colors.GREEN)
    log("=" * 50, Colors.GREEN)
    print()

    def cleanup(signum=None, frame=None):
        print()
        log("Shutting down...", Colors.YELLOW)
        if qdrant_process:
            try:
                qdrant_process.terminate()
                qdrant_process.wait(timeout=5)
            except Exception:
                try:
                    qdrant_process.kill()
                except Exception:
                    pass
        if watchdog_process:
            try:
                watchdog_process.terminate()
                watchdog_process.wait(timeout=5)
            except Exception:
                try:
                    watchdog_process.kill()
                except Exception:
                    pass
        sys.exit(0)

    # Register signal handlers
    if sys.platform != "win32":
        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)

    try:
        # Use --reload only in development
        uvicorn_args = [
            str(venv_python),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            BACKEND_HOST,
            "--port",
            str(BACKEND_PORT),
        ]

        # Add reload flag only if not in production
        if os.environ.get("MAI_PRODUCTION") != "1":
            uvicorn_args.append("--reload")

        subprocess.run(uvicorn_args, cwd=str(PROJECT_ROOT))
    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        log(f"Backend failed to start: {e}", Colors.RED)
        # Cleanup on failure
        cleanup()
        sys.exit(1)


def main():
    print()
    log("=" * 50, Colors.GREEN)
    log("  MAi-RAG-PA Smart Launcher", Colors.GREEN)
    log("=" * 50, Colors.GREEN)
    print()

    # Step 0: Validate required files
    if not validate_required_files():
        sys.exit(1)

    # Step 1: Check Python version
    if not check_python_version():
        sys.exit(1)

    # Step 2: Clean up existing processes
    cleanup_existing_processes()

    # Step 3: Create venv
    if not create_venv():
        sys.exit(1)

    # Step 4: Install dependencies
    if not install_dependencies():
        sys.exit(1)

    # Step 5: Setup SpaCy model
    setup_spacy_model()

    # Step 6: Build frontend
    if not build_frontend():
        log("Warning: Frontend not built. Web UI may not work.", Colors.YELLOW)
        log(
            "   You can build it manually: cd frontend && npm install && npm run build",
            Colors.YELLOW,
        )

    # Step 7: Check Ollama
    if not check_ollama():
        sys.exit(1)

    # Step 8: Start Watchdog (for WebUI Start/Stop buttons)
    watchdog_process = start_watchdog()

    # Step 9: Start Qdrant
    qdrant_process = start_qdrant()
    if qdrant_process is False:
        # User chose not to continue without Qdrant
        sys.exit(1)

    # Step 10: Start backend
    start_backend(qdrant_process, watchdog_process)


if __name__ == "__main__":
    main()
