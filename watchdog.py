#!/usr/bin/env python3
import http.server
import json
import os
import subprocess
import threading
import time
from pathlib import Path

PROJECT_ROOT = Path.home() / "MAi-RAG"
START_SCRIPT = PROJECT_ROOT / "start.sh"
STOP_SCRIPT = PROJECT_ROOT / "stop.sh"
PORT = 8001  # Mini server port

class StartHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/start':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "starting"}
            self.wfile.write(json.dumps(response).encode())
            
            # Start MAi-RAG in background
            if START_SCRIPT.exists():
                subprocess.Popen(
                    ["bash", str(START_SCRIPT)], 
                    cwd=str(PROJECT_ROOT),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                print("✅ MAi-RAG Start command issued via Watchdog.")
            else:
                print("⚠️  start.sh not found")
                
        elif self.path == '/stop':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "stopping"}
            self.wfile.write(json.dumps(response).encode())
            
            # Stop MAi-RAG
            if STOP_SCRIPT.exists():
                subprocess.Popen(
                    ["bash", str(STOP_SCRIPT)],
                    cwd=str(PROJECT_ROOT),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                print("✅ MAi-RAG Stop command issued via Watchdog.")
            else:
                print("⚠️  stop.sh not found")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logs

def run_mini_server():
    server = http.server.HTTPServer(('127.0.0.1', PORT), StartHandler)
    print(f"🐶 Watchdog Mini-Server running on port {PORT}")
    server.serve_forever()

if __name__ == "__main__":
    print("🐶 MAi-RAG Watchdog starting...")
    thread = threading.Thread(target=run_mini_server, daemon=True)
    thread.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Watchdog stopping.")
