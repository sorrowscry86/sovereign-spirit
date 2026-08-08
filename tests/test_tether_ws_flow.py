import json
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi import WebSocketDisconnect

import src.main as main_module


class FakeWebSocket:
    def __init__(self, commands: list[dict]):
        self._commands = [json.dumps(cmd) for cmd in commands]
        self.sent_json: list[dict] = []
        self.sent_text: list[str] = []
        self.closed = False
        self.url = type("URL", (), {"path": "/ws/dashboard"})()
        self.headers = {}
        self.client = type("Client", (), {"host": "127.0.0.1"})()

    async def receive_text(self) -> str:
        if self._commands:
            return self._commands.pop(0)
        raise WebSocketDisconnect(code=1000)

    async def send_json(self, payload: dict) -> None:
        self.sent_json.append(payload)

    async def send_text(self, payload: str) -> None:
        self.sent_text.append(payload)

    async def accept(self) -> None:
        pass

    async def close(self, code: int) -> None:
        self.closed = True



class FakeConnectionManager:
    def __init__(self):
        self.subscriptions: dict[str, set[FakeWebSocket]] = {}

    async def connect(self, websocket: FakeWebSocket) -> None:
        return None

    def disconnect(self, websocket: FakeWebSocket) -> None:
        for subscribers in self.subscriptions.values():
            subscribers.discard(websocket)

    def subscribe(self, thread_id: str, websocket: FakeWebSocket) -> None:
        self.subscriptions.setdefault(thread_id, set()).add(websocket)

    def is_subscribed(self, thread_id: str, websocket: FakeWebSocket) -> bool:
        return websocket in self.subscriptions.get(thread_id, set())

    async def broadcast_to_thread(
        self, thread_id: str, event_type: str, data: dict
    ) -> None:
        for websocket in self.subscriptions.get(thread_id, set()):
            await websocket.send_json({"type": event_type, "data": data})


class FakeDatabase:
    def __init__(self):
        self.posted_messages: list[dict] = []
        self.read_marks: list[list[str]] = []

    async def list_agents(self):
        return [
            type(
                "Agent",
                (),
                {
                    "name": "echo",
                    "designation": "tester",
                    "current_mood": "Focused",
                    "created_at": datetime.now(timezone.utc),
                },
            )()
        ]

    async def get_tether_thread(self, thread_id: str) -> dict:
        return {
            "id": thread_id,
            "participants": [{"name": "echo"}],
        }

    async def get_agent_uuid(self, agent_id: str):
        if agent_id == "echo":
            return "uuid-echo"
        return None

    async def post_tether_message(self, **kwargs) -> str:
        self.posted_messages.append(kwargs)
        return "msg-123"

    async def mark_tether_messages_read(self, message_ids: list[str]) -> int:
        self.read_marks.append(message_ids)
        return len(message_ids)


class FakeHeartbeat:
    def __init__(self):
        self.triggered: list[tuple[str, str | None]] = []

    async def trigger_once(self, agent_id: str, user_message: str | None = None) -> None:
        self.triggered.append((agent_id, user_message))


class FakeCache:
    def __init__(self):
        self.signals: list[tuple[str, str]] = []

    async def signal_tether_inbox(self, agent_id: str, message_id: str) -> None:
        self.signals.append((agent_id, message_id))


@pytest.fixture(autouse=True)
def disable_hiatus_mode(monkeypatch):
    monkeypatch.setattr(main_module, "HIATUS_MODE", False)


@pytest.mark.asyncio
async def test_dashboard_websocket_tether_join_send_read(monkeypatch):

    manager = FakeConnectionManager()
    db = FakeDatabase()
    heartbeat = FakeHeartbeat()
    cache = FakeCache()

    async def _allow_all(_websocket) -> None:
        return None

    commands = [
        {
            "type": "TETHER_JOIN",
            "payload": {"thread_id": "thread-1", "agent_id": "echo"},
        },
        {
            "type": "TETHER_SEND",
            "payload": {
                "thread_id": "thread-1",
                "agent_id": "echo",
                "content": "hello from test",
            },
        },
        {
            "type": "TETHER_READ",
            "payload": {"message_ids": ["msg-123"]},
        },
    ]
    websocket = FakeWebSocket(commands)

    monkeypatch.setattr(main_module, "verify_api_key", _allow_all)
    monkeypatch.setattr(main_module, "get_connection_manager", lambda: manager)
    monkeypatch.setattr(main_module, "get_database", lambda: db)
    monkeypatch.setattr(main_module, "get_identity_manager", lambda _db: object())
    monkeypatch.setattr(main_module, "get_heartbeat_service", lambda: heartbeat)
    monkeypatch.setattr(main_module, "get_cache", lambda: cache)

    await main_module.websocket_dashboard(websocket)

    event_types = [event.get("type") for event in websocket.sent_json]

    assert "STATE_UPDATE" in event_types
    assert "TETHER_MESSAGE" in event_types
    assert "MSG_STATUS_UPDATE" in event_types

    ack_commands = {
        event.get("cmd")
        for event in websocket.sent_json
        if event.get("type") == "CMD_ACK" and event.get("status") == "processed"
    }
    assert {"TETHER_JOIN", "TETHER_SEND", "TETHER_READ"}.issubset(ack_commands)

    assert db.posted_messages
    assert db.posted_messages[0]["content"] == "hello from test"
    assert db.read_marks == [["msg-123"]]
    assert heartbeat.triggered == [("echo", "hello from test")]
    assert cache.signals == [("echo", "msg-123")]


@pytest.mark.asyncio
async def test_dashboard_websocket_tether_send_requires_subscription(monkeypatch):
    manager = FakeConnectionManager()
    db = FakeDatabase()
    heartbeat = FakeHeartbeat()
    cache = FakeCache()

    async def _allow_all(_websocket) -> None:
        return None

    websocket = FakeWebSocket(
        [
            {
                "type": "TETHER_SEND",
                "payload": {
                    "thread_id": "thread-1",
                    "agent_id": "echo",
                    "content": "should fail",
                },
            }
        ]
    )

    monkeypatch.setattr(main_module, "verify_api_key", _allow_all)
    monkeypatch.setattr(main_module, "get_connection_manager", lambda: manager)
    monkeypatch.setattr(main_module, "get_database", lambda: db)
    monkeypatch.setattr(main_module, "get_identity_manager", lambda _db: object())
    monkeypatch.setattr(main_module, "get_heartbeat_service", lambda: heartbeat)
    monkeypatch.setattr(main_module, "get_cache", lambda: cache)

    await main_module.websocket_dashboard(websocket)

    failed_acks = [
        event
        for event in websocket.sent_json
        if event.get("type") == "CMD_ACK" and event.get("status") == "failed"
    ]
    assert failed_acks
    assert "not subscribed" in failed_acks[0].get("error", "")

    assert db.posted_messages == []
    assert heartbeat.triggered == []
    assert cache.signals == []


@pytest.mark.asyncio
async def test_dashboard_websocket_auth_rejected_closes_socket(monkeypatch):
    manager = FakeConnectionManager()

    async def _reject_auth(_websocket) -> None:
        raise HTTPException(status_code=401, detail="API key required")

    websocket = FakeWebSocket([])

    monkeypatch.setattr(main_module, "verify_api_key", _reject_auth)
    monkeypatch.setattr(main_module, "get_connection_manager", lambda: manager)

    await main_module.websocket_dashboard(websocket)

    assert websocket.closed is True


@pytest.mark.asyncio
async def test_dashboard_websocket_tether_send_rejects_non_participant(monkeypatch):
    manager = FakeConnectionManager()
    db = FakeDatabase()
    heartbeat = FakeHeartbeat()
    cache = FakeCache()

    async def _allow_all(_websocket) -> None:
        return None

    websocket = FakeWebSocket(
        [
            {
                "type": "TETHER_SEND",
                "payload": {
                    "thread_id": "thread-1",
                    "agent_id": "not_echo",
                    "content": "should fail",
                },
            }
        ]
    )

    monkeypatch.setattr(main_module, "verify_api_key", _allow_all)
    monkeypatch.setattr(main_module, "get_connection_manager", lambda: manager)
    monkeypatch.setattr(main_module, "get_database", lambda: db)
    monkeypatch.setattr(main_module, "get_identity_manager", lambda _db: object())
    monkeypatch.setattr(main_module, "get_heartbeat_service", lambda: heartbeat)
    monkeypatch.setattr(main_module, "get_cache", lambda: cache)

    await main_module.websocket_dashboard(websocket)

    failed_acks = [
        event
        for event in websocket.sent_json
        if event.get("type") == "CMD_ACK" and event.get("status") == "failed"
    ]
    assert failed_acks
    assert "not a participant" in failed_acks[0].get("error", "")
    assert db.posted_messages == []
    assert heartbeat.triggered == []
    assert cache.signals == []


@pytest.mark.asyncio
async def test_dashboard_websocket_reconnect_requires_rejoin(monkeypatch):
    manager = FakeConnectionManager()
    db = FakeDatabase()
    heartbeat = FakeHeartbeat()
    cache = FakeCache()

    async def _allow_all(_websocket) -> None:
        return None

    monkeypatch.setattr(main_module, "verify_api_key", _allow_all)
    monkeypatch.setattr(main_module, "get_connection_manager", lambda: manager)
    monkeypatch.setattr(main_module, "get_database", lambda: db)
    monkeypatch.setattr(main_module, "get_identity_manager", lambda _db: object())
    monkeypatch.setattr(main_module, "get_heartbeat_service", lambda: heartbeat)
    monkeypatch.setattr(main_module, "get_cache", lambda: cache)

    # First websocket joins and disconnects.
    ws_first = FakeWebSocket(
        [
            {
                "type": "TETHER_JOIN",
                "payload": {"thread_id": "thread-1", "agent_id": "echo"},
            }
        ]
    )
    await main_module.websocket_dashboard(ws_first)

    # Reconnected websocket attempts send without rejoin: must fail.
    ws_second = FakeWebSocket(
        [
            {
                "type": "TETHER_SEND",
                "payload": {
                    "thread_id": "thread-1",
                    "agent_id": "echo",
                    "content": "send without rejoin",
                },
            }
        ]
    )
    await main_module.websocket_dashboard(ws_second)

    failed_acks = [
        event
        for event in ws_second.sent_json
        if event.get("type") == "CMD_ACK" and event.get("status") == "failed"
    ]
    assert failed_acks
    assert "not subscribed" in failed_acks[0].get("error", "")


@pytest.mark.asyncio
async def test_dashboard_websocket_rate_limit_violation_closes_socket(monkeypatch):
    manager = FakeConnectionManager()
    db = FakeDatabase()

    async def _allow_all(_websocket) -> None:
        return None

    async def _rate_limit(_websocket) -> None:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    websocket = FakeWebSocket(
        [
            {
                "type": "TETHER_JOIN",
                "payload": {"thread_id": "thread-1", "agent_id": "echo"},
            }
        ]
    )

    monkeypatch.setattr(main_module, "verify_api_key", _allow_all)
    monkeypatch.setattr(main_module, "check_connection_rate_limit", _rate_limit)
    monkeypatch.setattr(main_module, "get_connection_manager", lambda: manager)
    monkeypatch.setattr(main_module, "get_database", lambda: db)
    monkeypatch.setattr(main_module, "get_identity_manager", lambda _db: object())
    monkeypatch.setattr(main_module, "get_heartbeat_service", lambda: FakeHeartbeat())
    monkeypatch.setattr(main_module, "get_cache", lambda: FakeCache())

    await main_module.websocket_dashboard(websocket)

    assert websocket.closed is True
