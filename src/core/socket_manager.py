"""
VoidCat RDC: Sovereign Spirit - Connection Manager
==================================================
Version: 2.0.0
Author: Echo (E-01)
Date: 2026-01-24
Restored: 2026-02-26 by Vivy (Context Integrator)
Updated: 2026-03-05 — Tether Protocol thread subscriptions

Manages WebSocket connections for The Observatorium.
Broadcasts 'Pulse' events to all connected clients.
Supports thread-scoped subscriptions for the Tether Protocol.
"""

import logging
from typing import List, Dict, Any, Set

from fastapi import WebSocket

logger = logging.getLogger("sovereign.socket_manager")


class ConnectionManager:
    """The Nervous System. Relays impulses to connected observers."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self._thread_subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Observer connected. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Handle disconnection and clean up thread subscriptions."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Remove from all thread subscriptions
        empty_threads = []
        for thread_id, sockets in self._thread_subscriptions.items():
            sockets.discard(websocket)
            if not sockets:
                empty_threads.append(thread_id)
        for thread_id in empty_threads:
            del self._thread_subscriptions[thread_id]

        logger.info("Observer disconnected.")

    async def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
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
            "data": payload,
        }

        to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to transmit pulse to observer: {e}")
                to_remove.append(connection)

        for dead in to_remove:
            self.disconnect(dead)

    # =========================================================================
    # Tether Protocol — Thread Subscriptions
    # =========================================================================

    def subscribe(self, thread_id: str, websocket: WebSocket) -> None:
        """Subscribe a WebSocket to a specific thread's events."""
        if thread_id not in self._thread_subscriptions:
            self._thread_subscriptions[thread_id] = set()
        self._thread_subscriptions[thread_id].add(websocket)
        logger.debug(f"Socket subscribed to thread {thread_id}")

    def unsubscribe(self, thread_id: str, websocket: WebSocket) -> None:
        """Unsubscribe a WebSocket from a thread."""
        if thread_id in self._thread_subscriptions:
            self._thread_subscriptions[thread_id].discard(websocket)
            if not self._thread_subscriptions[thread_id]:
                del self._thread_subscriptions[thread_id]

    async def broadcast_to_thread(
        self, thread_id: str, event_type: str, payload: Dict[str, Any]
    ) -> None:
        """
        Send an event only to WebSockets subscribed to a specific thread.

        Falls back silently if no subscribers exist for the thread.
        """
        subscribers = self._thread_subscriptions.get(thread_id)
        if not subscribers:
            return

        message = {
            "type": event_type,
            "data": payload,
        }

        to_remove = []
        for ws in subscribers:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send thread event to subscriber: {e}")
                to_remove.append(ws)

        for dead in to_remove:
            self.disconnect(dead)


# Singleton
_manager: ConnectionManager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    return _manager
