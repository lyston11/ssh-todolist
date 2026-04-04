from pathlib import Path

from backend.store import utc_ms


def build_admin_overview(
    *,
    snapshot: dict,
    connect_config: dict,
    connect_link: dict,
    auth_required: bool,
    db_path: Path,
    ws_port: int,
) -> dict:
    lists = list(snapshot.get("lists") or [])
    todos = list(snapshot.get("items") or [])
    active_todos = [todo for todo in todos if not todo.get("completed")]
    completed_todos = [todo for todo in todos if todo.get("completed")]

    return {
        "status": "ok",
        "time": utc_ms(),
        "authRequired": auth_required,
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
        },
        "lists": _build_list_summaries(lists, todos),
        "recentTodos": _build_recent_todos(todos),
        "connectLink": connect_link,
    }


def _build_list_summaries(lists: list[dict], todos: list[dict]) -> list[dict]:
    summaries = []
    for todo_list in lists:
        list_todos = [todo for todo in todos if todo.get("listId") == todo_list.get("id")]
        active_count = len([todo for todo in list_todos if not todo.get("completed")])
        completed_count = len(list_todos) - active_count
        summaries.append(
            {
                "id": todo_list.get("id", ""),
                "title": todo_list.get("title", ""),
                "createdAt": todo_list.get("createdAt"),
                "updatedAt": todo_list.get("updatedAt"),
                "todoCount": len(list_todos),
                "activeTodoCount": active_count,
                "completedTodoCount": completed_count,
            }
        )
    return summaries


def _build_recent_todos(todos: list[dict], limit: int = 12) -> list[dict]:
    return sorted(
        todos,
        key=lambda todo: todo.get("updatedAt") or todo.get("createdAt") or 0,
        reverse=True,
    )[:limit]


def _get_file_size(db_path: Path) -> int:
    try:
        return db_path.stat().st_size
    except OSError:
        return 0
