import asyncio
import json
import uuid
from datetime import datetime

import httpx
import websockets

BASE = "http://localhost:8090"
WS_URL = "ws://localhost:8090/ws/dashboard"
API_KEY = "dev-local"
AGENT_ID = "echo"


def ts():
    return datetime.utcnow().isoformat() + "Z"


async def main():
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        send_resp = await client.post(
            f"{BASE}/api/tether/send",
            headers=headers,
            json={
                "agent_id": AGENT_ID,
                "content": "Please continue our current task and provide a concrete next action.",
                "sender_name": "Contractor",
            },
        )
        send_resp.raise_for_status()
        send_data = send_resp.json()

    thread_id = send_data["thread_id"]
    print(f"[{ts()}] send thread_id={thread_id} msg_id={send_data.get('id')}")

    events = []
    got_chain = False
    got_message = False
    got_tool = False
    got_approval = False

    async with websockets.connect(
        WS_URL,
        additional_headers={"X-API-Key": API_KEY},
        max_size=4_000_000,
    ) as ws:
        await ws.send(json.dumps({"type": "TETHER_JOIN", "payload": {"thread_id": thread_id}}))

        # send one more message through websocket command path
        await ws.send(
            json.dumps(
                {
                    "type": "TETHER_SEND",
                    "payload": {
                        "thread_id": thread_id,
                        "agent_id": AGENT_ID,
                        "content": "Confirm chain tracking and respond with your next concrete step.",
                    },
                }
            )
        )

        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < 35:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                continue

            msg = json.loads(raw)
            event_type = msg.get("type")
            data = msg.get("data") or msg.get("payload") or msg
            events.append({"type": event_type, "data": data})

            if event_type == "REPLY_CHAIN_EVENT":
                got_chain = True
            elif event_type == "TETHER_MESSAGE":
                got_message = True
            elif event_type == "TOOL_USE_EVENT":
                got_tool = True
            elif event_type == "TOOL_USE_APPROVAL_REQUIRED":
                got_approval = True
                chain_id = data.get("chain_id")
                if chain_id:
                    await ws.send(
                        json.dumps(
                            {
                                "type": "TOOL_USE_APPROVE",
                                "payload": {"chain_id": chain_id},
                            }
                        )
                    )

        print("RESULT_START")
        print(
            json.dumps(
                {
                    "thread_id": thread_id,
                    "got_chain": got_chain,
                    "got_message": got_message,
                    "got_tool": got_tool,
                    "got_approval": got_approval,
                    "event_count": len(events),
                    "sample": events[:20],
                },
                indent=2,
                default=str,
            )
        )
        print("RESULT_END")


if __name__ == "__main__":
    asyncio.run(main())
