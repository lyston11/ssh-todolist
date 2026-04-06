import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.admin_activity import AdminActivityFeed
from backend.admin_config import build_default_admin_config_store
from backend.http_server import create_http_server
from backend.realtime import WebSocketHub
from backend.store import TodoStore


class HttpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tempdir.name) / "todos.db"
        self.store = TodoStore(self.db_path)
        self.hub = WebSocketHub(self.store)
        self.server = None
        self.thread = None

    def tearDown(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)
        self._tempdir.cleanup()

    def test_health_is_public_but_meta_requires_auth(self) -> None:
        self._start_server(auth_token="secret-token")

        health = self._request_json("/api/health")
        self.assertEqual(health["status"], "ok")
        self.assertTrue(health["authRequired"])

        with self.assertRaises(HTTPError) as ctx:
            self._request_json("/api/meta")
        self.assertEqual(ctx.exception.code, 401)

        meta = self._request_json("/api/meta", token="secret-token")
        self.assertEqual(meta["authRequired"], True)
        self.assertIn("serverUrl", meta)

    def test_root_serves_admin_dashboard_when_no_static_app(self) -> None:
        self._start_server()

        html = self._request_text("/")
        self.assertIn("ssh-todolist-services", html)
        self.assertIn("同步服务后台", html)

    def test_admin_alias_serves_dashboard_when_no_static_app(self) -> None:
        self._start_server()

        html = self._request_text("/admin")
        self.assertIn("ssh-todolist-services", html)
        self.assertIn("同步服务后台", html)

    def test_connect_link_and_qr_svg_require_auth(self) -> None:
        self._start_server(auth_token="secret-token")

        with self.assertRaises(HTTPError) as link_ctx:
            self._request_json("/api/connect-link")
        self.assertEqual(link_ctx.exception.code, 401)

        connect_link = self._request_json("/api/connect-link", token="secret-token")
        self.assertIn("config64", connect_link)
        self.assertEqual(connect_link["qrSvgPath"], "/api/connect-link/qr.svg")

        with self.assertRaises(HTTPError) as qr_ctx:
            self._request_text("/api/connect-link/qr.svg")
        self.assertEqual(qr_ctx.exception.code, 401)

        svg = self._request_text("/api/connect-link/qr.svg", token="secret-token")
        self.assertIn("<svg", svg)

    def test_todo_crud_round_trip_over_http(self) -> None:
        self._start_server()

        created_list = self._request_json(
            "/api/lists",
            method="POST",
            body={"title": "工作台", "id": "work-list"},
        )
        self.assertEqual(created_list["id"], "work-list")

        created_todo = self._request_json(
            "/api/todos",
            method="POST",
            body={"title": "联调 API", "listId": "work-list", "tag": "开发"},
        )
        self.assertEqual(created_todo["listId"], "work-list")
        self.assertEqual(created_todo["tag"], "开发")

        updated_todo = self._request_json(
            f"/api/todos/{created_todo['id']}",
            method="PATCH",
            body={"completed": True, "dueAt": 1760086400000},
        )
        self.assertTrue(updated_todo["completed"])
        self.assertEqual(updated_todo["dueAt"], 1760086400000)

        cleared = self._request_json("/api/todos/clear-completed", method="POST", body={})
        self.assertEqual(cleared["deleted"], 1)

        todos_payload = self._request_json("/api/todos")
        self.assertEqual(todos_payload["items"], [])

    def test_invalid_json_body_returns_bad_request(self) -> None:
        self._start_server()

        with self.assertRaises(HTTPError) as ctx:
            self._request_raw(
                "/api/todos",
                method="POST",
                body=b"{invalid",
                headers={"Content-Type": "application/json"},
            )

        self.assertEqual(ctx.exception.code, 400)
        self.assertIn("invalid json", ctx.exception.read().decode("utf-8"))

    def test_non_object_json_body_returns_bad_request(self) -> None:
        self._start_server()

        with self.assertRaises(HTTPError) as ctx:
            self._request_raw(
                "/api/todos",
                method="POST",
                body=b"[]",
                headers={"Content-Type": "application/json"},
            )

        self.assertEqual(ctx.exception.code, 400)
        self.assertIn("json body must be an object", ctx.exception.read().decode("utf-8"))

    def test_delete_missing_todo_returns_not_found_payload(self) -> None:
        self._start_server()

        with self.assertRaises(HTTPError) as ctx:
            self._request_raw("/api/todos/missing-todo", method="DELETE")

        self.assertEqual(ctx.exception.code, 404)
        self.assertIn("todo not found", ctx.exception.read().decode("utf-8"))

    def test_reserved_todo_clear_completed_paths_return_not_found(self) -> None:
        self._start_server()

        with self.assertRaises(HTTPError) as patch_ctx:
            self._request_raw(
                "/api/todos/clear-completed",
                method="PATCH",
                body=b"{}",
                headers={"Content-Type": "application/json"},
            )
        self.assertEqual(patch_ctx.exception.code, 404)
        self.assertIn("endpoint not found", patch_ctx.exception.read().decode("utf-8"))

        with self.assertRaises(HTTPError) as delete_ctx:
            self._request_raw("/api/todos/clear-completed", method="DELETE")
        self.assertEqual(delete_ctx.exception.code, 404)
        self.assertIn("endpoint not found", delete_ctx.exception.read().decode("utf-8"))

    def test_unknown_endpoint_returns_not_found(self) -> None:
        self._start_server()

        with self.assertRaises(HTTPError) as ctx:
            self._request_raw("/api/unknown-endpoint", method="POST", body=b"{}")

        self.assertEqual(ctx.exception.code, 404)
        self.assertIn("endpoint not found", ctx.exception.read().decode("utf-8"))

    def test_admin_config_round_trip_over_http(self) -> None:
        config_store = build_default_admin_config_store(
            data_dir=Path(self._tempdir.name),
            public_base_url=None,
            public_ws_base_url=None,
            app_web_url=None,
            app_deep_link_base="com.lyston11.sshtodolist://connect",
            http_log_mode="errors",
        )
        self._start_server(
            auth_token="secret-token",
            admin_config_store=config_store,
            admin_activity_feed=AdminActivityFeed(),
        )

        config_payload = self._request_json("/api/admin/config", token="secret-token")
        self.assertEqual(config_payload["httpLogMode"], "errors")
        self.assertTrue(config_payload["authRequired"])

        updated_config = self._request_json(
            "/api/admin/config",
            method="POST",
            token="secret-token",
            body={
                "publicBaseUrl": "https://todo.example.com/",
                "publicWsBaseUrl": "wss://todo.example.com/",
                "appWebUrl": "https://app.example.com/",
                "appDeepLinkBase": "com.lyston11.sshtodolist://import/",
                "httpLogMode": "all",
            },
        )
        self.assertEqual(updated_config["publicBaseUrl"], "https://todo.example.com")
        self.assertEqual(updated_config["publicWsBaseUrl"], "wss://todo.example.com")
        self.assertEqual(updated_config["appWebUrl"], "https://app.example.com")
        self.assertEqual(updated_config["appDeepLinkBase"], "com.lyston11.sshtodolist://import")
        self.assertEqual(updated_config["httpLogMode"], "all")

        connect_config = self._request_json("/api/connect-config")
        self.assertEqual(connect_config["serverUrl"], "https://todo.example.com")
        self.assertEqual(connect_config["wsUrl"], "wss://todo.example.com/ws")

    def test_admin_activity_endpoint_includes_recent_mutations(self) -> None:
        self._start_server(auth_token="secret-token", admin_activity_feed=AdminActivityFeed())

        self._request_json(
            "/api/lists",
            method="POST",
            token="secret-token",
            body={"title": "工作台", "id": "work-list"},
        )
        todo = self._request_json(
            "/api/todos",
            method="POST",
            token="secret-token",
            body={"title": "联调 API", "listId": "work-list"},
        )
        self._request_json(
            f"/api/todos/{todo['id']}",
            method="PATCH",
            token="secret-token",
            body={"completed": True},
        )

        activity_payload = self._request_json("/api/admin/activity", token="secret-token")
        self.assertEqual(activity_payload["count"], 3)
        self.assertEqual(
            [item["kind"] for item in activity_payload["items"]],
            ["todo.updated", "todo.created", "list.created"],
        )

    def _start_server(
        self,
        auth_token: str | None = None,
        *,
        admin_config_store=None,
        admin_activity_feed=None,
    ) -> None:
        self.server = create_http_server(
            "127.0.0.1",
            0,
            self.store,
            self.hub,
            ws_port=8001,
            static_root=None,
            auth_token=auth_token,
            admin_config_store=admin_config_store,
            admin_activity_feed=admin_activity_feed,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def _request_json(
        self,
        path: str,
        *,
        method: str = "GET",
        body: dict | None = None,
        token: str | None = None,
    ) -> dict:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{self.server.server_address[1]}{path}",
            data=payload,
            method=method,
            headers={
                **({"Content-Type": "application/json"} if payload is not None else {}),
                **({"Authorization": f"Bearer {token}"} if token else {}),
            },
        )
        with urlopen(request, timeout=3) as response:
            return json.loads(response.read().decode("utf-8"))

    def _request_text(
        self,
        path: str,
        *,
        method: str = "GET",
        token: str | None = None,
    ) -> str:
        request = Request(
            f"http://127.0.0.1:{self.server.server_address[1]}{path}",
            method=method,
            headers={
                **({"Authorization": f"Bearer {token}"} if token else {}),
            },
        )
        with urlopen(request, timeout=3) as response:
            return response.read().decode("utf-8")

    def _request_raw(
        self,
        path: str,
        *,
        method: str = "GET",
        body: bytes | None = None,
        headers: dict | None = None,
    ) -> bytes:
        request = Request(
            f"http://127.0.0.1:{self.server.server_address[1]}{path}",
            data=body,
            method=method,
            headers=headers or {},
        )
        with urlopen(request, timeout=3) as response:
            return response.read()
