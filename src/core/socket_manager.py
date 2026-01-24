"""
VoidCat RDC: Sovereign Spirit - Connection Manager
==================================================
Version: 1.0.0
Author: Echo (E-01)
Date: 2026-01-24

Manages WebSocket connections for The Observatorium.
Broadcasts 'Pulse' events to all connected clients.
"""

import logging
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("sovereign.socket_manager")

class ConnectionManager:
    """The Nervous System. Relays impulses to connected observers."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Observer connected. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Handle disconnection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("Observer disconnected.")

    async def broadcast(self, event_type: str, payload: Dict[str, Any]):
        """
        Send a signal to all connected observers.
        
        Args:
            event_type: e.g., 'HEARTBEAT', 'STATUS_CHANGE', 'SYSTEM_ALERT'
            payload: JSON-serializable data
        """
        if not self.active_connections:
            return

        message = {
            "type": event_type,
            "data": payload
        }

        # Broadcast loop
        to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to transmit pulse to observer: {e}")
                to_remove.append(connection)
        
        # Cleanup dead connections
        for dead in to_remove:
            self.disconnect(dead)

# Singleton
_manager: ConnectionManager = ConnectionManager()

def get_connection_manager() -> ConnectionManager:
    return _manager
