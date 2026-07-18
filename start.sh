#!/bin/bash
# ~/MAi-RAG-PA/start.sh

# Kill any existing uvicorn instances to prevent port conflicts
pkill -f "uvicorn app.main:app" || true

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN}  MAi-RAG-PA Startup Script${NC}"
echo -e "${GREEN}=======================================${NC}"
echo ""

# =============================================================================
# Prerequisite Check: Ollama
# =============================================================================
echo -e "${YELLOW}[1/4] Checking Ollama prerequisite...${NC}"

if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama is running on localhost:11434${NC}"
else
    echo -e "${RED}✗ Ollama is not running on localhost:11434${NC}"
    echo -e "${RED}  Please start Ollama before running MAi-RAG-PA${NC}"
    echo -e "${RED}  Run: ollama serve${NC}"
    exit 1
fi

# =============================================================================
# Start Qdrant
# =============================================================================
echo -e "${YELLOW}[2/4] Starting Qdrant vector database...${NC}"

# Check if Qdrant is already running
if curl -s http://localhost:6333/dashboard > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Qdrant is already running${NC}"
else
    # Start Qdrant in background
    if [ -f "./qdrant" ]; then
        ./qdrant > /tmp/qdrant.log 2>&1 &
        QDRANT_PID=$!
        echo -e "${GREEN}✓ Qdrant started (PID: $QDRANT_PID)${NC}"

        # Wait for Qdrant to initialize
        echo "  Waiting for Qdrant to initialize..."
        for i in {1..10}; do
            if curl -s http://localhost:6333/dashboard > /dev/null 2>&1; then
                echo -e "${GREEN}  ✓ Qdrant is ready${NC}"
                break
            fi
            if [ $i -eq 10 ]; then
                echo -e "${RED}  ✗ Qdrant failed to start. Check /tmp/qdrant.log${NC}"
                exit 1
            fi
            sleep 1
        done
    else
        echo -e "${YELLOW}⚠ Qdrant binary not found. Skipping Qdrant startup.${NC}"
        echo -e "${YELLOW}  RAG features will be disabled until Qdrant is available.${NC}"
    fi
fi

# =============================================================================
# Activate Virtual Environment
# =============================================================================
echo -e "${YELLOW}[3/3] Activating Python virtual environment...${NC}"

if [ ! -d "./venv" ]; then
    echo -e "${RED}✗ Virtual environment not found at ./venv${NC}"
    echo -e "${RED}  Please run ./install.sh first to set up the environment.${NC}"
    exit 1
fi

source ./venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Verify uvicorn is available
if ! command -v uvicorn &> /dev/null; then
    echo -e "${RED}✗ uvicorn not found. Your virtual environment may be corrupted.${NC}"
    echo -e "${RED}  Please delete the 'venv' folder and run ./install.sh again.${NC}"
    exit 1
fi

# =============================================================================
# Set Environment Variables
# =============================================================================
export OLLAMA_URL="http://localhost:11434"
export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}$(pwd)"

echo -e "${GREEN}✓ Environment configured:${NC}"
echo "  - Ollama URL: $OLLAMA_URL"
echo "  - Python path: $PYTHONPATH"
echo ""

# =============================================================================
# Display API Key (BEFORE starting server)
# =============================================================================
echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN}  🔑 YOUR API KEY (for CLI/curl testing):${NC}"
echo -e "${GREEN}=======================================${NC}"

# Wait a moment for database to be ready
sleep 1

# Try to get the API key
if [ -f "./memory/memory_store.db" ]; then
    API_KEY=$(sqlite3 ./memory/memory_store.db "SELECT value FROM short_term_memory WHERE key='api_key';" 2>/dev/null || echo "")
    if [ -n "$API_KEY" ]; then
        echo -e "${YELLOW}$API_KEY${NC}"
        echo ""
        echo "Use this key with: -H \"X-API-Key: $API_KEY\""
    else
        echo -e "${YELLOW}Key not generated yet. Will be created on first request.${NC}"
        echo "After starting, retrieve it with:"
        echo "  curl http://localhost:8000/api/auth/auto-key"
    fi
else
    echo -e "${YELLOW}Database not found. Key will be generated on first launch.${NC}"
    echo "After starting, retrieve it with:"
    echo "  curl http://localhost:8000/api/auth/auto-key"
fi

echo ""
echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN}  MAi-RAG-PA is starting...${NC}"
echo -e "${GREEN}  Web UI: http://localhost:8000${NC}"
echo -e "${GREEN}  API Docs: http://localhost:8000/docs${NC}"
echo -e "${GREEN}=======================================${NC}"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# =============================================================================
# Trap Ctrl+C to clean up
# =============================================================================
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down MAi-RAG-PA...${NC}"
    if [ ! -z "$QDRANT_PID" ]; then
        echo "Stopping Qdrant (PID: $QDRANT_PID)..."
        kill $QDRANT_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}Goodbye!${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# =============================================================================
# Start MAi-RAG-PA Backend (BLOCKS HERE)
# =============================================================================
echo -e "${YELLOW}[4/4] Starting MAi-RAG-PA backend server...${NC}"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
