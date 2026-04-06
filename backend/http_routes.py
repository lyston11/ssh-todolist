import re
from collections.abc import Callable
from dataclasses import dataclass
from http import HTTPStatus

from backend.http_responses import SVG_CONTENT_TYPE, build_json_response, build_text_response


ROUTE_RESPONSE_JSON = "json"
ROUTE_RESPONSE_SVG = "svg"


@dataclass(frozen=True)
class RootRouteAction:
    pass


@dataclass(frozen=True)
class AdminAssetRouteAction:
    asset_path: str | None = None
    asset_path_param: str | None = None

    def resolve_asset_path(self, params: dict[str, str]) -> str:
        if self.asset_path is not None:
            return self.asset_path

        if self.asset_path_param is None:
            raise TypeError("admin asset action must define asset_path or asset_path_param")

        return params.get(self.asset_path_param, "index.html")


@dataclass(frozen=True)
class BoundServiceAction:
    execute: Callable[[dict | None], object]
    expects_request_body: bool
    status: HTTPStatus = HTTPStatus.OK
    response_builder: Callable[..., object] = build_json_response


@dataclass(frozen=True)
class ServiceRouteAction:
    service_method: str
    status: HTTPStatus = HTTPStatus.OK
    path_param_names: tuple[str, ...] = ()
    request_body_param: str | None = None
    request_headers_param: str | None = None
    response_format: str = ROUTE_RESPONSE_JSON
    reserved_param_values: tuple[tuple[str, str], ...] = ()

    def matches_params(self, params: dict[str, str]) -> bool:
        return all(params.get(name) != value for name, value in self.reserved_param_values)

    def bind(self, service, params: dict[str, str], request_headers) -> BoundServiceAction | None:
        if not self.matches_params(params):
            return None

        service_method = getattr(service, self.service_method)
        kwargs = {name: params[name] for name in self.path_param_names}
        if self.request_headers_param is not None:
            kwargs[self.request_headers_param] = request_headers

        if self.request_body_param is not None:
            return BoundServiceAction(
                execute=lambda payload: service_method(**kwargs, **{self.request_body_param: payload or {}}),
                expects_request_body=True,
                status=self.status,
                response_builder=response_builder_for(self.response_format),
            )

        return BoundServiceAction(
            execute=lambda payload=None: service_method(**kwargs),
            expects_request_body=False,
            status=self.status,
            response_builder=response_builder_for(self.response_format),
        )


@dataclass(frozen=True)
class Route:
    method: str
    pattern: re.Pattern[str]
    action: RootRouteAction | AdminAssetRouteAction | ServiceRouteAction
    requires_auth: bool = False


@dataclass(frozen=True)
class RouteMatch:
    route: Route
    params: dict[str, str]


def match_route(method: str, path: str) -> RouteMatch | None:
    for route in ROUTES:
        if route.method != method:
            continue

        matched = route.pattern.fullmatch(path)
        if matched is None:
            continue

        return RouteMatch(route=route, params=matched.groupdict())
    return None


def response_builder_for(response_format: str):
    if response_format == ROUTE_RESPONSE_JSON:
        return build_json_response
    if response_format == ROUTE_RESPONSE_SVG:
        return lambda payload, *, status: build_text_response(
            payload,
            content_type=SVG_CONTENT_TYPE,
            status=status,
        )
    raise ValueError(f"unsupported route response format: {response_format}")


ROUTES: tuple[Route, ...] = (
    Route("GET", re.compile(r"/"), RootRouteAction()),
    Route("GET", re.compile(r"/admin(?:/|/index\.html)?"), AdminAssetRouteAction(asset_path="index.html")),
    Route("GET", re.compile(r"/admin/(?P<relative_path>.+)"), AdminAssetRouteAction(asset_path_param="relative_path")),
    Route("GET", re.compile(r"/api/health"), ServiceRouteAction("get_health_payload")),
    Route(
        "GET",
        re.compile(r"/api/connect-config"),
        ServiceRouteAction("get_connect_config_payload", request_headers_param="request_headers"),
    ),
    Route(
        "GET",
        re.compile(r"/api/connect-link"),
        ServiceRouteAction("get_connect_link_payload", request_headers_param="request_headers"),
        requires_auth=True,
    ),
    Route(
        "GET",
        re.compile(r"/api/connect-link/qr\.svg"),
        ServiceRouteAction(
            "get_connect_link_qr_svg",
            request_headers_param="request_headers",
            response_format=ROUTE_RESPONSE_SVG,
        ),
        requires_auth=True,
    ),
    Route(
        "GET",
        re.compile(r"/api/meta"),
        ServiceRouteAction("get_meta_payload", request_headers_param="request_headers"),
        requires_auth=True,
    ),
    Route(
        "GET",
        re.compile(r"/api/admin/overview"),
        ServiceRouteAction("get_admin_overview_payload", request_headers_param="request_headers"),
        requires_auth=True,
    ),
    Route(
        "GET",
        re.compile(r"/api/admin/config"),
        ServiceRouteAction("get_admin_config_payload", request_headers_param="request_headers"),
        requires_auth=True,
    ),
    Route(
        "POST",
        re.compile(r"/api/admin/config"),
        ServiceRouteAction("update_admin_config", request_body_param="payload"),
        requires_auth=True,
    ),
    Route(
        "GET",
        re.compile(r"/api/admin/activity"),
        ServiceRouteAction("get_admin_activity_payload"),
        requires_auth=True,
    ),
    Route("GET", re.compile(r"/api/snapshot"), ServiceRouteAction("get_snapshot_payload"), requires_auth=True),
    Route("GET", re.compile(r"/api/lists"), ServiceRouteAction("list_lists_payload"), requires_auth=True),
    Route("GET", re.compile(r"/api/todos"), ServiceRouteAction("list_todos_payload"), requires_auth=True),
    Route(
        "POST",
        re.compile(r"/api/lists"),
        ServiceRouteAction("create_list", status=HTTPStatus.CREATED, request_body_param="payload"),
        requires_auth=True,
    ),
    Route(
        "POST",
        re.compile(r"/api/todos"),
        ServiceRouteAction("create_todo", status=HTTPStatus.CREATED, request_body_param="payload"),
        requires_auth=True,
    ),
    Route(
        "POST",
        re.compile(r"/api/todos/clear-completed"),
        ServiceRouteAction("clear_completed_todos", request_body_param="payload"),
        requires_auth=True,
    ),
    Route(
        "PATCH",
        re.compile(r"/api/lists/(?P<list_id>[^/]+)"),
        ServiceRouteAction("update_list", path_param_names=("list_id",), request_body_param="payload"),
        requires_auth=True,
    ),
    Route(
        "PATCH",
        re.compile(r"/api/todos/(?P<todo_id>[^/]+)"),
        ServiceRouteAction(
            "update_todo",
            path_param_names=("todo_id",),
            request_body_param="payload",
            reserved_param_values=(("todo_id", "clear-completed"),),
        ),
        requires_auth=True,
    ),
    Route(
        "DELETE",
        re.compile(r"/api/lists/(?P<list_id>[^/]+)"),
        ServiceRouteAction("delete_list", path_param_names=("list_id",)),
        requires_auth=True,
    ),
    Route(
        "DELETE",
        re.compile(r"/api/todos/(?P<todo_id>[^/]+)"),
        ServiceRouteAction(
            "delete_todo",
            path_param_names=("todo_id",),
            reserved_param_values=(("todo_id", "clear-completed"),),
        ),
        requires_auth=True,
    ),
)
