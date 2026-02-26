"""
VoidCat RDC: Sovereign Spirit Core - Heartbeat Service
=======================================================
Version: 1.0.0
Author: Echo (E-01)
Date: 2026-01-23

AsyncIO service wrapper for the Heartbeat pulse loop.
Manages autonomous background operation of Sovereign Spirit agents.
"""

import asyncio
import logging
import os
from typing import Optional, Dict, List, Set

from src.core.heartbeat.pulse import (
    execute_pulse,
    calculate_next_interval,
)
from src.core.database import DatabaseClient, get_database
from src.core.graph import GraphClient, get_graph
from src.core.memory.stasis_chamber import StasisChamber
from src.core.cache import get_cache

logger = logging.getLogger("sovereign.heartbeat.service")

# =============================================================================
# Heartbeat Service
# =============================================================================

class HeartbeatService:
    """
    Manages the autonomous heartbeat loop for Sovereign Spirit agents.
    
    Features:
    - Start/stop service lifecycle
    - Register agents for autonomous monitoring
    - Manual trigger for single cycles
    - Graceful shutdown with task cleanup
    """
    
    def __init__(
        self,
        db: Optional[DatabaseClient] = None,
        graph: Optional[GraphClient] = None,
        stasis: Optional[StasisChamber] = None,
    ):
        self._db = db or get_database()
        self._graph = graph or get_graph()
        self._stasis = stasis or StasisChamber()
        self._cache = get_cache()
        self._running = False
        self._registered_agents: Set[str] = set()
        self._tasks: Dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self, agent_ids: Optional[List[str]] = None) -> None:
        """
        Start the heartbeat service.
        
        Args:
            agent_ids: Optional list of agent IDs to register on start.
                       If None, uses default agents from database.
        """
        if self._running:
            logger.warning("Heartbeat service already running")
            return
        
        self._running = True
        self._shutdown_event.clear()
        
        logger.info("=== HEARTBEAT SERVICE STARTING ===")
        
        # Register agents
        if agent_ids:
            for agent_id in agent_ids:
                await self.register_agent(agent_id)
        else:
            # Load default agents from environment variable or use defaults
            # Format: SOVEREIGN_DEFAULT_AGENTS="echo,ryuzu,beatrice"
            default_agents_str = os.getenv("SOVEREIGN_DEFAULT_AGENTS", "echo,ryuzu,beatrice")
            default_agents = [a.strip() for a in default_agents_str.split(",") if a.strip()]
            for agent_id in default_agents:
                agent = await self._db.get_agent_state(agent_id)
                if agent:
                    await self.register_agent(agent_id)
        
        # Start Auto-Chronicler
        self._chronicler_task = asyncio.create_task(self._chronicler_loop())
        logger.info("Auto-Chronicler daemon started")
        
        logger.info(f"=== HEARTBEAT SERVICE ONLINE: {len(self._registered_agents)} agents ===")
    
    async def stop(self) -> None:
        """
        Stop the heartbeat service and freeze state to stasis.
        """
        if not self._running:
            return
            
        logger.info("Stopping Heartbeat Service...")
        self._running = False
        self._shutdown_event.set()
        
        # Snapshot current state to Stasis for each agent
        for agent_id in self._registered_agents:
            try:
                # Capture working memory from cache
                history = await self._cache.get_messages(f"session_{agent_id}", limit=20)
                focus = await self._cache.get_focus(agent_id)
                
                snapshot = {
                    "agent_id": agent_id,
                    "working_memory": history,
                    "current_focus": focus,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                self._stasis.freeze(agent_id, snapshot)
                logger.info(f"State snapshot frozen for {agent_id} during shutdown.")
            except Exception as e:
                logger.error(f"Failed to freeze {agent_id} during shutdown: {e}")

        # Cancel chronicler
        if hasattr(self, '_chronicler_task') and not self._chronicler_task.done():
            self._chronicler_task.cancel()
            try:
                await self._chronicler_task
            except asyncio.CancelledError:
                pass
        
        # Cancel all tasks
        for agent_id, task in self._tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.debug(f"Cancelled pulse loop for {agent_id}")
        
        self._tasks.clear()
        self._registered_agents.clear()
        
        logger.info("=== HEARTBEAT SERVICE STOPPED ===")

    async def _chronicler_loop(self) -> None:
        """Background task to auto-update chronicles."""
        from src.core.chronicler import get_chronicler
        from src.core.visualization.timeline_renderer import TimelineRenderer
        
        logger.info("Chronicler loop started")
        renderer = TimelineRenderer()
        
        while self._running:
            try:
                # Update every 5 minutes (300s)
                interval = 300.0
                
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=interval,
                    )
                    break
                except asyncio.TimeoutError:
                    pass
                
                # Regenerate Timeline
                logger.debug("Auto-Chronicler: Regenerating timeline...")
                chronicler = get_chronicler()
                events = await chronicler.get_timeline(limit=500)
                path = renderer.generate_html_report(events)
                logger.debug(f"Auto-Chronicler: Timeline updated at {path}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto-Chronicler error: {e}")
                await asyncio.sleep(60)

    # =========================================================================
    # Agent Registration
    # =========================================================================
    
    async def register_agent(self, agent_id: str) -> bool:
        """
        Register an agent for autonomous heartbeat monitoring.
        
        Creates a background task that runs the pulse loop.
        """
        if agent_id in self._registered_agents:
            logger.warning(f"Agent {agent_id} already registered")
            return False
        
        # Verify agent exists
        agent = await self._db.get_agent_state(agent_id)
        if not agent:
            logger.error(f"Cannot register unknown agent: {agent_id}")
            return False
        
        # Create pulse loop task
        self._registered_agents.add(agent_id)
        
        # Restore state from Stasis if available
        await self._restore_agent_state(agent_id)
        
        task = asyncio.create_task(self._pulse_loop(agent_id))
        self._tasks[agent_id] = task
        
        logger.info(f"Registered agent for heartbeat: {agent_id}")
        return True

    async def _restore_agent_state(self, agent_id: str):
        """Attempts to restore agent working memory and focus from Stasis."""
        try:
            ptr_path = f"stasis_tanks/{agent_id}.ptr"
            snapshot = self._stasis.thaw(ptr_path)
            
            if snapshot:
                logger.info(f"Restoring state for {agent_id} from Stasis...")
                
                # Restore to Redis cache
                if "working_memory" in snapshot:
                    # Invert list because push_message uses lpush
                    for msg in reversed(snapshot["working_memory"]):
                        await self._cache.push_message(f"session_{agent_id}", msg)
                
                if "current_focus" in snapshot and snapshot["current_focus"]:
                    await self._cache.set_focus(agent_id, snapshot["current_focus"])
                    
                logger.info(f"State restoration complete for {agent_id}.")
            else:
                logger.debug(f"No stasis snapshot found for {agent_id}. Starting fresh.")
        except Exception as e:
            logger.error(f"Failed to restore state for {agent_id} from stasis: {e}")
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from heartbeat monitoring.
        """
        if agent_id not in self._registered_agents:
            return False
        
        # Cancel task
        if agent_id in self._tasks:
            task = self._tasks[agent_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del self._tasks[agent_id]
        
        self._registered_agents.discard(agent_id)
        logger.info(f"Unregistered agent from heartbeat: {agent_id}")
        return True
    
    # =========================================================================
    # Pulse Loop
    # =========================================================================
    
    async def _pulse_loop(self, agent_id: str) -> None:
        """
        Main pulse loop for a single agent.
        
        Runs continuously until service shutdown or agent unregistration.
        """
        logger.info(f"Starting pulse loop for: {agent_id}")
        
        while self._running and agent_id in self._registered_agents:
            try:
                # Calculate next interval
                interval = calculate_next_interval()
                logger.debug(f"Next pulse for {agent_id} in {interval:.1f}s")
                
                # Wait for interval or shutdown
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=interval,
                    )
                    # Shutdown event triggered
                    break
                except asyncio.TimeoutError:
                    # Normal timeout, continue to pulse
                    pass
                
                # Execute pulse
                result = await execute_pulse(agent_id, self._db, self._graph)
                
                # Broadcast via WebSocket (The Observatorium)
                from src.core.socket_manager import get_connection_manager
                manager = get_connection_manager()
                await manager.broadcast("HEARTBEAT", {
                    "agent_id": agent_id,
                    "action": result.get("action", "UNKNOWN"),
                    "thought": result.get("thought", ""),
                    "timestamp": str(result.get("timestamp", ""))
                })
                
            except asyncio.CancelledError:
                logger.debug(f"Pulse loop cancelled: {agent_id}")
                break
            except Exception as e:
                logger.error(f"Pulse loop error for {agent_id}: {e}")
                # Continue loop despite errors
                await asyncio.sleep(30)
        
        logger.info(f"Pulse loop ended: {agent_id}")
    
    # =========================================================================
    # Manual Trigger
    # =========================================================================
    
    async def trigger_once(self, agent_id: str, user_message: Optional[str] = None) -> dict:
        """
        Manually trigger a single heartbeat cycle for an agent.
        
        This is called by the /agent/{id}/cycle endpoint and /api/messages/send.
        
        Args:
            agent_id: The agent to trigger
            user_message: Optional user message to inject as context
        """
        return await execute_pulse(agent_id, self._db, self._graph, user_message=user_message)
    
    # =========================================================================
    # Status
    # =========================================================================
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def registered_agents(self) -> List[str]:
        return list(self._registered_agents)
    
    def get_status(self) -> dict:
        """Get current service status."""
        return {
            "running": self._running,
            "registered_agents": list(self._registered_agents),
            "active_tasks": len([t for t in self._tasks.values() if not t.done()]),
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_heartbeat_service: Optional[HeartbeatService] = None


def get_heartbeat_service() -> HeartbeatService:
    """Get or create the singleton heartbeat service."""
    global _heartbeat_service
    if _heartbeat_service is None:
        _heartbeat_service = HeartbeatService()
    return _heartbeat_service
