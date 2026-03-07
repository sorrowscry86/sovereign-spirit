import asyncio
import json
import websockets

WS_URL = "ws://localhost:8090/ws/dashboard"
CMDS = [
    {"type": "TOOL_USE_APPROVE", "payload": {"event_id": "e2e-approve-1"}},
    {"type": "TOOL_USE_DENY", "payload": {"event_id": "e2e-deny-1"}},
    {"type": "REPLY_CHAIN_RESUME", "payload": {"chain_id": "e2e-chain-1"}},
    {"type": "REPLY_CHAIN_CANCEL", "payload": {"chain_id": "e2e-chain-2"}},
]

async def wait_for_cmd_ack(ws, expected_cmd, timeout=6):
    end = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < end:
        msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=end - asyncio.get_event_loop().time()))
        if msg.get("type") == "CMD_ACK":
            payload = msg.get("payload", {})
            if payload.get("cmd") == expected_cmd:
                return {"ok": True, "ack": payload}
    return {"ok": False, "ack": None}

async def run():
    results = []
    async with websockets.connect(WS_URL, open_timeout=10, ping_interval=20) as ws:
        _ = await asyncio.wait_for(ws.recv(), timeout=10)
        for cmd in CMDS:
            await ws.send(json.dumps(cmd))
            try:
                res = await wait_for_cmd_ack(ws, cmd["type"], timeout=6)
            except Exception as e:
                res = {"ok": False, "error": str(e), "ack": None}
            results.append({"cmd": cmd["type"], **res})
    print("RESULT_START")
    print(json.dumps(results, indent=2))
    print("RESULT_END")

asyncio.run(run())
