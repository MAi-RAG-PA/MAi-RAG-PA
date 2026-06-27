#!/usr/bin/env python3
"""
MAi-RAG-PA Watchdog Service
Provides HTTP endpoints for WebUI to control MAi-RAG-PA services
"""
import http.server
import json
import os
import subprocess
import sys
import threading
import time
import signal
from pathlib import Path
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.resolve()
START_SCRIPT = PROJECT_ROOT / "start.sh"
STOP_SCRIPT = PROJECT_ROOT / "stop.sh"
PORT = 8001
HOST = "127.0.0.1"  # Bind to localhost only for security
ALLOWED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]

# State tracking
state = {
    "status": "running",
    "last_start": None,
    "last_stop": None,
    "last_error": None,
    "uptime_start": datetime.now().isoformat()
}
state_lock = threading.Lock()


# ============================================================================
# Utility Functions
# ============================================================================

def log(message, level="INFO"):
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")
    sys.stdout.flush()


def is_process_running(pattern):
    """Check if a process matching pattern is running."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {pattern}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return pattern.lower() in result.stdout.lower()
        else:
            result = subprocess.run(
                ["pgrep", "-f", pattern],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
    except Exception as e:
        log(f"Error checking process {pattern}: {e}", "ERROR")
        return False


def get_system_info():
    """Get basic system information."""
    try:
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(str(PROJECT_ROOT))
        
        return {
            "cpu_percent": cpu_percent,
            "memory_total_gb": round(memory.total / (1024**3), 2),
            "memory_used_gb": round(memory.used / (1024**3), 2),
            "memory_percent": memory.percent,
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_percent": disk.percent
        }
    except ImportError:
        return {"error": "psutil not installed"}
    except Exception as e:
        return {"error": str(e)}


# ============================================================================
# HTTP Handler
# ============================================================================

class WatchdogHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for watchdog service."""
    
    def _set_cors_headers(self):
        """Set CORS headers to allow frontend requests."""
        origin = self.headers.get('Origin', '')
        if origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def _send_json_response(self, status_code, data):
        """Send a JSON response with proper headers."""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        try:
            if self.path == '/status':
                self._handle_status()
            elif self.path == '/health':
                self._handle_health()
            elif self.path == '/system':
                self._handle_system()
            elif self.path == '/services':
                self._handle_services()
            else:
                self._send_json_response(404, {"error": "Not found"})
        except Exception as e:
            log(f"Error handling GET {self.path}: {e}", "ERROR")
            self._send_json_response(500, {"error": str(e)})
    
    def do_POST(self):
        """Handle POST requests."""
        try:
            if self.path == '/start':
                self._handle_start()
            elif self.path == '/stop':
                self._handle_stop()
            elif self.path == '/restart':
                self._handle_restart()
            else:
                self._send_json_response(404, {"error": "Not found"})
        except Exception as e:
            log(f"Error handling POST {self.path}: {e}", "ERROR")
            self._send_json_response(500, {"error": str(e)})
    
    def _handle_status(self):
        """Return current status."""
        with state_lock:
            status_data = state.copy()
        
        # Add service status
        status_data["services"] = {
            "backend": is_process_running("uvicorn app.main:app"),
            "qdrant": is_process_running("qdrant"),
            "watchdog": True
        }
        
        self._send_json_response(200, status_data)
    
    def _handle_health(self):
        """Health check endpoint."""
        self._send_json_response(200, {
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        })
    
    def _handle_system(self):
        """Return system information."""
        system_info = get_system_info()
        self._send_json_response(200, system_info)
    
    def _handle_services(self):
        """Return detailed service status."""
        services = {
            "backend": {
                "running": is_process_running("uvicorn app.main:app"),
                "port": 8000
            },
            "qdrant": {
                "running": is_process_running("qdrant"),
                "port": 6333
            },
            "ollama": {
                "running": is_process_running("ollama"),
                "port": 11434
            },
            "watchdog": {
                "running": True,
                "port": PORT
            }
        }
        
        self._send_json_response(200, services)
    
    def _handle_start(self):
        """Start MAi-RAG-PA services."""
        log("Start command received")
        
        if not START_SCRIPT.exists():
            log(f"Start script not found: {START_SCRIPT}", "ERROR")
            self._send_json_response(500, {
                "status": "error",
                "message": f"Start script not found: {START_SCRIPT}"
            })
            return
        
        # Check if already running
        if is_process_running("uvicorn app.main:app"):
            log("Backend already running", "WARNING")
            self._send_json_response(200, {
                "status": "already_running",
                "message": "MAi-RAG-PA is already running"
            })
            return
        
        try:
            # Execute start script
            if sys.platform == "win32":
                subprocess.Popen(
                    ["cmd", "/c", str(START_SCRIPT)],
                    cwd=str(PROJECT_ROOT),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                subprocess.Popen(
                    ["bash", str(START_SCRIPT)],
                    cwd=str(PROJECT_ROOT),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            
            with state_lock:
                state["last_start"] = datetime.now().isoformat()
                state["last_error"] = None
            
            log("Start command executed successfully")
            self._send_json_response(200, {
                "status": "starting",
                "message": "MAi-RAG-PA start command issued"
            })
            
        except Exception as e:
            error_msg = f"Failed to start: {e}"
            log(error_msg, "ERROR")
            
            with state_lock:
                state["last_error"] = error_msg
            
            self._send_json_response(500, {
                "status": "error",
                "message": error_msg
            })
    
    def _handle_stop(self):
        """Stop MAi-RAG-PA services."""
        log("Stop command received")
        
        if not STOP_SCRIPT.exists():
            log(f"Stop script not found: {STOP_SCRIPT}", "ERROR")
            self._send_json_response(500, {
                "status": "error",
                "message": f"Stop script not found: {STOP_SCRIPT}"
            })
            return
        
        try:
            # Execute stop script
            if sys.platform == "win32":
                subprocess.Popen(
                    ["cmd", "/c", str(STOP_SCRIPT)],
                    cwd=str(PROJECT_ROOT),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                subprocess.Popen(
                    ["bash", str(STOP_SCRIPT)],
                    cwd=str(PROJECT_ROOT),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            
            with state_lock:
                state["last_stop"] = datetime.now().isoformat()
                state["last_error"] = None
            
            log("Stop command executed successfully")
            self._send_json_response(200, {
                "status": "stopping",
                "message": "MAi-RAG-PA stop command issued"
            })
            
        except Exception as e:
            error_msg = f"Failed to stop: {e}"
            log(error_msg, "ERROR")
            
            with state_lock:
                state["last_error"] = error_msg
            
            self._send_json_response(500, {
                "status": "error",
                "message": error_msg
            })
    
    def _handle_restart(self):
        """Restart MAi-RAG-PA services."""
        log("Restart command received")
        
        # Stop first
        self._handle_stop()
        
        # Wait a bit before starting
        time.sleep(3)
        
        # Then start
        self._handle_start()
    
    def log_message(self, format, *args):
        """Suppress default HTTP server logging."""
        pass


# ============================================================================
# Main Server
# ============================================================================

def run_server():
    """Run the watchdog HTTP server."""
    try:
        server = http.server.HTTPServer((HOST, PORT), WatchdogHandler)
        log(f"Watchdog server started on http://{HOST}:{PORT}")
        log(f"Project root: {PROJECT_ROOT}")
        
        # Verify required scripts exist
        if not START_SCRIPT.exists():
            log(f"WARNING: Start script not found: {START_SCRIPT}", "WARNING")
        else:
            log(f"Start script: {START_SCRIPT}")
        
        if not STOP_SCRIPT.exists():
            log(f"WARNING: Stop script not found: {STOP_SCRIPT}", "WARNING")
        else:
            log(f"Stop script: {STOP_SCRIPT}")
        
        server.serve_forever()
        
    except OSError as e:
        if e.errno == 98:  # Address already in use
            log(f"ERROR: Port {PORT} is already in use. Another watchdog may be running.", "ERROR")
            sys.exit(1)
        else:
            log(f"ERROR: {e}", "ERROR")
            sys.exit(1)
    except Exception as e:
        log(f"ERROR: {e}", "ERROR")
        sys.exit(1)


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    log(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """Main entry point."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    log("=" * 50)
    log("MAi-RAG-PA Watchdog Service")
    log("=" * 50)
    
    # Run server in main thread (simpler and more reliable)
    run_server()


if __name__ == "__main__":
    main()
