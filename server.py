import argparse
import asyncio
import os
import threading
from pathlib import Path

from websockets.asyncio.server import serve

from backend.http_server import create_http_server, run_http_server
from backend.realtime import WebSocketHub, build_websocket_process_request, websocket_handler
from backend.store import TodoStore


PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATABASE_DIR / "todos.db"
DEFAULT_AUTH_TOKEN = os.environ.get("SSH_TODOLIST_TOKEN", "").strip() or None


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
