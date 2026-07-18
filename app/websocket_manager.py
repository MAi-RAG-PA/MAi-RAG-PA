# app/websocket_manager.py
"""
WebSocket connection manager for MAi-RAG real-time updates.
Handles client connections, broadcasting, and message routing.
"""
import asyncio
import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
            total = len(self.active_connections)
        logger.info("WebSocket connected (%s total)", total)

    async def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket."""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            total = len(self.active_connections)
        logger.info("WebSocket disconnected (%s total)", total)

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        async with self._lock:
            connections = list(self.active_connections)

        if not connections:
            return

        payload = json.dumps(message)
        disconnected = []

        for connection in connections:
            try:
                await connection.send_text(payload)
            except Exception:
                disconnected.append(connection)

        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)
                remaining = len(self.active_connections)
            logger.info(
                "Cleaned up %s dead WebSocket connections (%s remaining)",
                len(disconnected),
                remaining,
            )

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send a message to a specific client."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning("Failed to send personal message: %s", e)

    @property
    def client_count(self) -> int:
        return len(self.active_connections)


ws_manager = ConnectionManager()
