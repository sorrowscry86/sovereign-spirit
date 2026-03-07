import asyncio
import json
from datetime import datetime

import requests
import websockets

BASE = "http://localhost:8090"
WS_URL = "ws://localhost:8090/ws/dashboard"
HEADERS = {"X-API-Key": "dev-local", "Content-Type": "application/json"}


def warmup_and_get_thread(agent_id: str) -> str:
    payload = {
        "agent_id": agent_id,
        "content": "Verifier warmup for lifecycle event capture",
        "sender_name": "Verifier",
    }
    r = requests.post(f"{BASE}/api/tether/send", headers=HEADERS, data=json.dumps(payload), timeout=20)
    r.raise_for_status()
    data = r.json()
    return data["thread_id"]


async def run() -> None:
    thread_id = warmup_and_get_thread("echo")
    summary = {
        "thread_id": thread_id,
        "acks": [],
        "reply_chain_events": [],
        "tool_use_events": [],
        "approval_events": [],
        "other_events": {},
        "started_at": datetime.utcnow().isoformat() + "Z",
    }

    async with websockets.connect(WS_URL, open_timeout=10, ping_interval=20) as ws:
        # Consume initial STATE_UPDATE
        first = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        summary["other_events"][first.get("type", "UNKNOWN")] = 1

        await ws.send(json.dumps({
            "type": "TETHER_JOIN",
            "payload": {"thread_id": thread_id},
        }))

        # Trigger a fresh turn through websocket path
        await ws.send(json.dumps({
            "type": "TETHER_SEND",
            "payload": {
                "thread_id": thread_id,
                "agent_id": "echo",
                "content": "Please process this through the reply chain verifier.",
            },
        }))

        deadline = asyncio.get_event_loop().time() + 55
        while asyncio.get_event_loop().time() < deadline:
            remaining = max(0.1, deadline - asyncio.get_event_loop().time())
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                break

            msg = json.loads(raw)
            msg_type = msg.get("type", "UNKNOWN")
            payload = msg.get("data") or msg.get("payload") or msg

            if msg_type == "CMD_ACK":
                summary["acks"].append(payload)
            elif msg_type == "REPLY_CHAIN_EVENT":
                summary["reply_chain_events"].append(payload)
            elif msg_type == "TOOL_USE_EVENT":
                summary["tool_use_events"].append(payload)
            elif msg_type == "TOOL_USE_APPROVAL_REQUIRED":
                summary["approval_events"].append(payload)
            elif msg_type != "STATE_UPDATE":
                summary["other_events"][msg_type] = summary["other_events"].get(msg_type, 0) + 1

            # Exit early once we observed completed or failed chain
            if any(
                e.get("chain_status") in {"completed", "failed"}
                for e in summary["reply_chain_events"]
            ):
                break

    summary["finished_at"] = datetime.utcnow().isoformat() + "Z"
    print("RESULT_START")
    print(json.dumps(summary, indent=2))
    print("RESULT_END")


if __name__ == "__main__":
    asyncio.run(run())
