
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.core.database import get_database
from src.core.graph import get_graph
from src.core.heartbeat.service import get_heartbeat_service

async def main():
    print("Initializing...")
    db = get_database()
    graph = get_graph()
    await db.initialize()
    await graph.initialize()
    
    hb = get_heartbeat_service()
    # We don't need to start() the service to trigger once, 
    # BUT we need the WebSocket socket_manager to be available.
    # The socket_manager is a singleton, but it needs an event loop.
    # The HeartbeatService.trigger_once calls execute_pulse.
    # Wait, execute_pulse logic was modified to broadcast ONLY if called inside the loop in service.py?
    # No, I modified service.py _pulse_loop. 
    # trigger_once calls execute_pulse directly. 
    # I need to modify trigger_once to ALSO broadcast, or just call execute_pulse and broadcast manually here.
    
    print("Triggering pulse for 'echo'...")
    from src.core.heartbeat.pulse import execute_pulse
    result = await execute_pulse("echo", db, graph)
    print(f"Pulse result: {result}")
    
    # Manually broadcast since we are outside the service loop
    # Wait, the backend process (Uvicorn) has the WebSocket connections.
    # THIS script runs in a SEPARATE process.
    # The ConnectionManager singleton in THIS process is distinct from the one in Uvicorn!
    # A standalone script CANNOT broadcast to the Uvicorn websockets via the singleton memory.
    
    # We must use Redis/PubSub if we want cross-process broadcasting, OR hit an API endpoint that triggers the pulse.
    # Does the middleware have a POST /pulse endpoint?
    # src/api/agents.py might.
    
    print("Done. (Note: Direct broadcast impossible from separate process without Redis/API)")

if __name__ == "__main__":
    asyncio.run(main())
