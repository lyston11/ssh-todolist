const todoForm = document.querySelector("#todo-form");
const todoInput = document.querySelector("#todo-input");
const todoList = document.querySelector("#todo-list");
const todoCount = document.querySelector("#todo-count");
const clearCompletedButton = document.querySelector("#clear-completed");
const emptyState = document.querySelector("#empty-state");
const syncStatus = document.querySelector("#sync-status");
const filterButtons = document.querySelectorAll(".filter");
const itemTemplate = document.querySelector("#todo-item-template");
const editDialog = document.querySelector("#edit-dialog");
const editForm = document.querySelector("#edit-form");
const editInput = document.querySelector("#edit-input");
const cancelEditButton = document.querySelector("#cancel-edit");

const API_BASE = "/api/todos";

let todos = [];
let currentFilter = "all";
let editingTodoId = null;
let syncState = "connecting";
let socket = null;
let reconnectTimer = null;
let socketConfig = {
  wsPort: location.port ? Number(location.port) + 1 : 8001,
  wsPath: "/ws",
};

render();
bootstrap();

todoForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const value = todoInput.value.trim();
  if (!value) {
    return;
  }

  try {
    setSyncState("connecting");
    await request(API_BASE, {
      method: "POST",
      body: JSON.stringify({ title: value }),
    });
    todoForm.reset();
    todoInput.focus();
    await fetchTodos();
  } catch (error) {
    handleSyncError(error);
  }
});

clearCompletedButton.addEventListener("click", async () => {
  try {
    setSyncState("connecting");
    await request(`${API_BASE}/clear-completed`, { method: "POST" });
    await fetchTodos();
  } catch (error) {
    handleSyncError(error);
  }
});

filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    currentFilter = button.dataset.filter;
    filterButtons.forEach((item) => item.classList.toggle("is-active", item === button));
    render();
  });
});

todoList.addEventListener("click", async (event) => {
  const target = event.target;
  const item = target.closest(".todo-item");
  if (!item) {
    return;
  }

  const todoId = item.dataset.todoId;

  if (target.classList.contains("delete-button")) {
    try {
      setSyncState("connecting");
      await request(`${API_BASE}/${todoId}`, { method: "DELETE" });
      await fetchTodos();
    } catch (error) {
      handleSyncError(error);
    }
    return;
  }

  if (target.classList.contains("edit-button")) {
    openEditDialog(todoId);
  }
});

todoList.addEventListener("change", async (event) => {
  const target = event.target;
  if (!target.classList.contains("todo-toggle")) {
    return;
  }

  const item = target.closest(".todo-item");
  const todoId = item.dataset.todoId;

  try {
    setSyncState("connecting");
    await request(`${API_BASE}/${todoId}`, {
      method: "PATCH",
      body: JSON.stringify({ completed: target.checked }),
    });
    await fetchTodos();
  } catch (error) {
    handleSyncError(error);
  }
});

editForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!editingTodoId) {
    editDialog.close();
    return;
  }

  const value = editInput.value.trim();
  if (!value) {
    return;
  }

  try {
    setSyncState("connecting");
    await request(`${API_BASE}/${editingTodoId}`, {
      method: "PATCH",
      body: JSON.stringify({ title: value }),
    });
    editingTodoId = null;
    editDialog.close();
    await fetchTodos();
  } catch (error) {
    handleSyncError(error);
  }
});

cancelEditButton.addEventListener("click", () => {
  editingTodoId = null;
  editDialog.close();
});

editDialog.addEventListener("close", () => {
  editingTodoId = null;
});

function openEditDialog(todoId) {
  const todo = todos.find((item) => item.id === todoId);
  if (!todo) {
    return;
  }

  editingTodoId = todoId;
  editInput.value = todo.title;
  editDialog.showModal();
  editInput.focus();
  editInput.select();
}

function render() {
  const filteredTodos = getFilteredTodos();
  todoList.innerHTML = "";

  filteredTodos.forEach((todo) => {
    const itemFragment = itemTemplate.content.cloneNode(true);
    const item = itemFragment.querySelector(".todo-item");
    const title = itemFragment.querySelector(".todo-title");
    const meta = itemFragment.querySelector(".todo-meta");
    const toggle = itemFragment.querySelector(".todo-toggle");

    item.dataset.todoId = todo.id;
    item.classList.toggle("is-completed", todo.completed);
    title.textContent = todo.title;
    meta.textContent = todo.completed
      ? `已完成于 ${formatDate(todo.completedAt ?? todo.createdAt)}`
      : `创建于 ${formatDate(todo.createdAt)}`;
    toggle.checked = todo.completed;

    todoList.append(itemFragment);
  });

  const activeCount = todos.filter((todo) => !todo.completed).length;
  const hasVisibleTodos = filteredTodos.length > 0;

  todoCount.textContent = `${activeCount} 个待完成`;
  emptyState.classList.toggle("is-visible", !hasVisibleTodos);
  clearCompletedButton.disabled = !todos.some((todo) => todo.completed);
  renderSyncState();
}

function getFilteredTodos() {
  if (currentFilter === "active") {
    return todos.filter((todo) => !todo.completed);
  }

  if (currentFilter === "completed") {
    return todos.filter((todo) => todo.completed);
  }

  return todos;
}

async function fetchTodos() {
  try {
    const response = await request(API_BASE);
    todos = Array.isArray(response.items) ? response.items.filter(isTodoRecord) : [];
    render();
  } catch (error) {
    handleSyncError(error);
  }
}

function isTodoRecord(value) {
  return (
    value &&
    typeof value === "object" &&
    typeof value.id === "string" &&
    typeof value.title === "string" &&
    typeof value.completed === "boolean" &&
    typeof value.createdAt === "number" &&
    typeof value.updatedAt === "number" &&
    (typeof value.completedAt === "number" || value.completedAt === null || value.completedAt === undefined)
  );
}

function renderSyncState() {
  syncStatus.classList.toggle("is-online", syncState === "online");
  syncStatus.classList.toggle("is-offline", syncState === "offline");

  if (syncState === "online") {
    syncStatus.textContent = "已连接实时同步节点";
    return;
  }

  if (syncState === "offline") {
    syncStatus.textContent = "同步服务不可用";
    return;
  }

  syncStatus.textContent = "正在连接同步服务";
}

function setSyncState(nextState) {
  syncState = nextState;
  renderSyncState();
}

function handleSyncError(error) {
  console.error(error);
  setSyncState("offline");
}

async function bootstrap() {
  try {
    const meta = await request("/api/meta");
    socketConfig = {
      wsPort: typeof meta.wsPort === "number" ? meta.wsPort : socketConfig.wsPort,
      wsPath: typeof meta.wsPath === "string" ? meta.wsPath : "/ws",
    };
  } catch (error) {
    console.error(error);
  }

  await fetchTodos();
  connectSocket();
}

function connectSocket() {
  clearReconnectTimer();

  const url = buildSocketUrl();
  socket = new WebSocket(url);
  setSyncState("connecting");

  socket.addEventListener("open", () => {
    setSyncState("online");
  });

  socket.addEventListener("message", (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === "todos.snapshot" && Array.isArray(payload.items)) {
        todos = payload.items.filter(isTodoRecord);
        setSyncState("online");
        render();
      }
    } catch (error) {
      console.error(error);
    }
  });

  socket.addEventListener("close", () => {
    setSyncState("offline");
    scheduleReconnect();
  });

  socket.addEventListener("error", () => {
    setSyncState("offline");
    socket?.close();
  });
}

function scheduleReconnect() {
  if (reconnectTimer !== null) {
    return;
  }

  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    connectSocket();
  }, 2000);
}

function clearReconnectTimer() {
  if (reconnectTimer === null) {
    return;
  }

  window.clearTimeout(reconnectTimer);
  reconnectTimer = null;
}

function buildSocketUrl() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${location.hostname}:${socketConfig.wsPort}${socketConfig.wsPath}`;
}

async function request(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = typeof payload.error === "string" ? payload.error : `request failed: ${response.status}`;
    throw new Error(message);
  }

  return payload;
}

function formatDate(timestamp) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(timestamp);
}
