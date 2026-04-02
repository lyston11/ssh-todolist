import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from backend.realtime import WebSocketHub
from backend.store import TodoStore, utc_ms


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class SyncHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_class, *, store: TodoStore, hub: WebSocketHub, ws_port: int) -> None:
        super().__init__(server_address, handler_class)
        self.store = store
        self.hub = hub
        self.ws_port = ws_port


class TodoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"status": "ok", "time": utc_ms(), "wsPort": self.server.ws_port})
            return

        if parsed.path == "/api/meta":
            self._send_json({"wsPort": self.server.ws_port, "wsPath": "/ws", "time": utc_ms()})
            return

        if parsed.path == "/api/todos":
            self._send_json({"items": self.server.store.list_todos(), "time": utc_ms()})
            return

        if parsed.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/todos":
            try:
                payload = self._read_json()
            except ValueError:
                return

            title = str(payload.get("title", "")).strip()
            if not title:
                self._send_error_json(HTTPStatus.BAD_REQUEST, "title is required")
                return

            todo = self.server.store.create_todo(title[:120])
            self.server.hub.broadcast_snapshot_sync()
            self._send_json(todo, status=HTTPStatus.CREATED)
            return

        if parsed.path == "/api/todos/clear-completed":
            deleted = self.server.store.clear_completed()
            self.server.hub.broadcast_snapshot_sync()
            self._send_json({"deleted": deleted})
            return

        self._send_error_json(HTTPStatus.NOT_FOUND, "endpoint not found")

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        todo_id = self._extract_todo_id(parsed.path)
        if todo_id is None:
            self._send_error_json(HTTPStatus.NOT_FOUND, "endpoint not found")
            return

        try:
            payload = self._read_json()
        except ValueError:
            return

        title = payload.get("title")
        completed = payload.get("completed")

        if title is not None:
            title = str(title).strip()
            if not title:
                self._send_error_json(HTTPStatus.BAD_REQUEST, "title cannot be empty")
                return
            title = title[:120]

        if completed is not None and not isinstance(completed, bool):
            self._send_error_json(HTTPStatus.BAD_REQUEST, "completed must be a boolean")
            return

        todo = self.server.store.update_todo(todo_id, title, completed)
        if todo is None:
            self._send_error_json(HTTPStatus.NOT_FOUND, "todo not found")
            return

        self.server.hub.broadcast_snapshot_sync()
        self._send_json(todo)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        todo_id = self._extract_todo_id(parsed.path)
        if todo_id is None:
            self._send_error_json(HTTPStatus.NOT_FOUND, "endpoint not found")
            return

        deleted = self.server.store.delete_todo(todo_id)
        if not deleted:
            self._send_error_json(HTTPStatus.NOT_FOUND, "todo not found")
            return

        self.server.hub.broadcast_snapshot_sync()
        self._send_json({"deleted": True})

    def _extract_todo_id(self, path: str) -> str | None:
        prefix = "/api/todos/"
        if not path.startswith(prefix) or path == "/api/todos/clear-completed":
            return None
        return path.removeprefix(prefix).strip() or None

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        try:
            parsed = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_error_json(HTTPStatus.BAD_REQUEST, "invalid json")
            raise ValueError("invalid json")

        if not isinstance(parsed, dict):
            self._send_error_json(HTTPStatus.BAD_REQUEST, "json body must be an object")
            raise ValueError("json body must be an object")

        return parsed

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _send_error_json(self, status: HTTPStatus, message: str) -> None:
        self._send_json({"error": message}, status=status)

    def log_message(self, format: str, *args) -> None:
        return


def create_http_server(host: str, port: int, store: TodoStore, hub: WebSocketHub, ws_port: int) -> SyncHTTPServer:
    return SyncHTTPServer((host, port), TodoHandler, store=store, hub=hub, ws_port=ws_port)


def run_http_server(server: SyncHTTPServer) -> None:
    server.serve_forever()
