import asyncio
import json
from datetime import datetime

import httpx
import websockets

BASE = "http://localhost:8090"
WS_URL = "ws://localhost:8090/ws/dashboard"
API_KEY = "dev-local"
AGENT_ID = "echo"


def now():
    return datetime.utcnow().isoformat() + "Z"


async def main():
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(
            f"{BASE}/api/tether/send",
            headers=headers,
            json={
                "agent_id": AGENT_ID,
                "content": "Please continue and report your next concrete action.",
                "sender_name": "Contractor",
            },
        )
        r.raise_for_status()
        send_data = r.json()

    thread_id = send_data["thread_id"]

    counts = {
        "REPLY_CHAIN_EVENT": 0,
        "TOOL_USE_EVENT": 0,
        "TOOL_USE_APPROVAL_REQUIRED": 0,
        "TETHER_MESSAGE": 0,
        "CMD_ACK": 0,
    }
    chain_statuses = []
    ack_cmds = []

    async with websockets.connect(
        WS_URL,
        additional_headers={"X-API-Key": API_KEY},
        max_size=2_000_000,
    ) as ws:
        await ws.send(json.dumps({"type": "TETHER_JOIN", "payload": {"thread_id": thread_id}}))
        await ws.send(
            json.dumps(
                {
                    "type": "TETHER_SEND",
                    "payload": {
                        "thread_id": thread_id,
                        "agent_id": AGENT_ID,
                        "content": "Drive a reply chain for this thread.",
                    },
                }
            )
        )

        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < 30:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                continue

            msg = json.loads(raw)
            t = msg.get("type")
            if t == "STATE_UPDATE":
                continue

            if t in counts:
                counts[t] += 1

            payload = msg.get("data") or msg.get("payload") or {}
            if t == "REPLY_CHAIN_EVENT":
                status = payload.get("chain_status")
                if status:
                    chain_statuses.append(status)
            elif t == "TOOL_USE_APPROVAL_REQUIRED":
                chain_id = payload.get("chain_id")
                if chain_id:
                    await ws.send(json.dumps({"type": "TOOL_USE_APPROVE", "payload": {"chain_id": chain_id}}))
            elif t == "CMD_ACK":
                ack_cmds.append(payload.get("cmd") or msg.get("cmd"))

    print("VERIFY_SUMMARY")
    print(json.dumps({
        "timestamp": now(),
        "thread_id": thread_id,
        "counts": counts,
        "chain_statuses": chain_statuses,
        "ack_cmds": ack_cmds,
        "saw_chain": counts["REPLY_CHAIN_EVENT"] > 0,
        "saw_tool": counts["TOOL_USE_EVENT"] > 0,
        "saw_approval": counts["TOOL_USE_APPROVAL_REQUIRED"] > 0,
        "saw_message": counts["TETHER_MESSAGE"] > 0,
    }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
