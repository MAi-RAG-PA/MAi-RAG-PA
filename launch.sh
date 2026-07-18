#!/bin/bash
# MAi-RAG-PA Universal Launcher (macOS & Linux)
# Starts Ollama, Qdrant, Backend, and opens the browser.

cd "$(dirname "$0")"

echo "Starting MAi-RAG-PA..."
echo "Please keep this window open while the app is running."
echo ""

# 1. Start Ollama if not running
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

# 2. Start Qdrant if not running
if ! curl -s http://localhost:6333/dashboard > /dev/null 2>&1; then
    echo "Starting Qdrant..."
    if [ -f "./qdrant" ]; then
        ./qdrant &> /tmp/qdrant.log &
        sleep 3
    fi
else
    echo "Qdrant is already running."
fi

# 3. Activate Virtual Environment
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

# 4. Open Browser Automatically
echo "Opening Web UI..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    open http://localhost:8000
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open http://localhost:8000 || sensible-browser http://localhost:8000 || true
fi

echo "MAi-RAG-PA is ready!"
echo "   Close this window to STOP the application."
echo "================================================"

# 5. Start Backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
