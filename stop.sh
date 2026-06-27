#!/bin/bash
# MAi-RAG-PA Stop Script
# Stops all MAi-RAG-PA services gracefully

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${YELLOW}Stopping MAi-RAG-PA...${NC}"
echo ""

# Track if anything was stopped
stopped_something=false

# Function to gracefully stop a process
stop_process() {
    local process_name="$1"
    local pattern="$2"
    
    # Check if process is running
    if pgrep -f "$pattern" > /dev/null 2>&1; then
        echo -n "  Stopping $process_name... "
        
        # Try graceful shutdown first (SIGTERM)
        pkill -f "$pattern" 2>/dev/null
        
        # Wait up to 5 seconds for graceful shutdown
        for i in {1..10}; do
            if ! pgrep -f "$pattern" > /dev/null 2>&1; then
                echo -e "${GREEN}stopped${NC}"
                stopped_something=true
                return 0
            fi
            sleep 0.5
        done
        
        # Force kill if still running (SIGKILL)
        pkill -9 -f "$pattern" 2>/dev/null
        sleep 1
        
        if ! pgrep -f "$pattern" > /dev/null 2>&1; then
            echo -e "${YELLOW}force stopped${NC}"
            stopped_something=true
        else
            echo -e "${RED}failed to stop${NC}"
            return 1
        fi
    else
        echo -e "  $process_name: ${BLUE}not running${NC}"
    fi
    
    return 0
}

# Stop services in reverse order of startup
stop_process "Watchdog" "watchdog\.py"
stop_process "Backend (Uvicorn)" "uvicorn app\.main:app"
stop_process "Qdrant" "qdrant"

echo ""

if [ "$stopped_something" = true ]; then
    echo -e "${GREEN}✓ MAi-RAG-PA stopped successfully${NC}"
else
    echo -e "${YELLOW}⚠ No MAi-RAG-PA processes were running${NC}"
fi

# Note about Ollama
echo ""
echo -e "${BLUE}Note:${NC} Ollama is not stopped by this script."
echo "To stop Ollama manually, run: ${YELLOW}pkill ollama${NC}"
