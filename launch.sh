#!/bin/bash
# MAi-RAG-PA Universal Launcher (macOS & Linux)
# Starts Ollama, Qdrant, Backend, and opens the browser AFTER the backend is ready.

cd "$(dirname "$0")"

echo "Starting MAi-RAG-PA..."
echo "Please keep this window open while the app is running."
echo ""

# ============================================================
# 1. Start Ollama if not running
# ============================================================
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Starting Ollama..."
    if command -v ollama &> /dev/null; then
        ollama serve &> /tmp/ollama.log &
        sleep 3
    elif [ -d "/Applications/Ollama.app" ]; then
        open -a Ollama
        sleep 5
    fi
else
    echo "Ollama is already running."
fi

# ============================================================
# 2. Start Qdrant if not running
# ============================================================
if ! curl -s http://localhost:6333/dashboard > /dev/null 2>&1; then
    echo "Starting Qdrant..."
    if [ -f "./qdrant" ]; then
        ./qdrant &> /tmp/qdrant.log &
        sleep 3
    fi
else
    echo "Qdrant is already running."
fi

# ============================================================
# 3. Activate Virtual Environment
# ============================================================
if [ -d "./venv" ]; then
    # macOS Homebrew Python path fix
    if [[ "$OSTYPE" == "darwin"* ]] && [ -f "/opt/homebrew/bin/brew" ]; then
        export PATH="$(brew --prefix python@3.12)/libexec/bin:$PATH"
    fi
    source ./venv/bin/activate
else
    echo "Virtual environment not found. Please run the installer first."
    read -p "Press Enter to exit..."
    exit 1
fi

# ============================================================
# 4. Start Backend in the BACKGROUND
# ============================================================
echo "Starting backend..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Ensure we clean up on Ctrl+C
trap "echo ''; echo 'Shutting down...'; kill $BACKEND_PID 2>/dev/null; exit 0" INT TERM

# ============================================================
# 5. Wait for backend to be ready (max 60s)
# ============================================================
echo -n "Waiting for backend to be ready"
MAX_WAIT=60
WAITED=0
READY=0

while [ $WAITED -lt $MAX_WAIT ]; do
    # Check if the process died
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo ""
        echo "❌ Backend crashed during startup. Check the logs above."
        exit 1
    fi

    # Try the fast health endpoint
    if curl -fsS --max-time 2 http://localhost:8000/api/health/live >/dev/null 2>&1; then
        READY=1
        break
    fi

    sleep 1
    WAITED=$((WAITED + 1))
    echo -n "."
done

echo ""  # newline after dots

# ============================================================
# 6. Open Browser (only if backend is ready)
# ============================================================
if [ $READY -eq 1 ]; then
    echo "✓ Backend ready after ${WAITED}s"
    echo "Opening Web UI..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open http://localhost:8000
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open http://localhost:8000 || sensible-browser http://localhost:8000 || true
    fi
else
    echo "⚠️  Backend did not respond within ${MAX_WAIT}s"
    echo "    Opening browser anyway — you may need to refresh manually."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open http://localhost:8000
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open http://localhost:8000 || sensible-browser http://localhost:8000 || true
    fi
fi

echo ""
echo "MAi-RAG-PA is ready!"
echo "   Close this window to STOP the application."
echo "================================================"

# ============================================================
# 7. Bring backend to foreground (blocks until Ctrl+C)
# ============================================================
wait $BACKEND_PID
