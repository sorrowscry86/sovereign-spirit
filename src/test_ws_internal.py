import asyncio
import json
import websockets
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ws_internal")

async def test_internal():
    uri = "ws://localhost:8000/ws/dashboard"
    logger.info(f"Connecting to internal endpoint: {uri}")
    try:
        async with websockets.connect(uri, timeout=5) as websocket:
            response = await websocket.recv()
            logger.info(f"INTERNAL SUCCESS: {json.loads(response).get('type')}")
    except Exception as e:
        logger.error(f"INTERNAL FAILURE: {e}")

if __name__ == "__main__":
    asyncio.run(test_internal())
