import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from backend.auth import AuthError
from backend.admin_activity import AdminActivityFeed
from backend.admin_config import AdminConfigStore
from backend.http_admin_assets import AdminAssetNotFoundError, build_admin_asset_response
from backend.http_auth import require_api_request_auth
from backend.http_logging import (
    build_http_access_log_message,
    get_http_logger,
    normalize_http_log_mode,
    should_log_http_request,
)
from backend.http_responses import (
    HttpResponsePayload,
    JsonBodyError,
    build_json_error_response,
    build_json_response,
    parse_json_object,
)
from backend.http_routes import (
    AdminAssetRouteAction,
    RootRouteAction,
    ServiceRouteAction,
    match_route,
)
from backend.realtime import WebSocketHub
from backend.service import TodoService
from backend.service_errors import TodoServiceError
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
        host: str,
        port: int,
        ws_port: int,
        static_root: Path | None,
        auth_token: str | None,
        public_base_url: str | None,
        public_ws_base_url: str | None,
        app_web_url: str | None,
        app_deep_link_base: str | None,
        http_log_mode: str,
        admin_config_store: AdminConfigStore | None = None,
        admin_activity_feed: AdminActivityFeed | None = None,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.service = TodoService(
            store=store,
            hub=hub,
            host=host,
            port=port,
            ws_port=ws_port,
            admin_entry_path="/" if static_root is None else "/admin",
            admin_alias_path="/admin" if static_root is None else None,
            auth_token=auth_token,
            public_base_url=public_base_url,
            public_ws_base_url=public_ws_base_url,
            app_web_url=app_web_url,
            app_deep_link_base=app_deep_link_base,
            admin_config_store=admin_config_store,
            admin_activity_feed=admin_activity_feed,
        )
        self.static_root = static_root
        self.auth_token = auth_token
        self.admin_config_store = admin_config_store
        self.admin_activity_feed = admin_activity_feed
        self.http_log_mode = normalize_http_log_mode(
            admin_config_store.snapshot().http_log_mode if admin_config_store is not None else http_log_mode
        )
        self.http_logger = get_http_logger()


class TodoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        server = args[2] if len(args) >= 3 else None
        static_root = getattr(server, "static_root", None)
        resolved_directory = directory or str(static_root or PROJECT_ROOT)
        super().__init__(*args, directory=resolved_directory, **kwargs)

    def do_GET(self) -> None:
        self._dispatch_request("GET")

    def do_POST(self) -> None:
        self._dispatch_request("POST")

    def do_PATCH(self) -> None:
        self._dispatch_request("PATCH")

    def do_DELETE(self) -> None:
        self._dispatch_request("DELETE")

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        super().end_headers()

    def _dispatch_request(self, method: str) -> None:
        self._request_started_at = time.perf_counter()
        self._request_method = method
        self._request_path = self.path
        parsed = urlparse(self.path)
        route_match = match_route(method, parsed.path)
        if route_match is not None:
            route, params = route_match.route, route_match.params
            if route.requires_auth and not self._require_api_auth(parsed.path):
                return

            self._execute_route(route.action, params)
            return

        if method == "GET":
            self._serve_static_fallback(parsed)
            return

        self._send_error_response(HTTPStatus.NOT_FOUND, "endpoint not found")

    def _serve_static_fallback(self, parsed) -> None:
        if self.server.static_root is None:
            self._send_error_response(HTTPStatus.NOT_FOUND, "static app is not served by ssh-todolist-services")
            return

        if parsed.path == "/":
            self.path = "/index.html"

        super().do_GET()

    def _execute_route(
        self,
        action: RootRouteAction | AdminAssetRouteAction | ServiceRouteAction,
        params: dict[str, str],
    ) -> None:
        if isinstance(action, RootRouteAction):
            self._handle_root_action()
            return

        if isinstance(action, AdminAssetRouteAction):
            self._handle_admin_asset_action(action, params)
            return

        if isinstance(action, ServiceRouteAction):
            self._execute_bound_service_action(action, params)
            return

        raise TypeError(f"unsupported route action: {type(action)!r}")

    def _handle_root_action(self) -> None:
        if self.server.static_root is None:
            self._send_admin_asset("index.html")
            return

        self.path = "/index.html"
        super().do_GET()

    def _handle_admin_asset_action(self, action: AdminAssetRouteAction, params: dict[str, str]) -> None:
        self._send_admin_asset(action.resolve_asset_path(params))

    def _require_api_auth(self, path: str) -> bool:
        try:
            require_api_request_auth(self.server.auth_token, self.headers, path)
        except AuthError as auth_error:
            self._send_error_response(auth_error.status_code, auth_error.message)
            return False
        return True

    def _read_json(self) -> dict:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise JsonBodyError("invalid Content-Length header") from error

        raw_body = self.rfile.read(content_length) if content_length else b"{}"
        return parse_json_object(raw_body)

    def _execute_json_service_action(
        self,
        action,
        *,
        status: HTTPStatus = HTTPStatus.OK,
        response_builder=build_json_response,
    ) -> None:
        try:
            payload = self._read_json()
        except JsonBodyError as error:
            self._send_error_response(error.status_code, error.message)
            return

        self._execute_service_action(
            lambda: action(payload),
            status=status,
            response_builder=response_builder,
        )

    def _execute_bound_service_action(self, action: ServiceRouteAction, params: dict[str, str]) -> None:
        bound_action = action.bind(self.server.service, params, self.headers)
        if bound_action is None:
            self._send_error_response(HTTPStatus.NOT_FOUND, "endpoint not found")
            return

        if bound_action.expects_request_body:
            self._execute_json_service_action(
                bound_action.execute,
                status=bound_action.status,
                response_builder=bound_action.response_builder,
            )
            return

        self._execute_service_action(
            lambda: bound_action.execute(),
            status=bound_action.status,
            response_builder=bound_action.response_builder,
        )

    def _execute_service_action(
        self,
        action,
        *,
        status: HTTPStatus = HTTPStatus.OK,
        response_builder=build_json_response,
    ) -> None:
        try:
            payload = action()
        except TodoServiceError as error:
            self._send_error_response(error.status_code, error.message)
            return

        self._send_response(response_builder(payload, status=status))

    def _send_response(self, response: HttpResponsePayload) -> None:
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(response.body)

    def _send_admin_asset(self, relative_path: str) -> None:
        try:
            response = build_admin_asset_response(relative_path)
        except AdminAssetNotFoundError as error:
            self._send_error_response(error.status_code, error.message)
            return

        self._send_response(response)

    def _send_error_response(self, status: HTTPStatus, message: str) -> None:
        self._send_response(build_json_error_response(status, message))

    def log_request(self, code="-", size="-") -> None:
        status_code = _coerce_status_code(code)
        if not should_log_http_request(_resolve_http_log_mode(self.server), status_code):
            return

        payload_size = _coerce_optional_int(size)
        started_at = getattr(self, "_request_started_at", None)
        duration_ms = None
        if isinstance(started_at, (int, float)):
            duration_ms = (time.perf_counter() - started_at) * 1000

        message = build_http_access_log_message(
            client_ip=self.client_address[0] if self.client_address else "-",
            method=getattr(self, "_request_method", self.command or "-"),
            path=getattr(self, "_request_path", self.path or "-"),
            status_code=status_code,
            size=payload_size,
            duration_ms=duration_ms,
        )

        if status_code is not None and status_code >= 400:
            self.server.http_logger.warning(message)
            return

        self.server.http_logger.info(message)

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
    public_base_url: str | None = None,
    public_ws_base_url: str | None = None,
    app_web_url: str | None = None,
    app_deep_link_base: str | None = None,
    http_log_mode: str = "errors",
    admin_config_store: AdminConfigStore | None = None,
    admin_activity_feed: AdminActivityFeed | None = None,
) -> SyncHTTPServer:
    return SyncHTTPServer(
        (host, port),
        TodoHandler,
        store=store,
        hub=hub,
        host=host,
        port=port,
        ws_port=ws_port,
        static_root=static_root,
        auth_token=auth_token,
        public_base_url=public_base_url,
        public_ws_base_url=public_ws_base_url,
        app_web_url=app_web_url,
        app_deep_link_base=app_deep_link_base,
        http_log_mode=http_log_mode,
        admin_config_store=admin_config_store,
        admin_activity_feed=admin_activity_feed,
    )


def run_http_server(server: SyncHTTPServer) -> None:
    server.serve_forever()


def _coerce_status_code(value) -> int | None:
    if isinstance(value, HTTPStatus):
        return int(value)
    if isinstance(value, int):
        return value

    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _coerce_optional_int(value) -> int | None:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _resolve_http_log_mode(server: SyncHTTPServer) -> str:
    config_store = getattr(server, "admin_config_store", None)
    if config_store is None:
        return server.http_log_mode
    return normalize_http_log_mode(config_store.snapshot().http_log_mode)
