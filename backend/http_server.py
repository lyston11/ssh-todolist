import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from backend.auth import AuthError, extract_token_from_request, validate_token
from backend.realtime import WebSocketHub
from backend.service import TodoService, TodoServiceError
from backend.store import TodoStore


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class SyncHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address,
        handler_class,
        *,
        store: TodoStore,
        hub: WebSocketHub,
        ws_port: int,
        static_root: Path | None,
        auth_token: str | None,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.service = TodoService(store=store, hub=hub, ws_port=ws_port, auth_token=auth_token)
        self.static_root = static_root
        self.auth_token = auth_token


class TodoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        server = args[2] if len(args) >= 3 else None
        static_root = getattr(server, "static_root", None)
        resolved_directory = directory or str(static_root or PROJECT_ROOT)
        super().__init__(*args, directory=resolved_directory, **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json(self.server.service.get_health_payload())
            return

        if parsed.path.startswith("/api/") and not self._require_api_auth(parsed.path):
            return

        if parsed.path == "/api/meta":
            self._send_json(self.server.service.get_meta_payload())
            return

        if parsed.path == "/api/snapshot":
            self._send_json(self.server.service.get_snapshot_payload())
            return

        if parsed.path == "/api/lists":
            self._send_json(self.server.service.list_lists_payload())
            return

        if parsed.path == "/api/todos":
            self._send_json(self.server.service.list_todos_payload())
            return

        if self.server.static_root is None:
            self._send_error_json(HTTPStatus.NOT_FOUND, "static app is not served by ssh-todolist-services")
            return

        if parsed.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/") and not self._require_api_auth(parsed.path):
            return

        if parsed.path == "/api/lists":
            self._handle_json_request(
                lambda payload: self.server.service.create_list(payload),
                status=HTTPStatus.CREATED,
            )
            return

        if parsed.path == "/api/todos":
            self._handle_json_request(
                lambda payload: self.server.service.create_todo(payload),
                status=HTTPStatus.CREATED,
            )
            return

        if parsed.path == "/api/todos/clear-completed":
            self._handle_json_request(lambda payload: self.server.service.clear_completed_todos(payload))
            return

        self._send_error_json(HTTPStatus.NOT_FOUND, "endpoint not found")

    def do_PATCH(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/") and not self._require_api_auth(parsed.path):
            return

        list_id = self._extract_list_id(parsed.path)
        if list_id is not None:
            self._handle_json_request(lambda payload: self.server.service.update_list(list_id, payload))
            return

        todo_id = self._extract_todo_id(parsed.path)
        if todo_id is None:
            self._send_error_json(HTTPStatus.NOT_FOUND, "endpoint not found")
            return

        self._handle_json_request(lambda payload: self.server.service.update_todo(todo_id, payload))

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/") and not self._require_api_auth(parsed.path):
            return

        list_id = self._extract_list_id(parsed.path)
        if list_id is not None:
            try:
                self._send_json(self.server.service.delete_list(list_id))
            except TodoServiceError as error:
                self._send_error_json(error.status_code, error.message)
            return

        todo_id = self._extract_todo_id(parsed.path)
        if todo_id is None:
            self._send_error_json(HTTPStatus.NOT_FOUND, "endpoint not found")
            return

        try:
            self._send_json(self.server.service.delete_todo(todo_id))
        except TodoServiceError as error:
            self._send_error_json(error.status_code, error.message)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        super().end_headers()

    def _require_api_auth(self, path: str) -> bool:
        if path == "/api/health":
            return True

        provided_token = extract_token_from_request(self.headers, self.path)
        if not validate_token(self.server.auth_token, provided_token):
            auth_error = AuthError()
            self._send_error_json(auth_error.status_code, auth_error.message)
            return False
        return True

    def _extract_todo_id(self, path: str) -> str | None:
        prefix = "/api/todos/"
        if not path.startswith(prefix) or path == "/api/todos/clear-completed":
            return None
        return path.removeprefix(prefix).strip() or None

    def _extract_list_id(self, path: str) -> str | None:
        prefix = "/api/lists/"
        if not path.startswith(prefix):
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

    def _handle_json_request(self, handler, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = {}
        if self.command in {"POST", "PATCH"}:
            try:
                payload = self._read_json()
            except ValueError:
                return

        try:
            self._send_json(handler(payload), status=status)
        except TodoServiceError as error:
            self._send_error_json(error.status_code, error.message)

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


def create_http_server(
    host: str,
    port: int,
    store: TodoStore,
    hub: WebSocketHub,
    ws_port: int,
    static_root: Path | None = None,
    auth_token: str | None = None,
) -> SyncHTTPServer:
    return SyncHTTPServer(
        (host, port),
        TodoHandler,
        store=store,
        hub=hub,
        ws_port=ws_port,
        static_root=static_root,
        auth_token=auth_token,
    )


def run_http_server(server: SyncHTTPServer) -> None:
    server.serve_forever()
