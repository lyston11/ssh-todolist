import asyncio
import json

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
        payload = {
            "type": "todos.snapshot",
            "items": self.store.list_todos(),
            "time": utc_ms(),
        }
        await websocket.send(json.dumps(payload, ensure_ascii=False))

    async def broadcast_snapshot(self) -> None:
        if not self.clients:
            return

        payload = json.dumps(
            {
                "type": "todos.snapshot",
                "items": self.store.list_todos(),
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


async def websocket_handler(websocket, hub: WebSocketHub) -> None:
    await hub.register(websocket)
    try:
        async for message in websocket:
            if message == "ping":
                await websocket.send("pong")
    finally:
        await hub.unregister(websocket)
