import argparse
import asyncio
import json
import os
import threading
from pathlib import Path

from websockets.asyncio.server import serve

from backend.connection import has_trustworthy_remote_candidate
from backend.http_server import create_http_server, run_http_server
from backend.realtime import WebSocketHub, build_websocket_process_request, websocket_handler
from backend.store import TodoStore


PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATABASE_DIR / "todos.db"
DEFAULT_AUTH_TOKEN = os.environ.get("SSH_TODOLIST_TOKEN", "").strip() or None
DEFAULT_PUBLIC_BASE_URL = os.environ.get("SSH_TODOLIST_PUBLIC_BASE_URL", "").strip() or None
DEFAULT_PUBLIC_WS_BASE_URL = os.environ.get("SSH_TODOLIST_PUBLIC_WS_BASE_URL", "").strip() or None
DEFAULT_APP_WEB_URL = os.environ.get("SSH_TODOLIST_APP_WEB_URL", "").strip() or None
DEFAULT_APP_DEEP_LINK_BASE = os.environ.get("SSH_TODOLIST_APP_DEEP_LINK_BASE", "").strip() or "com.lyston11.sshtodolist://connect"
DEFAULT_PRINT_CONNECT_SECRETS = os.environ.get("SSH_TODOLIST_PRINT_CONNECT_SECRETS", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Focus List sync server.")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind. Use 0.0.0.0 for Tailscale access.")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind.")
    parser.add_argument("--ws-port", type=int, default=None, help="WebSocket port. Defaults to HTTP port + 1.")
    parser.add_argument("--db", type=Path, default=DATABASE_PATH, help="SQLite database path.")
    parser.add_argument(
        "--web-root",
        type=Path,
        default=None,
        help="Optional static app directory to serve alongside the API.",
    )
    parser.add_argument(
        "--token",
        default=DEFAULT_AUTH_TOKEN,
        help="Optional shared token for REST and WebSocket authentication. Can also come from SSH_TODOLIST_TOKEN.",
    )
    parser.add_argument(
        "--public-base-url",
        default=DEFAULT_PUBLIC_BASE_URL,
        help="Optional public HTTP base URL to advertise to clients, for example https://todo.example.com.",
    )
    parser.add_argument(
        "--public-ws-base-url",
        default=DEFAULT_PUBLIC_WS_BASE_URL,
        help="Optional public WebSocket base URL to advertise, for example wss://todo.example.com.",
    )
    parser.add_argument(
        "--app-web-url",
        default=DEFAULT_APP_WEB_URL,
        help="Optional web app URL used to generate import links, for example https://todo-app.example.com.",
    )
    parser.add_argument(
        "--app-deep-link-base",
        default=DEFAULT_APP_DEEP_LINK_BASE,
        help="Optional mobile deep-link base used to generate import links, for example com.lyston11.sshtodolist://connect.",
    )
    parser.add_argument(
        "--print-connect-secrets",
        action="store_true",
        default=DEFAULT_PRINT_CONNECT_SECRETS,
        help="Print token-bearing import payloads to the terminal. Disabled by default for safety.",
    )
    args = parser.parse_args()

    store = TodoStore(args.db)
    hub = WebSocketHub(store)
    ws_port = args.ws_port or (args.port + 1)
    web_root = args.web_root.resolve() if args.web_root is not None else None
    auth_token = None
    if isinstance(args.token, str):
        auth_token = args.token.strip() or None
    http_server = create_http_server(
        args.host,
        args.port,
        store,
        hub,
        ws_port,
        static_root=web_root,
        auth_token=auth_token,
        public_base_url=args.public_base_url,
        public_ws_base_url=args.public_ws_base_url,
        app_web_url=args.app_web_url,
        app_deep_link_base=args.app_deep_link_base,
    )
    http_thread = threading.Thread(target=run_http_server, args=(http_server,), daemon=True)
    http_thread.start()

    async def async_main() -> None:
        hub.bind_loop(asyncio.get_running_loop())
        print(f"Focus List HTTP server running at http://{args.host}:{args.port}")
        print(f"Focus List WebSocket server running at ws://{args.host}:{ws_port}/ws")
        print(f"Database: {args.db}")
        if web_root is not None:
            print(f"Static web root: {web_root}")
        if auth_token is not None:
            print("Authentication: enabled")
        else:
            print("Authentication: disabled")
        connect_config = http_server.service.get_connect_config_payload()
        print("Suggested app config:")
        print(json.dumps(connect_config, ensure_ascii=False, indent=2))
        if not has_trustworthy_remote_candidate(connect_config.get("candidates")):
            print(
                "Warning: no trustworthy Tailscale/public address was detected. "
                "Set SSH_TODOLIST_PUBLIC_BASE_URL or --public-base-url when running in Docker, NAT, or proxy setups."
            )
        if auth_token is None or args.print_connect_secrets:
            connect_link = http_server.service.get_connect_link_payload()
            print("Suggested app import link:")
            print(json.dumps(connect_link, ensure_ascii=False, indent=2))
        else:
            print("Suggested app import link: hidden because it contains the access token.")
            print(
                "Use GET /api/connect-link with Authorization: Bearer <token>, "
                "or restart with --print-connect-secrets if you need terminal output."
            )
        async with serve(
            lambda websocket: websocket_handler(websocket, hub),
            args.host,
            ws_port,
            process_request=build_websocket_process_request(auth_token),
        ):
            await asyncio.Future()

    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass
    finally:
        http_server.shutdown()
        http_server.server_close()


if __name__ == "__main__":
    main()
