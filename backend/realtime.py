import asyncio
import json

from backend.auth import AuthError, extract_token_from_request, validate_token
from backend.store import TodoStore, utc_ms


class WebSocketHub:
    def __init__(self, store: TodoStore) -> None:
        self.store = store
        self.clients = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    async def register(self, websocket) -> None:
        self.clients.add(websocket)
        await self.send_snapshot(websocket)

    async def unregister(self, websocket) -> None:
        self.clients.discard(websocket)

    async def send_snapshot(self, websocket) -> None:
        lists = self.store.list_lists()
        payload = {
            "type": "todos.snapshot",
            "lists": lists,
            "items": self.store.list_todos(),
            "defaultListId": self.store.get_default_list_id() if lists else None,
            "time": utc_ms(),
        }
        await websocket.send(json.dumps(payload, ensure_ascii=False))

    async def broadcast_snapshot(self) -> None:
        if not self.clients:
            return

        lists = self.store.list_lists()
        payload = json.dumps(
            {
                "type": "todos.snapshot",
                "lists": lists,
                "items": self.store.list_todos(),
                "defaultListId": self.store.get_default_list_id() if lists else None,
                "time": utc_ms(),
            },
            ensure_ascii=False,
        )

        disconnected = []
        for websocket in list(self.clients):
            try:
                await websocket.send(payload)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.clients.discard(websocket)

    def broadcast_snapshot_sync(self) -> None:
        if self.loop is None:
            return
        asyncio.run_coroutine_threadsafe(self.broadcast_snapshot(), self.loop)


def build_websocket_process_request(expected_token: str | None):
    async def process_request(connection, request):
        provided_token = extract_token_from_request(
            request.headers,
            request.path,
            allow_query_token=True,
        )
        if not validate_token(expected_token, provided_token):
            auth_error = AuthError()
            return connection.respond(auth_error.status_code, f"{auth_error.message}\n")
        return None

    return process_request


async def websocket_handler(websocket, hub: WebSocketHub) -> None:
    await hub.register(websocket)
    try:
        async for message in websocket:
            if message == "ping":
                await websocket.send("pong")
    finally:
        await hub.unregister(websocket)
