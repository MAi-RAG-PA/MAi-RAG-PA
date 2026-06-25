#!/bin/bash
# MAi-RAG Stop Script

echo "Stopping MAi-RAG..."

# Kill watchdog
pkill -f "watchdog.py" 2>/dev/null

# Kill uvicorn
pkill -f "uvicorn app.main:app" 2>/dev/null

# Kill Qdrant
pkill -f "./qdrant" 2>/dev/null

sleep 2

echo "MAi-RAG stopped."