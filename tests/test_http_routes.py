import unittest
from http import HTTPStatus

from backend.http_responses import SVG_CONTENT_TYPE
from backend.http_routes import (
    ROUTE_RESPONSE_SVG,
    AdminAssetRouteAction,
    ServiceRouteAction,
    match_route,
)


class _FakeService:
    def update_todo(self, todo_id: str, payload: dict) -> dict:
        return {
            "todoId": todo_id,
            "payload": payload,
        }

    def get_meta_payload(self, request_headers) -> dict:
        return {
            "authorization": request_headers.get("Authorization"),
        }

    def get_connect_link_qr_svg(self) -> str:
        return "<svg />"


class HttpRoutesTests(unittest.TestCase):
    def test_match_route_returns_route_and_params(self) -> None:
        match = match_route("PATCH", "/api/todos/abc-123")

        self.assertIsNotNone(match)
        self.assertEqual(match.params, {"todo_id": "abc-123"})
        self.assertTrue(match.route.requires_auth)

    def test_admin_asset_action_resolves_param_path(self) -> None:
        action = AdminAssetRouteAction(asset_path_param="relative_path")

        self.assertEqual(action.resolve_asset_path({"relative_path": "bundle.js"}), "bundle.js")

    def test_service_route_binding_injects_path_and_body_params(self) -> None:
        action = ServiceRouteAction(
            "update_todo",
            path_param_names=("todo_id",),
            request_body_param="payload",
            status=HTTPStatus.ACCEPTED,
        )

        bound_action = action.bind(_FakeService(), {"todo_id": "todo-1"}, {})

        self.assertIsNotNone(bound_action)
        self.assertTrue(bound_action.expects_request_body)
        self.assertEqual(bound_action.status, HTTPStatus.ACCEPTED)
        self.assertEqual(
            bound_action.execute({"completed": True}),
            {"todoId": "todo-1", "payload": {"completed": True}},
        )

    def test_service_route_binding_injects_request_headers(self) -> None:
        action = ServiceRouteAction(
            "get_meta_payload",
            request_headers_param="request_headers",
        )

        bound_action = action.bind(_FakeService(), {}, {"Authorization": "Bearer secret"})

        self.assertIsNotNone(bound_action)
        self.assertFalse(bound_action.expects_request_body)
        self.assertEqual(
            bound_action.execute(),
            {"authorization": "Bearer secret"},
        )

    def test_service_route_binding_rejects_reserved_path_values(self) -> None:
        action = ServiceRouteAction(
            "update_todo",
            path_param_names=("todo_id",),
            request_body_param="payload",
            reserved_param_values=(("todo_id", "clear-completed"),),
        )

        self.assertIsNone(action.bind(_FakeService(), {"todo_id": "clear-completed"}, {}))

    def test_match_route_covers_admin_config_and_activity_endpoints(self) -> None:
        config_get = match_route("GET", "/api/admin/config")
        self.assertIsNotNone(config_get)
        self.assertTrue(config_get.route.requires_auth)
        self.assertEqual(config_get.route.action.service_method, "get_admin_config_payload")

        config_post = match_route("POST", "/api/admin/config")
        self.assertIsNotNone(config_post)
        self.assertTrue(config_post.route.requires_auth)
        self.assertEqual(config_post.route.action.service_method, "update_admin_config")

        activity_get = match_route("GET", "/api/admin/activity")
        self.assertIsNotNone(activity_get)
        self.assertTrue(activity_get.route.requires_auth)
        self.assertEqual(activity_get.route.action.service_method, "get_admin_activity_payload")

    def test_svg_route_binding_uses_svg_response_builder(self) -> None:
        action = ServiceRouteAction(
            "get_connect_link_qr_svg",
            response_format=ROUTE_RESPONSE_SVG,
        )

        bound_action = action.bind(_FakeService(), {}, {})

        self.assertIsNotNone(bound_action)
        response = bound_action.response_builder(bound_action.execute(), status=HTTPStatus.OK)
        self.assertEqual(response.content_type, SVG_CONTENT_TYPE)
        self.assertIn(b"<svg", response.body)


if __name__ == "__main__":
    unittest.main()
