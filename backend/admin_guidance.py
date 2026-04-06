from pathlib import Path
from urllib.parse import urlsplit


PROJECT_DIR_NAME = "ssh-todolist-services"
TOKEN_PLACEHOLDER = "your-shared-token"
DEFAULT_SERVER_URL = "http://100.x.x.x:8000"
DEFAULT_WS_URL = "ws://100.x.x.x:8001"


def build_admin_runtime_payload(
    *,
    connect_config: dict,
    auth_required: bool,
    db_path: Path,
    ws_port: int,
    admin_entry_path: str = "/admin",
    admin_alias_path: str | None = None,
) -> dict:
    server_url = str(connect_config.get("serverUrl") or "")
    ws_url = str(connect_config.get("wsUrl") or "")

    return {
        "projectDir": PROJECT_DIR_NAME,
        "serverUrl": server_url,
        "wsUrl": ws_url,
        "adminUrl": _join_url(server_url, admin_entry_path),
        "adminAliasUrl": _join_url(server_url, admin_alias_path) if admin_alias_path else "",
        "healthUrl": _join_url(server_url, "/api/health"),
        "snapshotUrl": _join_url(server_url, "/api/snapshot"),
        "connectConfigUrl": _join_url(server_url, "/api/connect-config"),
        "connectLinkUrl": _join_url(server_url, "/api/connect-link"),
        "httpPort": _extract_port(server_url),
        "wsPort": ws_port,
        "authRequired": auth_required,
        "authSummary": (
            "REST / WebSocket 都需要 Bearer Token。"
            if auth_required
            else "当前服务未启用 token，局域网内可直接访问。"
        ),
        "databasePath": str(db_path),
        "databaseExists": db_path.exists(),
        "databaseSizeBytes": _safe_file_size(db_path),
    }


def build_admin_install_payload(
    *,
    connect_config: dict,
    auth_required: bool,
) -> dict:
    server_url = str(connect_config.get("serverUrl") or DEFAULT_SERVER_URL)
    ws_url = str(connect_config.get("wsUrl") or DEFAULT_WS_URL)
    token_arg = f" --token {TOKEN_PLACEHOLDER}" if auth_required else ""
    token_env_lines = [f"export SSH_TODOLIST_TOKEN={TOKEN_PLACEHOLDER}"] if auth_required else []
    public_env_lines = [
        f"export SSH_TODOLIST_PUBLIC_BASE_URL={server_url}",
        f"export SSH_TODOLIST_PUBLIC_WS_BASE_URL={ws_url}",
    ]

    return {
        "methods": [
            {
                "id": "script",
                "title": "一键脚本",
                "summary": "适合直接把当前节点装成一个长期运行的同步服务。",
                "recommended": True,
                "command": "\n".join(
                    [
                        f"cd {PROJECT_DIR_NAME}",
                        "./install.sh",
                        f"./run.sh{token_arg}",
                    ]
                ),
                "notes": [
                    "脚本会按仓库内 install.sh / run.sh 的默认约定安装并启动服务。",
                    "适合单机、自建 NAS 或 Tailscale 节点直接部署。",
                ],
            },
            {
                "id": "source",
                "title": "源码运行",
                "summary": "适合开发调试，继续使用 ssh-todolist conda 环境。",
                "recommended": False,
                "command": "\n".join(
                    [
                        f"cd {PROJECT_DIR_NAME}",
                        "conda run -n ssh-todolist python server.py --host 0.0.0.0 --port 8000 --ws-port 8001"
                        f"{token_arg}",
                    ]
                ),
                "notes": [
                    "最适合本地开发、联调 Android / Web 客户端，便于直接改代码后重启验证。",
                ],
            },
            {
                "id": "docker",
                "title": "Docker 单容器",
                "summary": "适合快速试跑或发给别人按容器方式落地。",
                "recommended": False,
                "command": "\n".join(
                    [
                        f"cd {PROJECT_DIR_NAME}",
                        "docker build -t ssh-todolist-services:latest .",
                        "docker run --rm -p 8000:8000 -p 8001:8001 \\",
                        *[f"  -e {line.removeprefix('export ')} \\" for line in token_env_lines],
                        *[f"  -e {line.removeprefix('export ')} \\" for line in public_env_lines],
                        '  -v "$(pwd)/data:/app/data" \\',
                        "  ssh-todolist-services:latest",
                    ]
                ),
                "notes": [
                    "如果你希望 Android / Web 客户端稳定连到服务端，建议显式传入对外 HTTP / WS 地址。",
                ],
            },
            {
                "id": "compose",
                "title": "Docker Compose",
                "summary": "适合长期运行，仓库已经自带 compose.yaml。",
                "recommended": True,
                "command": "\n".join(
                    [
                        f"cd {PROJECT_DIR_NAME}",
                        *(token_env_lines + public_env_lines),
                        "docker compose up -d --build",
                    ]
                ),
                "notes": [
                    "当前 compose.yaml 会映射 8000 / 8001 并挂载 ./data 到容器内 /app/data。",
                    "长期运行建议优先用 compose，而不是手写 docker run。",
                ],
            },
        ]
    }


def _join_url(base_url: str, path: str) -> str:
    normalized_base_url = str(base_url or "").strip().rstrip("/")
    if not normalized_base_url:
        return ""
    return f"{normalized_base_url}{path}"


def _extract_port(url: str) -> int | None:
    if not url:
        return None

    try:
        parsed = urlsplit(url)
    except ValueError:
        return None

    if parsed.port is not None:
        return parsed.port
    if parsed.scheme == "https":
        return 443
    if parsed.scheme == "http":
        return 80
    return None


def _safe_file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0
