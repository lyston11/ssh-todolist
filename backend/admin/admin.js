const TOKEN_STORAGE_KEY = "ssh-todolist-services.admin.token";
const THEME_STORAGE_KEY = "ssh-todolist-services.admin.theme";
const TODO_SCOPE_LABELS = {
  all: "全部任务",
  active: "待完成",
  completed: "已完成",
  today: "今天到期",
  overdue: "已逾期",
  unscheduled: "未安排日期",
};
const VIEW_CONFIG = {
  overview: {
    title: "概览",
    description: "查看当前节点的任务总览、清单分布和整体运行状态。",
  },
  config: {
    title: "服务配置",
    description: "管理服务端对外地址、导入入口和 HTTP 日志模式；高级运维信息默认收起，避免干扰普通使用路径。",
  },
  share: {
    title: "导入与分享",
    description: "给 Android、Web 或其他设备分发连接配置、二维码和导入链接。",
  },
  workbench: {
    title: "任务工作台",
    description: "左侧选择清单，右侧集中处理当前清单或全部任务。",
  },
  activity: {
    title: "最近活动",
    description: "查看服务启动、配置变更、清单操作和任务变更，快速定位节点最近发生了什么。",
  },
};

let qrPreviewObjectUrl = "";
let memoryToken = "";
const dashboardState = {
  overview: null,
  health: null,
  adminConfig: null,
  adminActivity: null,
  todoItems: [],
  token: "",
  activeView: "overview",
  todoFilterScope: "all",
  todoFilterList: "all",
  runtimeExpanded: false,
};

const elements = {
  authStatus: document.querySelector("#auth-status"),
  authBadge: document.querySelector("#auth-badge"),
  healthIndicator: document.querySelector("#health-indicator"),
  updatedAt: document.querySelector("#updated-at"),
  themeToggleButton: document.querySelector("#theme-toggle-button"),
  themeToggleIcon: document.querySelector("#theme-toggle-icon"),
  tokenForm: document.querySelector("#token-form"),
  tokenInput: document.querySelector("#token-input"),
  authMessage: document.querySelector("#auth-message"),
  refreshButton: document.querySelector("#refresh-button"),
  viewTitle: document.querySelector("#view-title"),
  viewDescription: document.querySelector("#view-description"),
  viewButtons: Array.from(document.querySelectorAll("[data-view-target]")),
  viewPanels: Array.from(document.querySelectorAll("[data-view-panel]")),
  statsGrid: document.querySelector("#stats-grid"),
  opsFeedback: document.querySelector("#ops-feedback"),
  runtimeSummary: document.querySelector("#runtime-summary"),
  runtimeGrid: document.querySelector("#runtime-grid"),
  installGrid: document.querySelector("#install-grid"),
  runtimeToggleButton: document.querySelector("#runtime-toggle-button"),
  runtimeAdvancedPanel: document.querySelector("#runtime-advanced-panel"),
  configForm: document.querySelector("#config-form"),
  configRefreshButton: document.querySelector("#config-refresh-button"),
  configFeedback: document.querySelector("#config-feedback"),
  configSaveButton: document.querySelector("#config-save-button"),
  configPublicBaseUrl: document.querySelector("#config-public-base-url"),
  configPublicWsBaseUrl: document.querySelector("#config-public-ws-base-url"),
  configAppWebUrl: document.querySelector("#config-app-web-url"),
  configAppDeepLinkBase: document.querySelector("#config-app-deep-link-base"),
  configHttpLogMode: document.querySelector("#config-http-log-mode"),
  configPath: document.querySelector("#config-path"),
  configUpdatedAt: document.querySelector("#config-updated-at"),
  configAuthRequired: document.querySelector("#config-auth-required"),
  serverUrl: document.querySelector("#server-url"),
  wsUrl: document.querySelector("#ws-url"),
  serverEntryActions: document.querySelector("#server-entry-actions"),
  dbPath: document.querySelector("#db-path"),
  dbSize: document.querySelector("#db-size"),
  candidateList: document.querySelector("#candidate-list"),
  shareHint: document.querySelector("#share-hint"),
  shareCards: document.querySelector("#share-cards"),
  shareQrBlock: document.querySelector("#share-qr-block"),
  shareQrPreview: document.querySelector("#share-qr-preview"),
  shareCopyQrValueButton: document.querySelector("#share-copy-qr-value-button"),
  shareDownloadQrButton: document.querySelector("#share-download-qr-button"),
  shareTextBlock: document.querySelector("#share-text-block"),
  shareText: document.querySelector("#share-text"),
  shareCopyTextButton: document.querySelector("#share-copy-text-button"),
  shareFeedback: document.querySelector("#share-feedback"),
  listsGrid: document.querySelector("#lists-grid"),
  listCreateForm: document.querySelector("#list-create-form"),
  listCreateButton: document.querySelector("#list-create-button"),
  listCreateTitle: document.querySelector("#list-create-title"),
  listFeedback: document.querySelector("#list-feedback"),
  listManagerGrid: document.querySelector("#list-manager-grid"),
  workbenchSelectedTitle: document.querySelector("#workbench-selected-title"),
  workbenchSelectedSummary: document.querySelector("#workbench-selected-summary"),
  workbenchListTitleInput: document.querySelector("#workbench-list-title-input"),
  workbenchSaveListButton: document.querySelector("#workbench-save-list-button"),
  workbenchDeleteListButton: document.querySelector("#workbench-delete-list-button"),
  workbenchShowAllButton: document.querySelector("#workbench-show-all-button"),
  todoCreateForm: document.querySelector("#todo-create-form"),
  todoCreateButton: document.querySelector("#todo-create-button"),
  todoCreateTitle: document.querySelector("#todo-create-title"),
  todoCreateList: document.querySelector("#todo-create-list"),
  todoCreateTag: document.querySelector("#todo-create-tag"),
  todoCreateDueAt: document.querySelector("#todo-create-due-at"),
  todoCreateFeedback: document.querySelector("#todo-create-feedback"),
  todoFilterScope: document.querySelector("#todo-filter-scope"),
  todoFilterList: document.querySelector("#todo-filter-list"),
  todoClearCompletedButton: document.querySelector("#todo-clear-completed-button"),
  todoFeedback: document.querySelector("#todo-feedback"),
  recentTodos: document.querySelector("#recent-todos"),
  activitySummaryOpenButton: document.querySelector("#activity-summary-open-button"),
  activityRefreshButton: document.querySelector("#activity-refresh-button"),
  activitySummary: document.querySelector("#activity-summary"),
  activityList: document.querySelector("#activity-list"),
};

bootstrap();

function bootstrap() {
  initializeThemeToggle();
  syncRuntimeAdvancedVisibility();

  const presetToken = readLegacyQueryToken() || loadToken();
  if (presetToken) {
    saveToken(presetToken);
  }
  clearLegacyQueryToken();
  elements.tokenInput.value = presetToken || "";

  elements.tokenForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const token = elements.tokenInput.value.trim();
    saveToken(token);
    await refreshDashboard();
  });

  elements.refreshButton.addEventListener("click", async () => {
    await refreshDashboard();
  });

  elements.configForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await handleConfigSave();
  });

  elements.configRefreshButton?.addEventListener("click", async () => {
    await refreshDashboard();
  });

  elements.activityRefreshButton?.addEventListener("click", async () => {
    await refreshDashboard();
  });

  elements.activitySummaryOpenButton?.addEventListener("click", () => {
    setActiveView("activity");
  });

  elements.runtimeToggleButton?.addEventListener("click", () => {
    dashboardState.runtimeExpanded = !dashboardState.runtimeExpanded;
    syncRuntimeAdvancedVisibility();
  });

  elements.listCreateForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await handleCreateList();
  });

  elements.workbenchShowAllButton?.addEventListener("click", () => {
    focusListInWorkbench("all", { message: "已切换到全部任务。", skipNavigation: true });
  });

  elements.workbenchSaveListButton?.addEventListener("click", async () => {
    await handleSaveSelectedListTitle();
  });

  elements.workbenchDeleteListButton?.addEventListener("click", async () => {
    await handleDeleteSelectedList();
  });

  elements.workbenchListTitleInput?.addEventListener("keydown", async (event) => {
    if (event.key !== "Enter") {
      return;
    }
    event.preventDefault();
    await handleSaveSelectedListTitle();
  });

  elements.todoCreateForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    await handleCreateTodo();
  });

  elements.todoFilterScope.addEventListener("change", () => {
    dashboardState.todoFilterScope = elements.todoFilterScope.value || "all";
    renderFilteredTodos();
  });

  elements.todoFilterList.addEventListener("change", () => {
    dashboardState.todoFilterList = elements.todoFilterList.value || "all";
    if (dashboardState.todoFilterList !== "all") {
      elements.todoCreateList.value = dashboardState.todoFilterList;
    }
    renderListManager(dashboardState.overview?.lists || []);
    renderWorkbenchSelection();
    renderFilteredTodos();
  });

  elements.todoClearCompletedButton.addEventListener("click", async () => {
    await handleClearCompleted();
  });

  document.querySelectorAll("[data-copy-source]").forEach((button) => {
    button.addEventListener("click", () => {
      const sourceId = button.getAttribute("data-copy-source");
      const field = sourceId ? document.getElementById(sourceId) : null;
      if (!(field instanceof HTMLInputElement)) {
        setOpsFeedback("当前没有可复制内容。", "error", true);
        return;
      }
      void copyText(field.value, "内容已复制。", setOpsFeedback);
    });
  });

  initializeViewNavigation();
  void refreshDashboard();
}

function initializeThemeToggle() {
  const initialTheme = loadThemePreference();
  applyTheme(initialTheme);

  elements.themeToggleButton?.addEventListener("click", () => {
    const nextTheme = document.body.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(nextTheme);
    saveThemePreference(nextTheme);
  });
}

function loadThemePreference() {
  const storage = getLocalStorage();
  const savedTheme = storage?.getItem(THEME_STORAGE_KEY)?.trim();
  if (savedTheme === "light" || savedTheme === "dark") {
    return savedTheme;
  }
  return "dark";
}

function saveThemePreference(theme) {
  const storage = getLocalStorage();
  if (!storage) {
    return;
  }
  storage.setItem(THEME_STORAGE_KEY, theme);
}

function applyTheme(theme) {
  const normalizedTheme = theme === "dark" ? "dark" : "light";
  document.body.dataset.theme = normalizedTheme;

  if (!elements.themeToggleButton || !elements.themeToggleIcon) {
    return;
  }

  const nextModeLabel = normalizedTheme === "dark" ? "切换到白天模式" : "切换到夜晚模式";
  elements.themeToggleButton.title = nextModeLabel;
  elements.themeToggleButton.setAttribute("aria-label", nextModeLabel);
  elements.themeToggleIcon.textContent = normalizedTheme === "dark" ? "☀" : "☾";
}

function initializeViewNavigation() {
  elements.viewButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const targetView = button.dataset.viewTarget || "overview";
      setActiveView(targetView);
    });
  });

  window.addEventListener("hashchange", () => {
    setActiveView(location.hash.slice(1), { updateHash: false });
  });

  setActiveView(location.hash.slice(1), { updateHash: false });
}

function syncRuntimeAdvancedVisibility() {
  if (!elements.runtimeAdvancedPanel || !elements.runtimeToggleButton) {
    return;
  }

  elements.runtimeAdvancedPanel.hidden = !dashboardState.runtimeExpanded;
  elements.runtimeToggleButton.textContent = dashboardState.runtimeExpanded ? "收起高级信息" : "展开高级信息";
}

function normalizeView(view) {
  return Object.hasOwn(VIEW_CONFIG, view) ? view : "overview";
}

function setActiveView(view, { updateHash = true } = {}) {
  const normalizedView = normalizeView(view);
  dashboardState.activeView = normalizedView;

  const meta = VIEW_CONFIG[normalizedView];
  if (elements.viewTitle) {
    elements.viewTitle.textContent = meta.title;
  }
  if (elements.viewDescription) {
    elements.viewDescription.textContent = meta.description;
  }

  elements.viewButtons.forEach((button) => {
    button.dataset.active = String(button.dataset.viewTarget === normalizedView);
  });

  elements.viewPanels.forEach((panel) => {
    panel.hidden = panel.dataset.viewPanel !== normalizedView;
  });

  if (!updateHash) {
    return;
  }

  if (location.hash === `#${normalizedView}`) {
    return;
  }

  if (typeof history.replaceState === "function") {
    history.replaceState({}, "", `${location.pathname}#${normalizedView}`);
    return;
  }

  location.hash = normalizedView;
}

async function refreshDashboard() {
  setStatus("正在读取服务状态...", "idle");

  try {
    const health = await requestJson("/api/health");
    const token = elements.tokenInput.value.trim();
    const [overview, adminConfig, adminActivity, todoPayload] = await Promise.all([
      requestJson("/api/admin/overview", token),
      requestJson("/api/admin/config", token),
      requestJson("/api/admin/activity", token),
      requestJson("/api/todos", token),
    ]);
    await renderDashboard(overview, health, token, adminConfig, adminActivity, todoPayload);
    const authMessage = health.authRequired
      ? token
        ? "鉴权已启用，当前后台数据已使用 token 读取。"
        : "鉴权已启用，请输入 token 后刷新。"
      : "服务未启用 token，后台数据可直接读取。";
    setStatus(authMessage, "ready");
  } catch (error) {
    console.error(error);
    const statusMessage = error?.status === 401
      ? "需要有效 token 才能读取后台数据。"
      : error.message || "读取后台数据失败";
    setStatus(statusMessage, "error");
    clearDashboard();
  }
}

async function renderDashboard(overview, health, token, adminConfig, adminActivity, todoPayload) {
  dashboardState.overview = overview;
  dashboardState.health = health;
  dashboardState.adminConfig = adminConfig;
  dashboardState.adminActivity = adminActivity;
  dashboardState.todoItems = buildWorkbenchTodoItems(todoPayload?.items, overview.lists);
  dashboardState.token = token;
  elements.updatedAt.textContent = formatDateTime(overview.time);
  renderStats(overview.totals);
  renderServerMeta(overview, health);
  renderRuntimePanel(overview.runtime);
  renderAdminConfig(adminConfig);
  renderInstallGuide(overview.install);
  renderCandidates(overview.server.candidates);
  renderShareSection(overview.connectLink, health.authRequired);
  await renderShareQr(overview.connectLink, token);
  renderLists(overview.lists);
  renderListManager(overview.lists);
  renderTodoCreateListOptions(overview.lists, overview.defaultListId);
  renderTodoFilters(overview.lists);
  renderWorkbenchSelection();
  renderFilteredTodos();
  renderActivity(adminActivity);
  syncStatusChrome("ready");
}

function clearDashboard() {
  dashboardState.overview = null;
  dashboardState.health = null;
  dashboardState.adminConfig = null;
  dashboardState.adminActivity = null;
  dashboardState.todoItems = [];
  dashboardState.token = "";
  elements.updatedAt.textContent = "尚未加载";
  elements.statsGrid.innerHTML = "";
  setOpsFeedback("", "info", false);
  setConfigFeedback("", "info", false);
  elements.runtimeSummary.textContent = "后台数据未加载。";
  elements.runtimeSummary.className = "runtime-summary empty-slot";
  elements.runtimeGrid.textContent = "后台数据未加载。";
  elements.runtimeGrid.className = "runtime-grid empty-slot";
  elements.installGrid.textContent = "后台数据未加载。";
  elements.installGrid.className = "install-grid empty-slot";
  clearAdminConfigPanel();
  elements.serverUrl.value = "";
  elements.wsUrl.value = "";
  elements.serverEntryActions.textContent = "后台数据未加载。";
  elements.serverEntryActions.className = "server-entry-actions empty-slot";
  elements.dbPath.textContent = "-";
  elements.dbSize.textContent = "0 B";
  elements.candidateList.textContent = "后台数据未加载。";
  elements.candidateList.className = "candidate-list empty-slot";
  elements.shareHint.textContent = "后台数据未加载。";
  elements.shareCards.innerHTML = "";
  elements.shareCards.className = "share-cards empty-slot";
  elements.shareCards.textContent = "后台数据未加载。";
  clearShareQrPreview("后台数据未加载。");
  elements.shareCopyQrValueButton.hidden = true;
  elements.shareDownloadQrButton.hidden = true;
  elements.shareTextBlock.hidden = true;
  elements.shareText.textContent = "";
  elements.shareCopyTextButton.hidden = true;
  setShareFeedback("", false);
  elements.listsGrid.textContent = "后台数据未加载。";
  elements.listsGrid.className = "lists-grid empty-slot";
  elements.listCreateTitle.value = "";
  setListFeedback("", "info", false);
  elements.listManagerGrid.textContent = "后台数据未加载。";
  elements.listManagerGrid.className = "list-manager-grid empty-slot";
  renderWorkbenchSelection();
  elements.todoCreateTitle.value = "";
  elements.todoCreateTag.value = "";
  elements.todoCreateDueAt.value = "";
  elements.todoCreateList.innerHTML = "";
  elements.todoCreateList.disabled = true;
  elements.todoCreateButton.disabled = true;
  setTodoCreateFeedback("", "info", false);
  renderTodoFilters([]);
  renderTodoToolbarState([]);
  setTodoFeedback("", "success", false);
  elements.recentTodos.textContent = "后台数据未加载。";
  elements.recentTodos.className = "todo-stack empty-slot";
  clearActivityPanel();
}

function renderStats(totals) {
  elements.statsGrid.innerHTML = "";
  elements.statsGrid.className = "stats-grid";

  [
    ["清单数", totals.lists],
    ["任务总数", totals.todos],
    ["待完成", totals.activeTodos],
    ["已完成", totals.completedTodos],
    ["今天到期", totals.dueTodayTodos],
    ["已逾期", totals.overdueTodos],
    ["已安排日期", totals.scheduledTodos],
    ["未安排日期", totals.unscheduledTodos],
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
  elements.serverUrl.value = overview.server.serverUrl || "";
  elements.wsUrl.value = overview.server.wsUrl || "";
  renderServerEntryActions(overview, health);
  elements.dbPath.textContent = overview.database.path || "-";
  elements.dbSize.textContent = formatFileSize(overview.database.sizeBytes);
  if (elements.authBadge) {
    if (health.authRequired) {
      const hasToken = Boolean(getCurrentApiToken());
      elements.authBadge.textContent = hasToken ? "Token 已配置" : "需要 Token";
      elements.authBadge.dataset.state = hasToken ? "ready" : "error";
    } else {
      elements.authBadge.textContent = "无需鉴权";
      elements.authBadge.dataset.state = "ready";
    }
  }
}

function renderServerEntryActions(overview, health) {
  if (!elements.serverEntryActions) {
    return;
  }

  elements.serverEntryActions.innerHTML = "";
  elements.serverEntryActions.className = "server-entry-actions";

  const badges = document.createElement("div");
  badges.className = "server-entry-badges";
  badges.append(createTodoBadge(health.authRequired ? "需要 Token" : "局域网直连", health.authRequired ? "warning" : "success"));
  badges.append(createTodoBadge(`候选地址 ${overview.server.candidateCount || 0}`, "muted"));
  badges.append(createTodoBadge(`数据库 ${formatFileSize(overview.database.sizeBytes)}`, "neutral"));

  const actions = document.createElement("div");
  actions.className = "server-entry-action-row";
  actions.append(
    createActionButton("打开后台", () => {
      openExternalLink(overview.runtime?.adminUrl || overview.server.serverUrl, "后台入口", setOpsFeedback);
    }),
    createActionButton("健康检查", () => {
      openExternalLink(overview.runtime?.healthUrl || "", "健康检查接口", setOpsFeedback);
    }),
    createActionButton("连接配置", () => {
      openExternalLink(overview.runtime?.connectConfigUrl || "", "连接配置接口", setOpsFeedback);
    }),
  );

  elements.serverEntryActions.append(badges, actions);
}

function renderCandidates(candidates) {
  elements.candidateList.innerHTML = "";
  elements.candidateList.className = "candidate-list";

  if (!Array.isArray(candidates) || candidates.length === 0) {
    elements.candidateList.textContent = "当前没有可展示的候选连接地址。";
    elements.candidateList.className = "candidate-list empty-slot";
    return;
  }

  candidates.forEach((candidate) => {
    elements.candidateList.append(createCandidateCard(candidate));
  });
}

function createCandidateCard(candidate) {
  const card = document.createElement("article");
  card.className = "candidate-card";

  const header = document.createElement("div");
  header.className = "candidate-card-header";

  const copy = document.createElement("div");

  const title = document.createElement("p");
  title.className = "candidate-url";
  title.textContent = candidate.serverUrl || candidate.host || "";

  const meta = document.createElement("p");
  meta.className = "candidate-meta";
  meta.textContent = `${formatCandidateSource(candidate.source)} · ${formatCandidateKind(candidate.kind)}`;

  copy.append(title, meta);

  const badges = document.createElement("div");
  badges.className = "candidate-badges";
  if (candidate.wsUrl) {
    badges.append(createTodoBadge("含 WS 地址", "accent"));
  }
  if (candidate.kind === "tailscale") {
    badges.append(createTodoBadge("Tailscale", "success"));
  }

  header.append(copy, badges);

  const wsValue = document.createElement("p");
  wsValue.className = "candidate-meta";
  wsValue.textContent = candidate.wsUrl ? `WS: ${candidate.wsUrl}` : "当前候选地址没有可用的 WebSocket 地址。";

  const actions = document.createElement("div");
  actions.className = "candidate-card-actions";
  actions.append(
    createActionButton("复制 HTTP", () => {
      void copyText(candidate.serverUrl || "", "候选 HTTP 地址已复制。", setShareFeedback);
    }),
    createActionButton("复制 WS", () => {
      void copyText(candidate.wsUrl || "", "候选 WS 地址已复制。", setShareFeedback);
    }),
    createActionButton("设为公开地址", async () => {
      await applyCandidateAsPublicEndpoint(candidate);
    }),
  );

  card.append(header, wsValue, actions);
  return card;
}

function renderRuntimePanel(runtime) {
  renderRuntimeSummary(runtime);
  renderRuntimeCards(runtime);
}

function renderAdminConfig(config) {
  if (!config) {
    clearAdminConfigPanel();
    return;
  }

  elements.configPublicBaseUrl.value = config.publicBaseUrl || "";
  elements.configPublicWsBaseUrl.value = config.publicWsBaseUrl || "";
  elements.configAppWebUrl.value = config.appWebUrl || "";
  elements.configAppDeepLinkBase.value = config.appDeepLinkBase || "";
  elements.configHttpLogMode.value = config.httpLogMode || "errors";
  elements.configPath.textContent = config.configPath || "-";
  elements.configUpdatedAt.textContent = formatDateTime(config.time);
  elements.configAuthRequired.textContent = config.authRequired ? "需要 Token" : "无需 Token";
}

function clearAdminConfigPanel() {
  elements.configPublicBaseUrl.value = "";
  elements.configPublicWsBaseUrl.value = "";
  elements.configAppWebUrl.value = "";
  elements.configAppDeepLinkBase.value = "";
  elements.configHttpLogMode.value = "errors";
  elements.configPath.textContent = "-";
  elements.configUpdatedAt.textContent = "尚未加载";
  elements.configAuthRequired.textContent = "-";
}

async function handleConfigSave() {
  const token = getCurrentApiToken();
  const payload = {
    publicBaseUrl: elements.configPublicBaseUrl.value.trim(),
    publicWsBaseUrl: elements.configPublicWsBaseUrl.value.trim(),
    appWebUrl: elements.configAppWebUrl.value.trim(),
    appDeepLinkBase: elements.configAppDeepLinkBase.value.trim(),
    httpLogMode: elements.configHttpLogMode.value || "errors",
  };

  if (elements.configSaveButton) {
    elements.configSaveButton.disabled = true;
  }
  setConfigFeedback("正在保存服务配置...", "info", true);

  try {
    const updated = await requestJsonWithMethod("/api/admin/config", {
      method: "POST",
      token,
      body: payload,
    });
    renderAdminConfig(updated);
    await refreshDashboard();
    setConfigFeedback("服务配置已保存并重新加载。", "success", true);
  } catch (error) {
    console.error(error);
    setConfigFeedback(
      error?.status === 401 ? "保存配置需要有效 token。" : error.message || "保存服务配置失败。",
      "error",
      true,
    );
  } finally {
    if (elements.configSaveButton) {
      elements.configSaveButton.disabled = false;
    }
  }
}

async function handleCreateList() {
  const title = elements.listCreateTitle.value.trim();
  if (!title) {
    setListFeedback("请输入清单名称。", "error", true);
    return;
  }

  if (elements.listCreateButton) {
    elements.listCreateButton.disabled = true;
  }
  setListFeedback("正在创建清单...", "info", true);

  try {
    const created = await requestJsonWithMethod("/api/lists", {
      method: "POST",
      token: getCurrentApiToken(),
      body: { title },
    });
    dashboardState.todoFilterList = created.id || "all";
    elements.listCreateTitle.value = "";
    await refreshDashboard();
    setListFeedback(`清单“${created.title || "未命名清单"}”已创建。`, "success", true);
  } catch (error) {
    console.error(error);
    setListFeedback(error.message || "创建清单失败。", "error", true);
  } finally {
    if (elements.listCreateButton) {
      elements.listCreateButton.disabled = false;
    }
  }
}

async function handleCreateTodo() {
  const title = elements.todoCreateTitle.value.trim();
  if (!title) {
    setTodoCreateFeedback("请输入任务标题。", "error", true);
    return;
  }

  const dateValue = elements.todoCreateDueAt.value || "";
  const dueAt = parseDateInputToTimestamp(dateValue);
  if (dateValue && dueAt === null) {
    setTodoCreateFeedback("截止日期格式无效，请重新选择。", "error", true);
    return;
  }

  const payload = {
    title,
    listId: elements.todoCreateList.value || undefined,
    tag: elements.todoCreateTag.value.trim() || undefined,
    ...(dateValue ? { dueAt } : {}),
  };

  if (elements.todoCreateButton) {
    elements.todoCreateButton.disabled = true;
  }
  setTodoCreateFeedback("正在创建任务...", "info", true);

  try {
    const created = await requestJsonWithMethod("/api/todos", {
      method: "POST",
      token: getCurrentApiToken(),
      body: payload,
    });
    dashboardState.todoFilterList = created.listId || dashboardState.todoFilterList;
    dashboardState.todoFilterScope = "all";
    elements.todoCreateTitle.value = "";
    elements.todoCreateTag.value = "";
    elements.todoCreateDueAt.value = "";
    await refreshDashboard();
    if (created.listId) {
      elements.todoCreateList.value = created.listId;
    }
    setTodoCreateFeedback(`任务“${created.title || "未命名任务"}”已创建。`, "success", true);
  } catch (error) {
    console.error(error);
    setTodoCreateFeedback(error.message || "创建任务失败。", "error", true);
  } finally {
    if (elements.todoCreateButton) {
      elements.todoCreateButton.disabled = false;
    }
  }
}

function renderRuntimeSummary(runtime) {
  elements.runtimeSummary.innerHTML = "";
  elements.runtimeSummary.className = "runtime-summary";

  if (!runtime) {
    elements.runtimeSummary.textContent = "当前没有可展示的运行摘要。";
    elements.runtimeSummary.className = "runtime-summary empty-slot";
    return;
  }

  const title = document.createElement("p");
  title.className = "runtime-summary-title";
  title.textContent = runtime.serverUrl
    ? `当前节点正在对外提供 ${runtime.serverUrl}`
    : "当前还没有可用的对外服务地址";

  const copy = document.createElement("p");
  copy.className = "runtime-summary-copy";
  copy.textContent = runtime.authSummary || "运行摘要暂不可用。";

  const detail = document.createElement("p");
  detail.className = "runtime-summary-copy";
  detail.textContent = runtime.databaseExists
    ? `项目目录 ${runtime.projectDir || "-"} · 数据库 ${runtime.databasePath || "-"} · ${formatFileSize(runtime.databaseSizeBytes)}`
    : `项目目录 ${runtime.projectDir || "-"} · 数据库文件尚未创建`;

  const tags = document.createElement("div");
  tags.className = "runtime-summary-tags";
  tags.append(createTodoBadge(`HTTP ${runtime.httpPort || "-"}`, "accent"));
  tags.append(createTodoBadge(`WS ${runtime.wsPort || "-"}`, "accent"));
  tags.append(createTodoBadge(runtime.authRequired ? "需要 Token" : "局域网直连", runtime.authRequired ? "warning" : "success"));
  tags.append(
    createTodoBadge(
      runtime.databaseExists ? `数据库 ${formatFileSize(runtime.databaseSizeBytes)}` : "数据库未创建",
      runtime.databaseExists ? "neutral" : "danger",
    ),
  );

  elements.runtimeSummary.append(title, copy, detail, tags);
}

function renderRuntimeCards(runtime) {
  elements.runtimeGrid.innerHTML = "";
  elements.runtimeGrid.className = "runtime-grid";

  if (!runtime) {
    elements.runtimeGrid.textContent = "当前没有可展示的服务入口。";
    elements.runtimeGrid.className = "runtime-grid empty-slot";
    return;
  }

  const cards = [
    {
      label: "控制台",
      title: "后台入口",
      value: runtime.adminUrl || runtime.serverUrl || "",
      copy: "这是当前默认展示给你的后台入口地址。",
      canOpen: true,
    },
    {
      label: "健康检查",
      title: "健康接口",
      value: runtime.healthUrl || "",
      copy: "部署完成后优先用它检查服务是否正常响应。",
      canOpen: true,
    },
    {
      label: "数据接口",
      title: "快照接口",
      value: runtime.snapshotUrl || "",
      copy: "客户端和后台都依赖它获取当前完整任务快照。",
      canOpen: true,
    },
    {
      label: "连接配置",
      title: "Config 接口",
      value: runtime.connectConfigUrl || "",
      copy: "给客户端导入 serverUrl / wsUrl / token 的标准配置入口。",
      canOpen: true,
    },
    {
      label: "分享入口",
      title: "导入链接接口",
      value: runtime.connectLinkUrl || "",
      copy: "生成 deep link / web import / config64 的服务端出口。",
      canOpen: true,
    },
    {
      label: "实时同步",
      title: "WebSocket 地址",
      value: runtime.wsUrl || "",
      copy: "客户端建立实时同步连接时使用的 WS 基地址。",
      canOpen: false,
    },
  ];

  if (runtime.adminAliasUrl && runtime.adminAliasUrl !== runtime.adminUrl) {
    cards.push({
      label: "兼容别名",
      title: "/admin 入口",
      value: runtime.adminAliasUrl,
      copy: "保留兼容访问地址，方便你从固定后台路径进入。",
      canOpen: true,
    });
  }

  cards.forEach((config) => {
    elements.runtimeGrid.append(createRuntimeCard(config));
  });
}

function createRuntimeCard({ label, title, value, copy, canOpen }) {
  const card = document.createElement("article");
  card.className = "runtime-card";

  const header = document.createElement("div");
  header.className = "runtime-card-header";

  const content = document.createElement("div");

  const labelNode = document.createElement("p");
  labelNode.className = "runtime-card-label";
  labelNode.textContent = label;

  const titleNode = document.createElement("p");
  titleNode.className = "runtime-card-title";
  titleNode.textContent = title;

  const copyNode = document.createElement("p");
  copyNode.className = "runtime-card-copy";
  copyNode.textContent = copy;

  content.append(labelNode, titleNode, copyNode);
  header.append(content);

  const valueNode = document.createElement("pre");
  valueNode.className = "runtime-card-value";
  valueNode.textContent = value || "当前暂无地址";

  const actions = document.createElement("div");
  actions.className = "runtime-card-actions";
  actions.append(
    createActionButton("复制地址", () => {
      void copyText(value, `${title}已复制。`, setOpsFeedback);
    }),
  );

  if (canOpen && value) {
    actions.append(
      createActionButton("新窗口打开", () => {
        window.open(value, "_blank", "noopener,noreferrer");
        setOpsFeedback(`已尝试打开 ${title}。`, "info", true);
      }),
    );
  }

  card.append(header, valueNode, actions);
  return card;
}

function renderInstallGuide(install) {
  elements.installGrid.innerHTML = "";
  elements.installGrid.className = "install-grid";

  const methods = Array.isArray(install?.methods) ? install.methods : [];
  if (methods.length === 0) {
    elements.installGrid.textContent = "当前没有可展示的安装方式。";
    elements.installGrid.className = "install-grid empty-slot";
    return;
  }

  methods.forEach((method) => {
    elements.installGrid.append(createInstallCard(method));
  });
}

function createInstallCard(method) {
  const card = document.createElement("article");
  card.className = "install-card";

  const header = document.createElement("div");
  header.className = "install-card-header";

  const titleBlock = document.createElement("div");

  const title = document.createElement("p");
  title.className = "install-card-title";
  title.textContent = method.title || "未命名方式";

  const summary = document.createElement("p");
  summary.className = "install-card-summary";
  summary.textContent = method.summary || "";

  titleBlock.append(title, summary);
  header.append(titleBlock);

  if (method.recommended) {
    header.append(createTodoBadge("推荐", "success"));
  }

  const command = document.createElement("pre");
  command.className = "install-command";
  command.textContent = method.command || "当前没有可展示的命令。";

  const actions = document.createElement("div");
  actions.className = "install-card-actions";
  actions.append(
    createActionButton("复制命令", () => {
      void copyText(method.command || "", `${method.title || "部署命令"}已复制。`, setOpsFeedback);
    }),
  );

  const notes = document.createElement("div");
  notes.className = "install-notes";
  (Array.isArray(method.notes) ? method.notes : []).forEach((note) => {
    const noteNode = document.createElement("p");
    noteNode.className = "install-note";
    noteNode.textContent = note;
    notes.append(noteNode);
  });

  card.append(header, command, actions);
  if (notes.childNodes.length > 0) {
    card.append(notes);
  }
  return card;
}

function renderShareSection(connectLink, authRequired) {
  setShareFeedback("", false);
  elements.shareCards.innerHTML = "";
  elements.shareCards.className = "share-cards";

  const cards = [
    buildShareCardConfig({
      title: "Android App 导入",
      copy: "直接唤起 Android 客户端导入，适合你已经装好 app 的设备。",
      value: connectLink?.deepLinkUrl || "",
      actions: [
        createCopyAction("复制链接", connectLink?.deepLinkUrl || ""),
        createOpenAction("打开链接", connectLink?.deepLinkUrl || ""),
      ],
    }),
    buildShareCardConfig({
      title: "Web 导入链接",
      copy: "浏览器端可直接打开，适合桌面 Web 或中转到其他设备。",
      value: connectLink?.webImportUrl || "",
      actions: [
        createCopyAction("复制链接", connectLink?.webImportUrl || ""),
        createOpenAction("浏览器打开", connectLink?.webImportUrl || ""),
      ],
    }),
    buildShareCardConfig({
      title: "config64 载荷",
      copy: "给剪贴板导入、命令行调试或手动粘贴使用。",
      value: connectLink?.config64 || "",
      actions: [
        createCopyAction("复制 config64", connectLink?.config64 || ""),
      ],
    }),
  ].filter(Boolean);

  if (cards.length === 0) {
    elements.shareCards.className = "share-cards empty-slot";
    elements.shareCards.textContent = "当前没有可展示的导入动作。";
  } else {
    cards.forEach((config) => {
      elements.shareCards.append(createShareCard(config));
    });
  }

  elements.shareHint.textContent = authRequired
    ? "这些导入链接和二维码都包含访问 token，只应该分享给你自己的设备。"
    : "当前服务未启用 token，导入链接可直接在你的设备间使用。";

  if (connectLink?.shortText) {
    elements.shareTextBlock.hidden = false;
    elements.shareText.textContent = connectLink.shortText;
    elements.shareCopyTextButton.hidden = false;
    elements.shareCopyTextButton.onclick = () => {
      void copyText(connectLink.shortText, "短分享文本已复制。");
    };
    return;
  }

  elements.shareTextBlock.hidden = true;
  elements.shareText.textContent = "";
  elements.shareCopyTextButton.hidden = true;
}

async function renderShareQr(connectLink, token) {
  const qrPath = connectLink?.qrSvgPath || "";
  if (!qrPath) {
    clearShareQrPreview("当前没有可展示的二维码。");
    return;
  }

  try {
    const svg = await requestText(qrPath, token);
    const objectUrl = URL.createObjectURL(new Blob([svg], { type: "image/svg+xml" }));
    clearShareQrPreview();
    qrPreviewObjectUrl = objectUrl;
    elements.shareQrBlock.hidden = false;
    elements.shareQrPreview.className = "share-qr-preview";
    elements.shareQrPreview.innerHTML = "";

    const image = document.createElement("img");
    image.src = objectUrl;
    image.alt = "客户端导入二维码";
    elements.shareQrPreview.append(image);
    elements.shareCopyQrValueButton.hidden = !connectLink?.qrValue;
    elements.shareDownloadQrButton.hidden = false;
    elements.shareCopyQrValueButton.onclick = () => {
      void copyText(connectLink.qrValue, "二维码编码文本已复制。");
    };
    elements.shareDownloadQrButton.onclick = () => {
      downloadObjectUrl(objectUrl, "ssh-todolist-connect-qr.svg");
      setShareFeedback("二维码 SVG 已开始下载。", true);
    };
  } catch (error) {
    console.error(error);
    clearShareQrPreview(error?.status === 401 ? "二维码读取需要有效 token。" : "二维码加载失败，请确认 token 或服务状态。");
  }
}

function clearShareQrPreview(message = "当前没有可展示的二维码。") {
  if (qrPreviewObjectUrl) {
    URL.revokeObjectURL(qrPreviewObjectUrl);
    qrPreviewObjectUrl = "";
  }

  elements.shareQrBlock.hidden = false;
  elements.shareQrPreview.innerHTML = "";
  elements.shareQrPreview.className = "share-qr-preview empty-slot";
  elements.shareQrPreview.textContent = message;
  elements.shareCopyQrValueButton.hidden = true;
  elements.shareDownloadQrButton.hidden = true;
  elements.shareCopyQrValueButton.onclick = null;
  elements.shareDownloadQrButton.onclick = null;
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
    elements.listsGrid.append(createOverviewListCard(todoList));
  });
}

function createOverviewListCard(todoList) {
  const card = document.createElement("article");
  card.className = "list-card";

  const title = document.createElement("p");
  title.className = "list-title";
  title.textContent = todoList.title || "未命名清单";

  const meta = document.createElement("p");
  meta.className = "list-meta";
  meta.textContent = `${todoList.todoCount} 项任务 · ${todoList.activeTodoCount} 项待完成 · ${todoList.completedTodoCount} 项已完成`;

  const badges = document.createElement("div");
  badges.className = "list-badges";
  badges.append(createTodoBadge(`今天到期 ${todoList.dueTodayTodoCount || 0}`, "warning"));
  badges.append(createTodoBadge(`已逾期 ${todoList.overdueTodoCount || 0}`, "danger"));

  const footer = document.createElement("div");
  footer.className = "list-card-footer";

  const updatedAt = document.createElement("p");
  updatedAt.className = "list-meta";
  updatedAt.textContent = `最近更新 ${formatDateTime(todoList.updatedAt || todoList.createdAt)}`;

  const action = createActionButton("在工作台查看", () => {
    focusListInWorkbench(todoList.id, { message: `已切换到清单“${todoList.title || "未命名清单"}”。` });
  });

  footer.append(updatedAt, action);
  card.append(title, meta, badges, footer);
  return card;
}

function renderListManager(lists) {
  elements.listManagerGrid.innerHTML = "";
  elements.listManagerGrid.className = "list-manager-grid";

  if (!Array.isArray(lists) || lists.length === 0) {
    elements.listManagerGrid.textContent = "当前还没有可管理的清单。";
    elements.listManagerGrid.className = "list-manager-grid empty-slot";
    return;
  }

  elements.listManagerGrid.append(createListNavigationCard(null, { isAll: true }));
  lists.forEach((todoList) => {
    elements.listManagerGrid.append(createListNavigationCard(todoList));
  });
}

function createListNavigationCard(todoList, { isAll = false } = {}) {
  const card = document.createElement("button");
  const isSelected = isAll ? dashboardState.todoFilterList === "all" : dashboardState.todoFilterList === todoList?.id;
  card.className = "list-manager-card";
  card.type = "button";
  card.dataset.selected = String(isSelected);
  card.dataset.kind = isAll ? "all" : "list";

  const header = document.createElement("div");
  header.className = "list-manager-header";

  const copy = document.createElement("div");
  copy.className = "list-manager-copy";

  const title = document.createElement("p");
  title.className = "list-manager-title";
  title.textContent = isAll ? "全部任务" : (todoList.title || "未命名清单");

  const detail = document.createElement("p");
  detail.className = "list-manager-detail";
  detail.textContent = isAll
    ? `${dashboardState.overview?.totals?.todos || 0} 项任务 · ${dashboardState.overview?.totals?.activeTodos || 0} 项待完成 · ${dashboardState.overview?.totals?.completedTodos || 0} 项已完成`
    : `${todoList.todoCount || 0} 项任务 · ${todoList.activeTodoCount || 0} 项待完成 · ${todoList.completedTodoCount || 0} 项已完成`;

  const focusHint = document.createElement("p");
  focusHint.className = "list-manager-hint";
  focusHint.textContent = isSelected
    ? "当前工作区"
    : (isAll ? "查看全部清单中的任务" : "切换到这个清单继续处理");

  copy.append(title, detail, focusHint);

  const badges = document.createElement("div");
  badges.className = "list-badges";
  if (isAll) {
    badges.append(createTodoBadge(`清单 ${dashboardState.overview?.totals?.lists || 0}`, "muted"));
    badges.append(createTodoBadge(`今天到期 ${dashboardState.overview?.totals?.dueTodayTodos || 0}`, "warning"));
    badges.append(createTodoBadge(`已逾期 ${dashboardState.overview?.totals?.overdueTodos || 0}`, "danger"));
  } else {
    badges.append(createTodoBadge(`今天到期 ${todoList.dueTodayTodoCount || 0}`, "warning"));
    badges.append(createTodoBadge(`已逾期 ${todoList.overdueTodoCount || 0}`, "danger"));
  }
  if (isSelected) {
    badges.prepend(createTodoBadge("当前视图", "accent"));
  }

  header.append(copy, badges);
  card.append(header);
  card.addEventListener("click", () => {
    focusListInWorkbench(isAll ? "all" : todoList.id, {
      message: isAll
        ? "已切换到全部任务。"
        : `已切换到清单“${todoList.title || "未命名清单"}”。`,
      skipNavigation: true,
    });
  });
  return card;
}

function renderTodoCreateListOptions(lists, defaultListId) {
  const normalizedLists = Array.isArray(lists) ? lists : [];
  const preferredListId = elements.todoCreateList.value
    || (dashboardState.todoFilterList !== "all" ? dashboardState.todoFilterList : "")
    || defaultListId
    || normalizedLists[0]?.id
    || "";

  elements.todoCreateList.innerHTML = "";

  if (normalizedLists.length === 0) {
    elements.todoCreateList.append(createSelectOption("", "当前没有清单"));
    elements.todoCreateList.disabled = true;
    elements.todoCreateButton.disabled = true;
    return;
  }

  normalizedLists.forEach((todoList) => {
    elements.todoCreateList.append(createSelectOption(todoList.id || "", todoList.title || "未命名清单"));
  });

  const availableListIds = new Set(normalizedLists.map((todoList) => todoList.id));
  elements.todoCreateList.value = availableListIds.has(preferredListId)
    ? preferredListId
    : (defaultListId && availableListIds.has(defaultListId) ? defaultListId : normalizedLists[0].id || "");
  elements.todoCreateList.disabled = false;
  elements.todoCreateButton.disabled = false;
}

function renderTodoFilters(lists) {
  const normalizedLists = Array.isArray(lists) ? lists : [];
  const knownListIds = new Set(normalizedLists.map((todoList) => todoList.id));
  if (!knownListIds.has(dashboardState.todoFilterList)) {
    dashboardState.todoFilterList = "all";
  }

  elements.todoFilterScope.value = dashboardState.todoFilterScope;
  elements.todoFilterList.innerHTML = "";
  elements.todoFilterList.append(
    createSelectOption("all", "全部清单"),
  );
  normalizedLists.forEach((todoList) => {
    const label = `${todoList.title || "未命名清单"} (${todoList.activeTodoCount}/${todoList.todoCount})`;
    elements.todoFilterList.append(createSelectOption(todoList.id || "", label));
  });
  elements.todoFilterList.value = dashboardState.todoFilterList;
}

function renderFilteredTodos() {
  const filteredTodos = dashboardState.todoItems.filter((todo) => {
    if (!matchesTodoScope(todo, dashboardState.todoFilterScope)) {
      return false;
    }
    if (dashboardState.todoFilterList !== "all" && todo.listId !== dashboardState.todoFilterList) {
      return false;
    }
    return true;
  });
  renderTodoToolbarState(filteredTodos);
  renderRecentTodos(filteredTodos);
}

function renderActivity(activityPayload) {
  const items = Array.isArray(activityPayload?.items) ? activityPayload.items : [];
  renderActivitySummary(items, activityPayload?.time);
  renderActivityList(items);
}

function renderActivitySummary(items, refreshedAt) {
  elements.activitySummary.innerHTML = "";
  elements.activitySummary.className = "activity-summary";

  if (!items.length) {
    elements.activitySummary.textContent = "最近还没有服务活动。创建清单、保存配置或同步任务后，这里会显示真实记录。";
    elements.activitySummary.className = "activity-summary empty-slot";
    return;
  }

  const metrics = document.createElement("div");
  metrics.className = "activity-summary-metrics";

  const total = createActivityMetric("最近活动", String(items.length));
  const warnings = createActivityMetric(
    "警告事件",
    String(items.filter((item) => item.level === "warning").length),
  );
  const latest = createActivityMetric("最新事件", formatDateTime(items[0]?.time || refreshedAt));
  latest.classList.add("activity-metric-compact");
  metrics.append(total, warnings, latest);

  const previewList = document.createElement("div");
  previewList.className = "activity-preview-list";
  items.slice(0, 3).forEach((item) => {
    previewList.append(createActivityPreviewItem(item));
  });

  elements.activitySummary.append(metrics, previewList);
}

function renderActivityList(items) {
  elements.activityList.innerHTML = "";
  elements.activityList.className = "activity-list";

  if (!items.length) {
    elements.activityList.textContent = "最近还没有活动记录。";
    elements.activityList.className = "activity-list empty-slot";
    return;
  }

  items.forEach((item) => {
    elements.activityList.append(createActivityCard(item));
  });
}

function clearActivityPanel() {
  elements.activitySummary.textContent = "后台数据未加载。";
  elements.activitySummary.className = "activity-summary empty-slot";
  elements.activityList.textContent = "后台数据未加载。";
  elements.activityList.className = "activity-list empty-slot";
}

function createActivityMetric(label, value) {
  const card = document.createElement("article");
  card.className = "activity-metric";

  const labelNode = document.createElement("p");
  labelNode.className = "activity-metric-label";
  labelNode.textContent = label;

  const valueNode = document.createElement("p");
  valueNode.className = "activity-metric-value";
  valueNode.textContent = value || "-";

  card.append(labelNode, valueNode);
  return card;
}

function createActivityPreviewItem(item) {
  const row = document.createElement("article");
  row.className = "activity-preview-item";
  row.dataset.level = item.level || "info";

  const copy = document.createElement("div");
  copy.className = "activity-preview-copy";

  const title = document.createElement("p");
  title.className = "activity-preview-title";
  title.textContent = item.title || "未命名活动";

  const detail = document.createElement("p");
  detail.className = "activity-preview-detail";
  detail.textContent = item.detail || "没有附加说明。";

  copy.append(title, detail);

  const time = document.createElement("p");
  time.className = "activity-preview-time";
  time.textContent = formatDateTime(item.time);

  row.append(copy, time);
  return row;
}

function createActivityCard(item) {
  const card = document.createElement("article");
  card.className = "activity-card";
  card.dataset.level = item.level || "info";

  const header = document.createElement("div");
  header.className = "activity-card-header";

  const titleBlock = document.createElement("div");
  titleBlock.className = "activity-card-copy";

  const title = document.createElement("p");
  title.className = "activity-card-title";
  title.textContent = item.title || "未命名活动";

  const detail = document.createElement("p");
  detail.className = "activity-card-detail";
  detail.textContent = item.detail || "没有附加说明。";

  titleBlock.append(title, detail);

  const meta = document.createElement("div");
  meta.className = "activity-card-meta";
  meta.append(createTodoBadge(item.kind || "activity", item.level === "warning" ? "warning" : "accent"));
  if (item.entity_type) {
    meta.append(createTodoBadge(item.entity_type, "muted"));
  }

  header.append(titleBlock, meta);

  const footer = document.createElement("div");
  footer.className = "activity-card-footer";
  footer.textContent = `${formatDateTime(item.time)}${item.entity_id ? ` · ${item.entity_id}` : ""}`;

  card.append(header, footer);
  return card;
}

function renderRecentTodos(todos) {
  elements.recentTodos.innerHTML = "";
  elements.recentTodos.className = "todo-stack";

  if (!Array.isArray(todos) || todos.length === 0) {
    elements.recentTodos.textContent = buildTodoEmptyCopy();
    elements.recentTodos.className = "todo-stack empty-slot";
    return;
  }

  todos.forEach((todo) => {
    elements.recentTodos.append(createTodoCard(todo));
  });
}

function setStatus(message, state) {
  elements.authStatus.textContent = message;
  elements.authStatus.dataset.state = state;
  if (elements.authMessage) {
    elements.authMessage.textContent = message;
    elements.authMessage.hidden = !message;
    elements.authMessage.className = `alert ${state === "error" ? "alert-danger" : state === "ready" ? "alert-success" : "alert-info"}`;
  }
  syncStatusChrome(state);
}

function setShareFeedback(message, toneOrVisible = "info", visible = true) {
  const tone = typeof toneOrVisible === "string" ? toneOrVisible : "info";
  const isVisible = typeof toneOrVisible === "boolean" ? toneOrVisible : visible;
  elements.shareFeedback.textContent = message;
  elements.shareFeedback.hidden = !isVisible || !message;
  elements.shareFeedback.className = `alert ${tone === "error" ? "alert-danger" : tone === "success" ? "alert-success" : "alert-info"}`;
}

function setConfigFeedback(message, tone = "info", visible = true) {
  elements.configFeedback.textContent = message;
  elements.configFeedback.hidden = !visible || !message;
  elements.configFeedback.className = `alert ${tone === "error" ? "alert-danger" : tone === "success" ? "alert-success" : "alert-info"}`;
}

function setListFeedback(message, tone = "info", visible = true) {
  elements.listFeedback.textContent = message;
  elements.listFeedback.hidden = !visible || !message;
  elements.listFeedback.className = `alert ${tone === "error" ? "alert-danger" : tone === "success" ? "alert-success" : "alert-info"}`;
}

function setTodoCreateFeedback(message, tone = "info", visible = true) {
  elements.todoCreateFeedback.textContent = message;
  elements.todoCreateFeedback.hidden = !visible || !message;
  elements.todoCreateFeedback.className = `alert ${tone === "error" ? "alert-danger" : tone === "success" ? "alert-success" : "alert-info"}`;
}

function setOpsFeedback(message, tone = "info", visible = true) {
  elements.opsFeedback.textContent = message;
  elements.opsFeedback.hidden = !visible || !message;
  elements.opsFeedback.className = `alert ${tone === "error" ? "alert-danger" : tone === "success" ? "alert-success" : "alert-info"}`;
}

function setTodoFeedback(message, tone = "success", visible = true) {
  elements.todoFeedback.textContent = message;
  elements.todoFeedback.dataset.tone = tone;
  elements.todoFeedback.hidden = !visible || !message;
}

function syncStatusChrome(state) {
  if (elements.healthIndicator) {
    elements.healthIndicator.dataset.state = state === "error" ? "error" : state === "ready" ? "ready" : "unknown";
  }

  if (!elements.authBadge) {
    return;
  }

  if (state === "error") {
    elements.authBadge.textContent = "读取失败";
    elements.authBadge.dataset.state = "error";
    return;
  }

  if (dashboardState.health) {
    return;
  }

  if (state === "idle") {
    elements.authBadge.textContent = "读取中";
    elements.authBadge.dataset.state = "unknown";
  }
}

function createSelectOption(value, label) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = label;
  return option;
}

function matchesTodoScope(todo, scope) {
  switch (scope) {
    case "active":
      return !todo.completed;
    case "completed":
      return Boolean(todo.completed);
    case "today":
      return todo.dueBucket === "today";
    case "overdue":
      return todo.dueBucket === "overdue";
    case "unscheduled":
      return todo.dueBucket === "unscheduled";
    case "all":
    default:
      return true;
  }
}

function buildTodoEmptyCopy() {
  const scopeLabel = TODO_SCOPE_LABELS[dashboardState.todoFilterScope] || TODO_SCOPE_LABELS.all;
  const listTitle = getSelectedListTitle();
  if (listTitle) {
    return `${listTitle} 中没有符合“${scopeLabel}”条件的任务。`;
  }
  return `当前没有符合“${scopeLabel}”条件的任务。`;
}

function getSelectedList() {
  if (dashboardState.todoFilterList === "all") {
    return null;
  }

  return (dashboardState.overview?.lists || []).find(
    (todoList) => todoList.id === dashboardState.todoFilterList,
  ) || null;
}

function getSelectedListTitle() {
  return getSelectedList()?.title || "";
}

function renderWorkbenchSelection() {
  if (!elements.workbenchSelectedTitle || !elements.workbenchSelectedSummary || !elements.workbenchListTitleInput) {
    return;
  }

  if (!dashboardState.overview) {
    elements.workbenchSelectedTitle.textContent = "全部任务";
    elements.workbenchSelectedSummary.textContent = "左侧选择清单后，这里会切换到对应清单的任务视图。";
    elements.workbenchListTitleInput.value = "";
    elements.workbenchListTitleInput.disabled = true;
    elements.workbenchListTitleInput.placeholder = "选择清单后可在这里改名";
    if (elements.workbenchSaveListButton) {
      elements.workbenchSaveListButton.disabled = true;
    }
    if (elements.workbenchDeleteListButton) {
      elements.workbenchDeleteListButton.disabled = true;
    }
    if (elements.workbenchShowAllButton) {
      elements.workbenchShowAllButton.disabled = true;
    }
    return;
  }

  const selectedList = getSelectedList();
  if (!selectedList) {
    elements.workbenchSelectedTitle.textContent = "全部任务";
    elements.workbenchSelectedSummary.textContent = `当前查看全部清单，共 ${dashboardState.overview.totals?.todos || 0} 项任务，${dashboardState.overview.totals?.activeTodos || 0} 项待完成，${dashboardState.overview.totals?.completedTodos || 0} 项已完成。`;
    elements.workbenchListTitleInput.value = "";
    elements.workbenchListTitleInput.disabled = true;
    elements.workbenchListTitleInput.placeholder = "选择具体清单后可在这里改名";
    if (elements.workbenchSaveListButton) {
      elements.workbenchSaveListButton.disabled = true;
    }
    if (elements.workbenchDeleteListButton) {
      elements.workbenchDeleteListButton.disabled = true;
    }
    if (elements.workbenchShowAllButton) {
      elements.workbenchShowAllButton.disabled = true;
    }
    return;
  }

  elements.workbenchSelectedTitle.textContent = selectedList.title || "未命名清单";
  elements.workbenchSelectedSummary.textContent = `当前清单共有 ${selectedList.todoCount || 0} 项任务，${selectedList.activeTodoCount || 0} 项待完成，${selectedList.completedTodoCount || 0} 项已完成，今天到期 ${selectedList.dueTodayTodoCount || 0} 项，已逾期 ${selectedList.overdueTodoCount || 0} 项。`;
  elements.workbenchListTitleInput.value = selectedList.title || "";
  elements.workbenchListTitleInput.disabled = false;
  elements.workbenchListTitleInput.placeholder = "输入新的清单名称";
  if (elements.workbenchSaveListButton) {
    elements.workbenchSaveListButton.disabled = false;
  }
  if (elements.workbenchDeleteListButton) {
    elements.workbenchDeleteListButton.disabled = (dashboardState.overview.lists || []).length <= 1;
  }
  if (elements.workbenchShowAllButton) {
    elements.workbenchShowAllButton.disabled = false;
  }
}

function renderTodoToolbarState(filteredTodos) {
  const filteredCount = Array.isArray(filteredTodos) ? filteredTodos.length : 0;
  const completedCount = getCompletedTodoCountForSelectedList();
  elements.todoClearCompletedButton.textContent = dashboardState.todoFilterList === "all"
    ? `清空全部清单已完成 (${completedCount})`
    : `清空当前清单已完成 (${completedCount})`;
  elements.todoClearCompletedButton.disabled = !dashboardState.overview || completedCount <= 0;

  if (!dashboardState.overview) {
    return;
  }

  if (filteredCount > 0) {
    const listTitle = getSelectedListTitle();
    const scopeLabel = TODO_SCOPE_LABELS[dashboardState.todoFilterScope] || TODO_SCOPE_LABELS.all;
    const prefix = listTitle ? `${listTitle} · ${scopeLabel}` : scopeLabel;
    setTodoFeedback(`当前展示 ${filteredCount} 条任务 · ${prefix}`, "info", true);
    return;
  }

  setTodoFeedback(buildTodoEmptyCopy(), "info", true);
}

function getCompletedTodoCountForSelectedList() {
  if (!dashboardState.overview) {
    return 0;
  }

  if (dashboardState.todoFilterList === "all") {
    return Number(dashboardState.overview.totals?.completedTodos || 0);
  }

  const selectedList = (dashboardState.overview.lists || []).find(
    (todoList) => todoList.id === dashboardState.todoFilterList,
  );
  return Number(selectedList?.completedTodoCount || 0);
}

function createTodoCard(todo) {
  const card = document.createElement("article");
  card.className = "todo-card";

  const head = document.createElement("div");
  head.className = "todo-card-head";

  const copy = document.createElement("div");
  copy.className = "todo-card-copy";

  const title = document.createElement("p");
  title.className = "todo-title";
  title.textContent = todo.title || "未命名任务";

  const badges = document.createElement("div");
  badges.className = "todo-badges";
  badges.append(createTodoBadge(todo.completed ? "已完成" : "待完成", todo.completed ? "success" : "neutral"));

  if (!todo.completed) {
    const dueBadge = getDueBadge(todo.dueBucket);
    if (dueBadge) {
      badges.append(createTodoBadge(dueBadge.label, dueBadge.tone));
    }
  }

  const listTitle = todo.listTitle || todo.listId || "未分配清单";
  badges.append(createTodoBadge(listTitle, "muted"));

  if (todo.tag) {
    badges.append(createTodoBadge(`#${todo.tag}`, "accent"));
  }

  const meta = document.createElement("p");
  meta.className = "todo-meta";
  meta.textContent = `更新于 ${formatDateTime(todo.updatedAt || todo.createdAt)}`;

  const due = document.createElement("p");
  due.className = "todo-due";
  due.textContent = buildDueDescription(todo);

  const footer = document.createElement("div");
  footer.className = "todo-card-footer";

  const actions = document.createElement("div");
  actions.className = "todo-actions";
  actions.append(
    createTodoToggleButton(todo),
    createTodoDeleteButton(todo),
  );

  const editors = document.createElement("div");
  editors.className = "todo-control-grid";
  editors.append(
    createTodoListControl(todo),
    createTodoDueControl(todo),
  );

  copy.append(title, meta);
  head.append(copy, badges);
  footer.append(due, actions);
  card.append(head, footer, editors);
  return card;
}

function createTodoBadge(label, tone = "neutral") {
  const badge = document.createElement("span");
  badge.className = "todo-badge";
  badge.dataset.tone = tone;
  badge.textContent = label;
  return badge;
}

function getDueBadge(dueBucket) {
  switch (dueBucket) {
    case "overdue":
      return { label: "已逾期", tone: "danger" };
    case "today":
      return { label: "今天到期", tone: "warning" };
    case "upcoming":
      return { label: "未来安排", tone: "accent" };
    case "unscheduled":
      return { label: "未安排日期", tone: "muted" };
    default:
      return null;
  }
}

function buildDueDescription(todo) {
  if (typeof todo.dueAt === "number") {
    const prefix = todo.completed ? "原定截止" : "截止时间";
    return `${prefix} ${formatDate(todo.dueAt)}`;
  }

  if (todo.completed) {
    return todo.completedAt ? `完成于 ${formatDateTime(todo.completedAt)}` : "任务已完成";
  }

  return "未设置截止时间";
}

function createTodoToggleButton(todo) {
  return createSmallActionButton(
    todo.completed ? "恢复为待完成" : "标记已完成",
    async () => {
      await runTodoAction({
        pendingMessage: todo.completed ? "正在恢复任务状态..." : "正在标记任务完成...",
        successMessage: todo.completed ? "任务已恢复为待完成。" : "任务已标记为已完成。",
        action: () => requestJsonWithMethod(`/api/todos/${encodeURIComponent(todo.id)}`, {
          method: "PATCH",
          token: getCurrentApiToken(),
          body: { completed: !todo.completed },
        }),
      });
    },
  );
}

function createTodoDeleteButton(todo) {
  const button = createSmallActionButton("删除任务", async () => {
    const title = todo.title || "这条任务";
    if (!window.confirm(`确认删除“${title}”吗？此操作不能撤销。`)) {
      return;
    }

    await runTodoAction({
      pendingMessage: "正在删除任务...",
      successMessage: "任务已删除。",
      action: () => requestJsonWithMethod(`/api/todos/${encodeURIComponent(todo.id)}`, {
        method: "DELETE",
        token: getCurrentApiToken(),
      }),
    });
  });
  button.dataset.variant = "danger";
  return button;
}

function createTodoListControl(todo) {
  const field = document.createElement("label");
  field.className = "todo-field";

  const label = document.createElement("span");
  label.textContent = "移动到清单";

  const select = document.createElement("select");
  select.className = "todo-select";
  (dashboardState.overview?.lists || []).forEach((todoList) => {
    select.append(createSelectOption(todoList.id || "", todoList.title || "未命名清单"));
  });
  select.value = todo.listId || "";
  select.addEventListener("change", async () => {
    if (!select.value || select.value === todo.listId) {
      return;
    }

    await runTodoAction({
      pendingMessage: "正在移动任务...",
      successMessage: "任务所属清单已更新。",
      action: () => requestJsonWithMethod(`/api/todos/${encodeURIComponent(todo.id)}`, {
        method: "PATCH",
        token: getCurrentApiToken(),
        body: { listId: select.value },
      }),
    });
  });

  field.append(label, select);
  return field;
}

function createTodoDueControl(todo) {
  const field = document.createElement("div");
  field.className = "todo-field";

  const label = document.createElement("span");
  label.textContent = "截止日期";

  const inputRow = document.createElement("div");
  inputRow.className = "todo-inline-actions";

  const input = document.createElement("input");
  input.type = "date";
  input.className = "todo-date-input";
  input.value = toDateInputValue(todo.dueAt);
  input.addEventListener("change", async () => {
    await updateTodoDueDate(todo, input.value);
  });

  const clearButton = createSmallActionButton("清空日期", async () => {
    if (!input.value && typeof todo.dueAt !== "number") {
      return;
    }
    input.value = "";
    await updateTodoDueDate(todo, "");
  });

  inputRow.append(input, clearButton);
  field.append(label, inputRow);
  return field;
}

async function updateTodoDueDate(todo, dateValue) {
  const dueAt = parseDateInputToTimestamp(dateValue);
  if (dateValue && dueAt === null) {
    setTodoFeedback("日期格式无效，请重新选择。", "error", true);
    return;
  }

  await runTodoAction({
    pendingMessage: dateValue ? "正在更新截止日期..." : "正在清空截止日期...",
    successMessage: dateValue ? "截止日期已更新。" : "截止日期已清空。",
    action: () => requestJsonWithMethod(`/api/todos/${encodeURIComponent(todo.id)}`, {
      method: "PATCH",
      token: getCurrentApiToken(),
      body: { dueAt },
    }),
  });
}

async function handleClearCompleted() {
  const completedCount = getCompletedTodoCountForSelectedList();
  if (completedCount <= 0) {
    return;
  }

  const listTitle = getSelectedListTitle();
  const targetLabel = listTitle ? `清单“${listTitle}”` : "全部清单";
  if (!window.confirm(`确认清空 ${targetLabel} 中的 ${completedCount} 条已完成任务吗？此操作不能撤销。`)) {
    return;
  }

  const body = dashboardState.todoFilterList === "all"
    ? {}
    : { listId: dashboardState.todoFilterList };

  await runTodoAction({
    pendingMessage: "正在清空已完成任务...",
    successMessage: `已清空 ${completedCount} 条已完成任务。`,
    action: () => requestJsonWithMethod("/api/todos/clear-completed", {
      method: "POST",
      token: getCurrentApiToken(),
      body,
    }),
  });
}

async function runTodoAction({ pendingMessage, successMessage, action }) {
  setTodoFeedback(pendingMessage, "info", true);
  try {
    await action();
    await refreshDashboard();
    setTodoFeedback(successMessage, "success", true);
  } catch (error) {
    console.error(error);
    setTodoFeedback(error.message || "任务操作失败。", "error", true);
  }
}

async function runListAction({ pendingMessage, successMessage, action, feedback = setListFeedback }) {
  feedback(pendingMessage, "info", true);
  try {
    await action();
    await refreshDashboard();
    feedback(successMessage, "success", true);
  } catch (error) {
    console.error(error);
    feedback(error.message || "清单操作失败。", "error", true);
  }
}

function focusListInWorkbench(listId, { message = "", skipNavigation = false } = {}) {
  if (!dashboardState.overview) {
    return;
  }

  dashboardState.todoFilterList = listId || "all";
  dashboardState.todoFilterScope = "all";
  renderListManager(dashboardState.overview.lists || []);
  renderTodoFilters(dashboardState.overview.lists || []);
  renderTodoCreateListOptions(dashboardState.overview.lists || [], dashboardState.overview.defaultListId);
  renderWorkbenchSelection();
  if (dashboardState.todoFilterList !== "all") {
    elements.todoCreateList.value = dashboardState.todoFilterList;
  }
  renderFilteredTodos();

  if (!skipNavigation) {
    setActiveView("workbench");
  }

  if (message) {
    setTodoFeedback(message, "success", true);
  }
}

async function handleSaveSelectedListTitle() {
  const selectedList = getSelectedList();
  if (!selectedList) {
    setTodoFeedback("先从左侧选择一个具体清单，再修改名称。", "info", true);
    return;
  }

  const nextTitle = elements.workbenchListTitleInput.value.trim();
  if (!nextTitle) {
    setTodoFeedback("清单名称不能为空。", "error", true);
    return;
  }

  if (nextTitle === (selectedList.title || "")) {
    setTodoFeedback("清单名称没有变化。", "info", true);
    return;
  }

  await runListAction({
    pendingMessage: "正在保存清单名称...",
    successMessage: "清单名称已更新。",
    feedback: setTodoFeedback,
    action: () => requestJsonWithMethod(`/api/lists/${encodeURIComponent(selectedList.id)}`, {
      method: "PATCH",
      token: getCurrentApiToken(),
      body: { title: nextTitle },
    }),
  });
}

async function handleDeleteSelectedList() {
  const selectedList = getSelectedList();
  if (!selectedList) {
    setTodoFeedback("当前是全部任务视图，不能直接删除。请选择一个清单后再操作。", "info", true);
    return;
  }

  if ((dashboardState.overview?.lists || []).length <= 1) {
    setTodoFeedback("至少保留一个清单。", "error", true);
    return;
  }

  if (!window.confirm(`确认删除清单“${selectedList.title || "未命名清单"}”吗？该清单下的任务也会一起删除。`)) {
    return;
  }

  await runListAction({
    pendingMessage: "正在删除清单...",
    successMessage: "清单已删除。",
    feedback: setTodoFeedback,
    action: () => requestJsonWithMethod(`/api/lists/${encodeURIComponent(selectedList.id)}`, {
      method: "DELETE",
      token: getCurrentApiToken(),
    }),
  });
}

function buildWorkbenchTodoItems(items, lists) {
  const listTitleById = new Map((Array.isArray(lists) ? lists : []).map((todoList) => [todoList.id, todoList.title || ""]));
  return (Array.isArray(items) ? items : [])
    .map((todo) => ({
      ...todo,
      listTitle: listTitleById.get(todo.listId) || todo.listTitle || "",
      dueBucket: classifyTodoDueBucket(todo),
    }))
    .sort((left, right) => {
      const rightTime = right.updatedAt || right.createdAt || 0;
      const leftTime = left.updatedAt || left.createdAt || 0;
      return rightTime - leftTime;
    });
}

function classifyTodoDueBucket(todo) {
  if (todo.completed) {
    return "completed";
  }

  if (typeof todo.dueAt !== "number") {
    return "unscheduled";
  }

  const dueKey = toDateInputValue(todo.dueAt);
  const todayKey = toDateInputValue(Date.now());
  if (dueKey < todayKey) {
    return "overdue";
  }
  if (dueKey === todayKey) {
    return "today";
  }
  return "upcoming";
}

async function applyCandidateAsPublicEndpoint(candidate) {
  const serverUrl = String(candidate?.serverUrl || "").trim();
  const wsUrl = String(candidate?.wsUrl || "").trim();
  if (!serverUrl || !wsUrl) {
    setShareFeedback("候选地址不完整，无法保存为公开地址。", "error", true);
    return;
  }

  setShareFeedback("正在保存候选地址到服务配置...", "info", true);
  try {
    const updated = await requestJsonWithMethod("/api/admin/config", {
      method: "POST",
      token: getCurrentApiToken(),
      body: buildCurrentAdminConfigPayload({
        publicBaseUrl: serverUrl,
        publicWsBaseUrl: wsUrl,
      }),
    });
    renderAdminConfig(updated);
    await refreshDashboard();
    setShareFeedback("候选地址已保存为公开访问地址。", "success", true);
  } catch (error) {
    console.error(error);
    setShareFeedback(error.message || "保存公开地址失败。", "error", true);
  }
}

function buildCurrentAdminConfigPayload(overrides = {}) {
  return {
    publicBaseUrl: elements.configPublicBaseUrl.value.trim(),
    publicWsBaseUrl: elements.configPublicWsBaseUrl.value.trim(),
    appWebUrl: elements.configAppWebUrl.value.trim(),
    appDeepLinkBase: elements.configAppDeepLinkBase.value.trim(),
    httpLogMode: elements.configHttpLogMode.value || "errors",
    ...overrides,
  };
}

function formatCandidateKind(kind) {
  switch (kind) {
    case "tailscale":
      return "Tailscale";
    case "lan":
      return "局域网";
    case "configured":
      return "手动配置";
    case "request":
      return "当前访问源";
    case "public":
      return "公网";
    case "fallback":
      return "回退地址";
    default:
      return kind || "未知类型";
  }
}

function formatCandidateSource(source) {
  switch (source) {
    case "configured-public-base-url":
      return "配置文件";
    case "request-host":
      return "当前请求";
    case "tailscale":
      return "Tailscale 探测";
    case "bind":
      return "本机绑定";
    case "fallback":
      return "默认回退";
    default:
      return source || "未知来源";
  }
}

function getCurrentApiToken() {
  return elements.tokenInput.value.trim() || dashboardState.token || "";
}

function buildShareCardConfig({ title, copy, value, actions }) {
  if (!value) {
    return null;
  }

  return {
    title,
    copy,
    value,
    actions: actions.filter(Boolean),
  };
}

function createShareCard(config) {
  const card = document.createElement("article");
  card.className = "share-card";

  const header = document.createElement("div");
  header.className = "share-card-header";

  const content = document.createElement("div");

  const title = document.createElement("p");
  title.className = "share-card-title";
  title.textContent = config.title;

  const copy = document.createElement("p");
  copy.className = "share-card-copy";
  copy.textContent = config.copy;

  content.append(title, copy);
  header.append(content);

  const value = document.createElement("pre");
  value.className = "share-card-value";
  value.textContent = config.value;

  const actions = document.createElement("div");
  actions.className = "share-card-actions";
  config.actions.forEach((action) => actions.append(action));

  card.append(header, value, actions);
  return card;
}

function createActionButton(label, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "secondary-button";
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function createSmallActionButton(label, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn btn-ghost btn-xs";
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function createCopyAction(label, value) {
  if (!value) {
    return null;
  }

  return createActionButton(label, () => {
    void copyText(value, `${label}已复制。`);
  });
}

function createOpenAction(label, value) {
  if (!value) {
    return null;
  }

  return createActionButton(label, () => {
    openExternalLink(value, label, setShareFeedback);
  });
}

function openExternalLink(value, label, feedbackSetter = setShareFeedback) {
  if (!String(value || "").trim()) {
    feedbackSetter("当前没有可打开地址。", "error", true);
    return false;
  }

  window.open(value, "_blank", "noopener,noreferrer");
  feedbackSetter(`已尝试打开 ${label}。`, "success", true);
  return true;
}

async function copyText(value, successMessage, feedbackSetter = setShareFeedback) {
  try {
    if (!String(value || "").trim()) {
      feedbackSetter("当前没有可复制内容。", "error", true);
      return false;
    }

    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
    } else {
      fallbackCopyText(value);
    }
    feedbackSetter(successMessage, "success", true);
    return true;
  } catch (error) {
    console.error(error);
    feedbackSetter("复制失败，请检查浏览器剪贴板权限。", "error", true);
    return false;
  }
}

function downloadObjectUrl(objectUrl, filename) {
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
}

function fallbackCopyText(value) {
  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "readonly");
  textarea.style.position = "fixed";
  textarea.style.top = "-999px";
  document.body.append(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

async function requestJson(path, token = "") {
  return requestJsonWithMethod(path, { method: "GET", token });
}

async function requestJsonWithMethod(path, { method = "GET", token = "", body } = {}) {
  const headers = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json; charset=utf-8";
  }

  const response = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = typeof payload.error === "string" ? payload.error : `request failed: ${response.status}`;
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

async function requestText(path, token = "") {
  const response = await fetch(path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    const error = new Error(`request failed: ${response.status}`);
    error.status = response.status;
    throw error;
  }

  return response.text();
}

function saveToken(token) {
  const normalizedToken = token.trim();
  const sessionStorage = getSessionStorage();
  if (sessionStorage) {
    if (normalizedToken) {
      sessionStorage.setItem(TOKEN_STORAGE_KEY, normalizedToken);
    } else {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  }

  memoryToken = normalizedToken;
}

function loadToken() {
  const sessionStorage = getSessionStorage();
  if (sessionStorage) {
    const sessionToken = sessionStorage.getItem(TOKEN_STORAGE_KEY);
    if (typeof sessionToken === "string" && sessionToken.trim()) {
      memoryToken = sessionToken.trim();
      return memoryToken;
    }
  }

  return memoryToken;
}

function readLegacyQueryToken() {
  const queryToken = new URLSearchParams(location.search).get("token");
  return typeof queryToken === "string" ? queryToken.trim() : "";
}

function clearLegacyQueryToken() {
  if (typeof history.replaceState !== "function") {
    return;
  }

  const url = new URL(location.href);
  if (!url.searchParams.has("token")) {
    return;
  }

  url.searchParams.delete("token");
  const nextSearch = url.searchParams.toString();
  history.replaceState({}, "", `${url.pathname}${nextSearch ? `?${nextSearch}` : ""}${url.hash}`);
}

function getSessionStorage() {
  if (typeof globalThis.sessionStorage?.getItem !== "function") {
    return null;
  }
  return globalThis.sessionStorage;
}

function getLocalStorage() {
  if (typeof globalThis.localStorage?.getItem !== "function") {
    return null;
  }
  return globalThis.localStorage;
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

function formatDate(timestamp) {
  if (typeof timestamp !== "number") {
    return "-";
  }

  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    weekday: "short",
  }).format(timestamp);
}

function toDateInputValue(timestamp) {
  if (typeof timestamp !== "number") {
    return "";
  }

  const target = new Date(timestamp);
  return [
    target.getFullYear(),
    `${target.getMonth() + 1}`.padStart(2, "0"),
    `${target.getDate()}`.padStart(2, "0"),
  ].join("-");
}

function parseDateInputToTimestamp(dateValue) {
  const trimmed = String(dateValue || "").trim();
  if (!trimmed) {
    return null;
  }

  const [year, month, day] = trimmed.split("-").map(Number);
  if (!year || !month || !day) {
    return null;
  }

  return new Date(year, month - 1, day, 12, 0, 0, 0).getTime();
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
