#!/bin/bash
# ~/MAi-RAG-PA/start.sh

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
echo -e "${YELLOW}[3/4] Activating Python virtual environment...${NC}"

if [ ! -d "./venv" ]; then
    echo -e "${RED}✗ Virtual environment not found at ./venv${NC}"
    echo -e "${RED}  Please create it with: python3 -m venv venv${NC}"
    exit 1
fi

source ./venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# =============================================================================
# Start MAi-RAG-PA Backend
# =============================================================================
echo -e "${YELLOW}[4/4] Starting MAi-RAG-PA backend server...${NC}"

# Set environment variables
export OLLAMA_URL="http://localhost:11434"
export PYTHONPATH="${PYTHONPATH:+${PYTHONPATH}:}$(pwd)"

echo -e "${GREEN}✓ Environment configured:${NC}"
echo "  - Ollama URL: $OLLAMA_URL"
echo "  - Python path: $PYTHONPATH"
echo ""

echo -e "${GREEN}=======================================${NC}"
echo -e "${GREEN}  MAi-RAG-PA is starting...${NC}"
echo -e "${GREEN}  Web UI: http://localhost:8000${NC}"
echo -e "${GREEN}  API Docs: http://localhost:8000/docs${NC}"
echo -e "${GREEN}=======================================${NC}"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Trap Ctrl+C to clean up
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

# Start the FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload