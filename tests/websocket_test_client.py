import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ws_test")

async def test_dashboard_stream():
    """
    Connects to the Dashboard WebSocket and verifies:
    1. Initial state reception.
    2. Heartbeat broadcast updates.
    3. Command acknowledgement (CMD_ACK).
    """
    uri = "ws://localhost:8090/ws/dashboard"
    logger.info(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            # 1. Verification of Initial State
            response = await websocket.recv()
            data = json.loads(response)
            logger.info(f"RECEIVED INITIAL: {data.get('type')}")
            if data.get("type") != "STATE_UPDATE":
                logger.error("Error: Expected STATE_UPDATE")
            
            # 2. Verification of Heartbeat Broadcast
            logger.info("Waiting for next broadcast update...")
            response = await websocket.recv()
            data = json.loads(response)
            logger.info(f"RECEIVED BROADCAST: {data.get('type')} - Uptime: {data.get('payload', {}).get('stats', {}).get('uptime')}s")

            # 3. Verification of Command Injection (GOD_STIMULI)
            logger.info("Injecting test stimuli...")
            cmd = {
                "type": "GOD_STIMULI",
                "payload": {
                    "agent_id": "sovereign-001",
                    "content": "TEST_STIMULI_FROM_VALIDATOR"
                }
            }
            await websocket.send(json.dumps(cmd))
            
            response = await websocket.recv()
            ack = json.loads(response)
            logger.info(f"RECEIVED ACK: {ack}")
            
            if ack.get("type") == "CMD_ACK" and ack.get("status") == "processed":
                logger.info("SUCCESS: Logic-Stream Verified.")
            else:
                logger.error("FAILURE: Command Acknowledgement mismatch.")

    except Exception as e:
        logger.error(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_dashboard_stream())
