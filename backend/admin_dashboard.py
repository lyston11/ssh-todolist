from datetime import datetime
from pathlib import Path

from backend.admin_guidance import build_admin_install_payload, build_admin_runtime_payload
from backend.store import utc_ms


def build_admin_overview(
    *,
    snapshot: dict,
    connect_config: dict,
    connect_link: dict,
    auth_required: bool,
    db_path: Path,
    ws_port: int,
    admin_entry_path: str = "/admin",
    admin_alias_path: str | None = None,
) -> dict:
    lists = list(snapshot.get("lists") or [])
    todos = list(snapshot.get("items") or [])
    active_todos = [todo for todo in todos if not todo.get("completed")]
    completed_todos = [todo for todo in todos if todo.get("completed")]
    today_key = _current_local_date_key()
    scheduled_active_todos = [todo for todo in active_todos if isinstance(todo.get("dueAt"), int)]
    unscheduled_active_todos = [todo for todo in active_todos if not isinstance(todo.get("dueAt"), int)]
    due_today_active_todos = [todo for todo in scheduled_active_todos if _classify_due_bucket(todo, today_key) == "today"]
    overdue_active_todos = [todo for todo in scheduled_active_todos if _classify_due_bucket(todo, today_key) == "overdue"]

    return {
        "status": "ok",
        "time": utc_ms(),
        "authRequired": auth_required,
        "runtime": build_admin_runtime_payload(
            connect_config=connect_config,
            auth_required=auth_required,
            db_path=db_path,
            ws_port=ws_port,
            admin_entry_path=admin_entry_path,
            admin_alias_path=admin_alias_path,
        ),
        "install": build_admin_install_payload(
            connect_config=connect_config,
            auth_required=auth_required,
        ),
        "server": {
            "serverUrl": connect_config.get("serverUrl", ""),
            "wsUrl": connect_config.get("wsUrl", ""),
            "wsPort": ws_port,
            "candidateCount": len(connect_config.get("candidates") or []),
            "candidates": connect_config.get("candidates") or [],
        },
        "database": {
            "path": str(db_path),
            "exists": db_path.exists(),
            "sizeBytes": _get_file_size(db_path),
        },
        "totals": {
            "lists": len(lists),
            "todos": len(todos),
            "activeTodos": len(active_todos),
            "completedTodos": len(completed_todos),
            "scheduledTodos": len(scheduled_active_todos),
            "unscheduledTodos": len(unscheduled_active_todos),
            "dueTodayTodos": len(due_today_active_todos),
            "overdueTodos": len(overdue_active_todos),
        },
        "defaultListId": snapshot.get("defaultListId"),
        "lists": _build_list_summaries(lists, todos, today_key=today_key),
        "recentTodos": _build_recent_todos(todos, lists=lists, today_key=today_key),
        "connectLink": connect_link,
    }


def _build_list_summaries(lists: list[dict], todos: list[dict], *, today_key: str) -> list[dict]:
    summaries = []
    for todo_list in lists:
        list_todos = [todo for todo in todos if todo.get("listId") == todo_list.get("id")]
        active_count = len([todo for todo in list_todos if not todo.get("completed")])
        completed_count = len(list_todos) - active_count
        due_today_count = len(
            [
                todo
                for todo in list_todos
                if not todo.get("completed") and _classify_due_bucket(todo, today_key) == "today"
            ]
        )
        overdue_count = len(
            [
                todo
                for todo in list_todos
                if not todo.get("completed") and _classify_due_bucket(todo, today_key) == "overdue"
            ]
        )
        summaries.append(
            {
                "id": todo_list.get("id", ""),
                "title": todo_list.get("title", ""),
                "createdAt": todo_list.get("createdAt"),
                "updatedAt": todo_list.get("updatedAt"),
                "todoCount": len(list_todos),
                "activeTodoCount": active_count,
                "completedTodoCount": completed_count,
                "dueTodayTodoCount": due_today_count,
                "overdueTodoCount": overdue_count,
            }
        )
    return summaries


def _build_recent_todos(todos: list[dict], *, lists: list[dict], today_key: str, limit: int = 50) -> list[dict]:
    list_title_by_id = {todo_list.get("id"): todo_list.get("title", "") for todo_list in lists}
    recent_items = sorted(
        todos,
        key=lambda todo: todo.get("updatedAt") or todo.get("createdAt") or 0,
        reverse=True,
    )[:limit]
    payload = []
    for todo in recent_items:
        item = dict(todo)
        item["listTitle"] = list_title_by_id.get(todo.get("listId"), "")
        item["dueBucket"] = _classify_due_bucket(todo, today_key)
        payload.append(item)
    return payload


def _current_local_date_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _local_date_key(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d")


def _classify_due_bucket(todo: dict, today_key: str) -> str:
    if todo.get("completed"):
        return "completed"

    due_at = todo.get("dueAt")
    if not isinstance(due_at, int):
        return "unscheduled"

    due_key = _local_date_key(due_at)
    if due_key < today_key:
        return "overdue"
    if due_key == today_key:
        return "today"
    return "upcoming"


def _get_file_size(db_path: Path) -> int:
    try:
        return db_path.stat().st_size
    except OSError:
        return 0
