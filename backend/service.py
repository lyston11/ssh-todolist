from dataclasses import dataclass, field

from backend.admin_activity import AdminActivityFeed
from backend.admin_dashboard import build_admin_overview
from backend.admin_config import AdminConfigSnapshot, AdminConfigStore
from backend.auth import is_auth_enabled
from backend.connection import DEFAULT_APP_DEEP_LINK_BASE
from backend.connection import build_connect_config, build_connect_link_payload, render_qr_svg
from backend.http_logging import DEFAULT_HTTP_LOG_MODE
from backend.realtime import WebSocketHub
from backend.service_errors import NotFoundError, ValidationError
from backend.service_validators import ServiceValidators
from backend.store import TodoStore, utc_ms


@dataclass
class TodoService:
    store: TodoStore
    hub: WebSocketHub
    host: str
    port: int
    ws_port: int
    admin_entry_path: str = "/admin"
    admin_alias_path: str | None = None
    auth_token: str | None = None
    public_base_url: str | None = None
    public_ws_base_url: str | None = None
    app_web_url: str | None = None
    app_deep_link_base: str | None = None
    admin_config_store: AdminConfigStore | None = None
    admin_activity_feed: AdminActivityFeed | None = None
    validators: ServiceValidators = field(init=False)

    def __post_init__(self) -> None:
        self.validators = ServiceValidators.from_store(self.store)

    def get_health_payload(self) -> dict:
        return {
            "status": "ok",
            "time": utc_ms(),
            "wsPort": self.ws_port,
            "authRequired": is_auth_enabled(self.auth_token),
        }

    def get_meta_payload(self, request_headers=None) -> dict:
        connect_config = self.get_connect_config_payload(request_headers=request_headers)
        return {
            "wsPort": connect_config["wsPort"],
            "wsPath": "/ws",
            "time": utc_ms(),
            "authRequired": is_auth_enabled(self.auth_token),
            "connectConfigPath": "/api/connect-config",
            "connectLinkPath": "/api/connect-link",
            "serverUrl": connect_config["serverUrl"],
            "wsUrl": connect_config["wsUrl"],
            "candidates": connect_config["candidates"],
        }

    def get_connect_config_payload(self, request_headers=None, include_token: bool = False) -> dict:
        settings = self._get_admin_config_snapshot()
        return build_connect_config(
            bind_host=self.host,
            http_port=self.port,
            ws_port=self.ws_port,
            auth_token=self.auth_token,
            request_headers=request_headers,
            public_base_url=settings.public_base_url,
            public_ws_base_url=settings.public_ws_base_url,
            include_token=include_token,
        )

    def get_connect_link_payload(self, request_headers=None) -> dict:
        settings = self._get_admin_config_snapshot()
        connect_config = self.get_connect_config_payload(request_headers=request_headers, include_token=True)
        return build_connect_link_payload(
            connect_config=connect_config,
            app_web_url=settings.app_web_url,
            app_deep_link_base=settings.app_deep_link_base,
        )

    def get_connect_link_qr_svg(self, request_headers=None) -> str:
        connect_link = self.get_connect_link_payload(request_headers=request_headers)
        return render_qr_svg(connect_link["qrValue"])

    def get_admin_overview_payload(self, request_headers=None) -> dict:
        snapshot = self.get_snapshot_payload()
        connect_config = self.get_connect_config_payload(request_headers=request_headers)
        connect_link = self.get_connect_link_payload(request_headers=request_headers)
        return build_admin_overview(
            snapshot=snapshot,
            connect_config=connect_config,
            connect_link=connect_link,
            auth_required=is_auth_enabled(self.auth_token),
            db_path=self.store.db_path,
            ws_port=self.ws_port,
            admin_entry_path=self.admin_entry_path,
            admin_alias_path=self.admin_alias_path,
        )

    def get_admin_config_payload(self, request_headers=None) -> dict:
        return {
            **self._build_admin_config_payload(),
            "authRequired": is_auth_enabled(self.auth_token),
        }

    def update_admin_config(self, payload: dict) -> dict:
        if self.admin_config_store is None:
            raise ValidationError("当前服务未启用后台配置存储")

        previous = self.admin_config_store.snapshot()
        updated = self.admin_config_store.update(payload)
        current = self.admin_config_store.snapshot()
        self._add_activity(
            kind="config.updated",
            title="后台配置已更新",
            detail=_describe_admin_config_change(previous, current),
            entity_type="config",
        )
        return {
            **updated,
            "authRequired": is_auth_enabled(self.auth_token),
        }

    def get_admin_activity_payload(self) -> dict:
        items = self.admin_activity_feed.list_items() if self.admin_activity_feed is not None else []
        return {
            "items": items,
            "count": len(items),
            "time": utc_ms(),
        }

    def get_snapshot_payload(self) -> dict:
        lists = self.store.list_lists()
        default_list_id = self.store.get_default_list_id() if lists else None
        return {
            "lists": lists,
            "items": self.store.list_todos(),
            "defaultListId": default_list_id,
            "time": utc_ms(),
        }

    def list_todos_payload(self) -> dict:
        snapshot = self.get_snapshot_payload()
        return {
            "items": snapshot["items"],
            "lists": snapshot["lists"],
            "defaultListId": snapshot["defaultListId"],
            "time": snapshot["time"],
        }

    def list_lists_payload(self) -> dict:
        snapshot = self.get_snapshot_payload()
        return {
            "items": snapshot["lists"],
            "defaultListId": snapshot["defaultListId"],
            "time": snapshot["time"],
        }

    def create_list(self, payload: dict) -> dict:
        validated = self.validators.create_list.validate(payload)
        todo_list = self.store.create_list(validated.title, list_id=validated.item_id)
        self.hub.broadcast_snapshot_sync()
        self._add_activity(
            kind="list.created",
            title="已创建清单",
            detail=f"清单“{todo_list['title']}”已创建。",
            entity_type="list",
            entity_id=todo_list["id"],
        )
        return todo_list

    def update_list(self, list_id: str, payload: dict) -> dict:
        validated = self.validators.update_list.validate(payload)
        todo_list = self.store.update_list(list_id, validated.title)
        if todo_list is None:
            raise NotFoundError("list not found")

        self.hub.broadcast_snapshot_sync()
        self._add_activity(
            kind="list.updated",
            title="已更新清单",
            detail=f"清单“{todo_list['title']}”已更新。",
            entity_type="list",
            entity_id=todo_list["id"],
        )
        return todo_list

    def delete_list(self, list_id: str) -> dict:
        existing = self.store.get_list(list_id)
        if existing is None:
            raise NotFoundError("list not found")

        lists = self.store.list_lists()
        if len(lists) <= 1:
            raise ValidationError("至少保留一个清单")

        deleted = self.store.delete_list(list_id)
        if not deleted:
            raise NotFoundError("list not found")

        self.hub.broadcast_snapshot_sync()
        self._add_activity(
            kind="list.deleted",
            title="已删除清单",
            detail=f"清单“{existing['title']}”已删除。",
            entity_type="list",
            entity_id=list_id,
            level="warning",
        )
        return {"deleted": True}

    def create_todo(self, payload: dict) -> dict:
        validated = self.validators.create_todo.validate(payload)
        todo_list = self.store.get_list(validated.list_id)
        todo = self.store.create_todo(
            validated.list_id,
            validated.title,
            todo_id=validated.item_id,
            tag=validated.tag,
            due_at=validated.due_at if validated.due_at_provided else None,
        )
        self.hub.broadcast_snapshot_sync()
        self._add_activity(
            kind="todo.created",
            title="已创建任务",
            detail=f"任务“{todo['title']}”已加入清单“{todo_list['title'] if todo_list else todo['listId']}”。",
            entity_type="todo",
            entity_id=todo["id"],
        )
        return todo

    def update_todo(self, todo_id: str, payload: dict) -> dict:
        validated = self.validators.update_todo.validate(payload)
        todo = self.store.update_todo(
            todo_id,
            validated.title,
            validated.completed,
            list_id=validated.list_id,
            tag=validated.tag,
            due_at=validated.due_at,
            due_at_provided=validated.due_at_provided,
        )
        if todo is None:
            raise NotFoundError("todo not found")

        self.hub.broadcast_snapshot_sync()
        self._add_activity(
            kind="todo.updated",
            title="已更新任务",
            detail=f"任务“{todo['title']}”已更新。",
            entity_type="todo",
            entity_id=todo["id"],
        )
        return todo

    def delete_todo(self, todo_id: str) -> dict:
        existing = self.store.get_todo(todo_id)
        if existing is None:
            raise NotFoundError("todo not found")

        deleted = self.store.delete_todo(todo_id)
        if not deleted:
            raise NotFoundError("todo not found")

        self.hub.broadcast_snapshot_sync()
        self._add_activity(
            kind="todo.deleted",
            title="已删除任务",
            detail=f"任务“{existing['title']}”已删除。",
            entity_type="todo",
            entity_id=todo_id,
            level="warning",
        )
        return {"deleted": True}

    def clear_completed_todos(self, payload: dict | None = None) -> dict:
        validated = self.validators.clear_completed.validate(payload)
        deleted = self.store.clear_completed(validated.list_id)
        target_list = self.store.get_list(validated.list_id) if validated.list_id else None
        self.hub.broadcast_snapshot_sync()
        self._add_activity(
            kind="todo.cleared_completed",
            title="已清空已完成任务",
            detail=(
                f"已清空清单“{target_list['title']}”中的 {deleted} 条已完成任务。"
                if target_list is not None
                else f"已清空全部清单中的 {deleted} 条已完成任务。"
            ),
            entity_type="todo",
            level="warning",
            metadata={"deleted": deleted},
        )
        return {"deleted": deleted}

    def _build_admin_config_payload(self) -> dict:
        if self.admin_config_store is not None:
            return self.admin_config_store.to_payload()

        settings = self._get_admin_config_snapshot()
        return {
            "publicBaseUrl": settings.public_base_url or "",
            "publicWsBaseUrl": settings.public_ws_base_url or "",
            "appWebUrl": settings.app_web_url or "",
            "appDeepLinkBase": settings.app_deep_link_base,
            "httpLogMode": settings.http_log_mode,
            "configPath": "",
            "time": utc_ms(),
        }

    def _get_admin_config_snapshot(self) -> AdminConfigSnapshot:
        if self.admin_config_store is not None:
            return self.admin_config_store.snapshot()
        return AdminConfigSnapshot(
            public_base_url=self.public_base_url,
            public_ws_base_url=self.public_ws_base_url,
            app_web_url=self.app_web_url,
            app_deep_link_base=self.app_deep_link_base or DEFAULT_APP_DEEP_LINK_BASE,
            http_log_mode=DEFAULT_HTTP_LOG_MODE,
        )

    def _add_activity(
        self,
        *,
        kind: str,
        title: str,
        detail: str,
        level: str = "info",
        entity_type: str = "",
        entity_id: str = "",
        metadata: dict[str, str | int | bool] | None = None,
    ) -> None:
        if self.admin_activity_feed is None:
            return
        self.admin_activity_feed.add(
            kind=kind,
            title=title,
            detail=detail,
            level=level,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
        )


def _describe_admin_config_change(
    previous: AdminConfigSnapshot,
    current: AdminConfigSnapshot,
) -> str:
    changed_fields: list[str] = []
    if previous.public_base_url != current.public_base_url:
        changed_fields.append("公共 HTTP 地址")
    if previous.public_ws_base_url != current.public_ws_base_url:
        changed_fields.append("公共 WebSocket 地址")
    if previous.app_web_url != current.app_web_url:
        changed_fields.append("Web 导入地址")
    if previous.app_deep_link_base != current.app_deep_link_base:
        changed_fields.append("App Deep Link 基址")
    if previous.http_log_mode != current.http_log_mode:
        changed_fields.append("HTTP 日志模式")

    if not changed_fields:
        return "配置已保存，字段内容未发生变化。"

    return f"已更新：{'、'.join(changed_fields)}。"
