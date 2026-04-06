from collections import deque
from dataclasses import asdict, dataclass, field
from threading import Lock
from uuid import uuid4

from backend.store import utc_ms


DEFAULT_ACTIVITY_LIMIT = 120


@dataclass(frozen=True)
class AdminActivityItem:
    id: str
    kind: str
    title: str
    detail: str
    time: int
    level: str = "info"
    entity_type: str = ""
    entity_id: str = ""
    metadata: dict[str, str | int | bool] = field(default_factory=dict)


class AdminActivityFeed:
    def __init__(self, *, limit: int = DEFAULT_ACTIVITY_LIMIT) -> None:
        self._items: deque[AdminActivityItem] = deque(maxlen=limit)
        self._lock = Lock()

    def add(
        self,
        *,
        kind: str,
        title: str,
        detail: str,
        level: str = "info",
        entity_type: str = "",
        entity_id: str = "",
        metadata: dict[str, str | int | bool] | None = None,
    ) -> AdminActivityItem:
        item = AdminActivityItem(
            id=_build_activity_id(),
            kind=kind,
            title=title,
            detail=detail,
            time=utc_ms(),
            level=level,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=dict(metadata or {}),
        )
        with self._lock:
            self._items.appendleft(item)
        return item

    def list_items(self) -> list[dict]:
        with self._lock:
            return [asdict(item) for item in self._items]


def _build_activity_id() -> str:
    return f"activity_{utc_ms()}_{uuid4().hex[:8]}"
