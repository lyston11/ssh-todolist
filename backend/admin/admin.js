const TOKEN_STORAGE_KEY = "ssh-todolist-services.admin.token";

const elements = {
  authStatus: document.querySelector("#auth-status"),
  updatedAt: document.querySelector("#updated-at"),
  tokenForm: document.querySelector("#token-form"),
  tokenInput: document.querySelector("#token-input"),
  refreshButton: document.querySelector("#refresh-button"),
  statsGrid: document.querySelector("#stats-grid"),
  serverMeta: document.querySelector("#server-meta"),
  candidateList: document.querySelector("#candidate-list"),
  shareMeta: document.querySelector("#share-meta"),
  shareTextBlock: document.querySelector("#share-text-block"),
  shareText: document.querySelector("#share-text"),
  listsGrid: document.querySelector("#lists-grid"),
  recentTodos: document.querySelector("#recent-todos"),
};

bootstrap();

function bootstrap() {
  const presetToken = new URLSearchParams(location.search).get("token") ?? loadToken();
  elements.tokenInput.value = presetToken;

  elements.tokenForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const token = elements.tokenInput.value.trim();
    saveToken(token);
    await refreshDashboard();
  });

  elements.refreshButton.addEventListener("click", async () => {
    await refreshDashboard();
  });

  void refreshDashboard();
}

async function refreshDashboard() {
  setStatus("正在读取服务状态...", "idle");

  try {
    const health = await requestJson("/api/health");
    const token = elements.tokenInput.value.trim();
    const overview = await requestJson("/api/admin/overview", token);
    renderDashboard(overview, health);
    const authMessage = health.authRequired
      ? token
        ? "鉴权已启用，当前后台数据已使用 token 读取。"
        : "鉴权已启用，请输入 token 后刷新。"
      : "服务未启用 token，后台数据可直接读取。";
    setStatus(authMessage, "ready");
  } catch (error) {
    console.error(error);
    setStatus(error.message || "读取后台数据失败", "error");
    clearDashboard();
  }
}

function renderDashboard(overview, health) {
  elements.updatedAt.textContent = formatDateTime(overview.time);
  renderStats(overview.totals);
  renderServerMeta(overview, health);
  renderCandidates(overview.server.candidates);
  renderShareMeta(overview.connectLink);
  renderLists(overview.lists);
  renderRecentTodos(overview.recentTodos);
}

function clearDashboard() {
  elements.updatedAt.textContent = "尚未加载";
  elements.statsGrid.innerHTML = "";
  elements.serverMeta.innerHTML = "";
  elements.candidateList.textContent = "后台数据未加载。";
  elements.candidateList.className = "stack-list empty-slot";
  elements.shareMeta.innerHTML = "";
  elements.shareTextBlock.hidden = true;
  elements.shareText.textContent = "";
  elements.listsGrid.textContent = "后台数据未加载。";
  elements.listsGrid.className = "lists-grid empty-slot";
  elements.recentTodos.textContent = "后台数据未加载。";
  elements.recentTodos.className = "todo-stack empty-slot";
}

function renderStats(totals) {
  elements.statsGrid.innerHTML = "";
  elements.statsGrid.className = "stats-grid";

  [
    ["清单数", totals.lists],
    ["任务总数", totals.todos],
    ["待完成", totals.activeTodos],
    ["已完成", totals.completedTodos],
  ].forEach(([label, value]) => {
    const card = document.createElement("article");
    card.className = "stat-card";

    const labelNode = document.createElement("p");
    labelNode.className = "stat-label";
    labelNode.textContent = label;

    const valueNode = document.createElement("p");
    valueNode.className = "stat-value";
    valueNode.textContent = String(value);

    card.append(labelNode, valueNode);
    elements.statsGrid.append(card);
  });
}

function renderServerMeta(overview, health) {
  elements.serverMeta.innerHTML = "";
  appendMeta("HTTP 地址", overview.server.serverUrl);
  appendMeta("WebSocket", overview.server.wsUrl);
  appendMeta("鉴权", health.authRequired ? "已启用" : "未启用");
  appendMeta("数据库路径", overview.database.path);
  appendMeta("数据库大小", formatFileSize(overview.database.sizeBytes));
  appendMeta("候选地址数", String(overview.server.candidateCount));
}

function renderCandidates(candidates) {
  elements.candidateList.innerHTML = "";
  elements.candidateList.className = "stack-list";

  if (!Array.isArray(candidates) || candidates.length === 0) {
    elements.candidateList.textContent = "当前没有可展示的候选连接地址。";
    elements.candidateList.className = "stack-list empty-slot";
    return;
  }

  candidates.forEach((candidate) => {
    const card = document.createElement("article");
    card.className = "candidate-card";

    const title = document.createElement("p");
    title.className = "candidate-url";
    title.textContent = candidate.serverUrl || candidate.host || "";

    const meta = document.createElement("p");
    meta.className = "candidate-meta";
    meta.textContent = `${candidate.kind} · ${candidate.source} · ${candidate.wsUrl || ""}`;

    card.append(title, meta);
    elements.candidateList.append(card);
  });
}

function renderShareMeta(connectLink) {
  elements.shareMeta.innerHTML = "";

  const entries = [
    ["config64", connectLink?.config64 || ""],
    ["Deep Link", connectLink?.deepLinkUrl || ""],
    ["Web 导入", connectLink?.webImportUrl || ""],
    ["二维码值", connectLink?.qrValue || ""],
    ["二维码地址", connectLink?.qrSvgUrl || ""],
  ].filter(([, value]) => Boolean(value));

  if (entries.length === 0) {
    appendShareMeta("提示", "当前没有可展示的导入信息。");
  } else {
    entries.forEach(([label, value]) => appendShareMeta(label, value));
  }

  if (connectLink?.shortText) {
    elements.shareTextBlock.hidden = false;
    elements.shareText.textContent = connectLink.shortText;
    return;
  }

  elements.shareTextBlock.hidden = true;
  elements.shareText.textContent = "";
}

function renderLists(lists) {
  elements.listsGrid.innerHTML = "";
  elements.listsGrid.className = "lists-grid";

  if (!Array.isArray(lists) || lists.length === 0) {
    elements.listsGrid.textContent = "当前还没有清单数据。";
    elements.listsGrid.className = "lists-grid empty-slot";
    return;
  }

  lists.forEach((todoList) => {
    const card = document.createElement("article");
    card.className = "list-card";

    const title = document.createElement("p");
    title.className = "list-title";
    title.textContent = todoList.title || "未命名清单";

    const meta = document.createElement("p");
    meta.className = "list-meta";
    meta.textContent = `${todoList.todoCount} 项任务 · ${todoList.activeTodoCount} 项待完成 · ${todoList.completedTodoCount} 项已完成`;

    card.append(title, meta);
    elements.listsGrid.append(card);
  });
}

function renderRecentTodos(todos) {
  elements.recentTodos.innerHTML = "";
  elements.recentTodos.className = "todo-stack";

  if (!Array.isArray(todos) || todos.length === 0) {
    elements.recentTodos.textContent = "当前还没有任务数据。";
    elements.recentTodos.className = "todo-stack empty-slot";
    return;
  }

  todos.forEach((todo) => {
    const card = document.createElement("article");
    card.className = "todo-card";

    const title = document.createElement("p");
    title.className = "todo-title";
    title.textContent = todo.title || "未命名任务";

    const meta = document.createElement("p");
    meta.className = "todo-meta";
    meta.textContent = `${todo.completed ? "已完成" : "待完成"} · 清单 ${todo.listId} · 更新于 ${formatDateTime(todo.updatedAt)}`;

    card.append(title, meta);
    elements.recentTodos.append(card);
  });
}

function appendMeta(label, value) {
  const dt = document.createElement("dt");
  dt.textContent = label;
  const dd = document.createElement("dd");
  dd.textContent = value || "-";
  elements.serverMeta.append(dt, dd);
}

function appendShareMeta(label, value) {
  const dt = document.createElement("dt");
  dt.textContent = label;
  const dd = document.createElement("dd");
  dd.textContent = value || "-";
  elements.shareMeta.append(dt, dd);
}

function setStatus(message, state) {
  elements.authStatus.textContent = message;
  elements.authStatus.dataset.state = state;
}

async function requestJson(path, token = "") {
  const response = await fetch(path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = typeof payload.error === "string" ? payload.error : `request failed: ${response.status}`;
    throw new Error(message);
  }

  return payload;
}

function saveToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
    return;
  }
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

function loadToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY) ?? "";
}

function formatDateTime(timestamp) {
  if (typeof timestamp !== "number") {
    return "-";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(timestamp);
}

function formatFileSize(sizeBytes) {
  if (typeof sizeBytes !== "number" || sizeBytes <= 0) {
    return "0 B";
  }

  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }

  if (sizeBytes < 1024 * 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`;
  }

  return `${(sizeBytes / (1024 * 1024)).toFixed(2)} MB`;
}
