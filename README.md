# ssh-todolist-services

`ssh-todolist-services` 是 Focus List 的独立同步服务工程。

## 职责

- 提供 Todo / List 的 REST API
- 提供 WebSocket 实时快照广播
- 使用 SQLite 做本地持久化
- 作为 Tailscale 局域网中的同步节点
- 导出可供独立 app 使用的连接配置

## 目录

- `server.py`: 服务启动入口
- `backend/store.py`: SQLite 存储
- `backend/service.py`: 业务逻辑和校验
- `backend/http_server.py`: HTTP API、CORS、可选静态目录挂载
- `backend/realtime.py`: WebSocket 广播
- `backend/network.py`: Tailscale / 局域网地址发现
- `backend/connection.py`: 客户端连接配置与导入链接导出
- `tests/test_store.py`: 服务端回归测试
- `data/`: 默认 SQLite 数据目录

## 安装方式

`ssh-todolist-services` 不再要求只能用 conda。

现在至少支持这几种安装路径：

1. `pip` 本地安装
2. `pipx` 作为命令行服务安装
3. 从 `wheel` / `sdist` 安装
4. `Docker` 单容器运行
5. `docker compose` 部署
6. 一键脚本安装与启动

## 一键脚本

最省事的方式：

```bash
cd ssh-todolist-services
./install.sh
./run.sh --token your-shared-token
```

也可以显式指定安装方式：

```bash
./install.sh --method venv
./install.sh --method pipx
./install.sh --method docker
```

## pip 安装

```bash
cd ssh-todolist-services
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install --no-build-isolation .
ssh-todolist-service --host 0.0.0.0 --port 8000 --token your-shared-token
```

## pipx 安装

如果你更希望把它当成一个独立 CLI：

```bash
pipx install . --pip-args=--no-build-isolation
ssh-todolist-service --host 0.0.0.0 --port 8000 --token your-shared-token
```

## wheel / sdist 安装

先打包：

```bash
cd ssh-todolist-services
python -m pip install --upgrade build
python -m build --no-isolation
```

产物会在 `dist/` 下，例如：

- `ssh_todolist_services-0.10.0-py3-none-any.whl`
- `ssh_todolist_services-0.10.0.tar.gz`

别人可以直接安装：

```bash
pip install ssh_todolist_services-0.10.0-py3-none-any.whl
```

## Docker 安装

```bash
cd ssh-todolist-services
docker build -t ssh-todolist-services:latest .
docker run --rm -p 8000:8000 -p 8001:8001 \
  -e SSH_TODOLIST_TOKEN=your-shared-token \
  -v "$(pwd)/data:/app/data" \
  ssh-todolist-services:latest
```

## docker compose 安装

仓库已经带了 [compose.yaml](/Users/lyston/PycharmProjects/ssh-todolist/ssh-todolist-services/compose.yaml)：

```bash
cd ssh-todolist-services
docker compose up -d --build
```

## 源码运行

如果你自己开发，依然可以继续用源码直接启动。

```bash
cd ssh-todolist-services
conda run -n ssh-todolist python server.py --host 0.0.0.0 --port 8000 --token your-shared-token
```

默认端口：

- HTTP: `8000`
- WebSocket: `8001`

## 可选参数

```bash
conda run -n ssh-todolist python server.py \
  --host 0.0.0.0 \
  --port 8000 \
  --ws-port 8001 \
  --db ./data/todos.db \
  --token your-shared-token
```

如果你准备通过域名或反向代理暴露给客户端，建议显式告诉服务端对外地址：

```bash
conda run -n ssh-todolist python server.py \
  --host 0.0.0.0 \
  --port 8000 \
  --ws-port 8001 \
  --token your-shared-token \
  --public-base-url https://todo.example.com \
  --public-ws-base-url wss://todo.example.com \
  --app-web-url https://todo-app.example.com \
  --app-deep-link-base com.lyston11.sshtodolist://connect
```

也可以通过环境变量提供 token：

```bash
export SSH_TODOLIST_TOKEN=your-shared-token
conda run -n ssh-todolist python server.py --host 0.0.0.0 --port 8000
```

如果你想临时把独立 app 静态目录也挂到这个服务上，可以额外传：

```bash
conda run -n ssh-todolist python server.py \
  --host 0.0.0.0 \
  --port 8000 \
  --web-root ../ssh-todolist-app
```

## 独立部署说明

- 服务端现在默认按独立 API / WebSocket 工程运行
- 已启用 CORS，独立 Web App 和 Android App 可直接跨域访问
- 当设置 `--token` 或 `SSH_TODOLIST_TOKEN` 时，REST 和 WebSocket 都会校验 Bearer token
- 推荐让服务端和 app 分别部署，通过显式节点地址连接
- 命令行入口现在统一为 `ssh-todolist-service`
- Docker 镜像默认数据目录为 `/app/data`
- wheel / sdist 适合发给别人离线安装

## GitHub 自动打包

仓库已补 [services-release.yml](/Users/lyston/PycharmProjects/ssh-todolist/ssh-todolist-services/.github/workflows/services-release.yml)：

- 推送到 `main` 时会自动构建并上传 `dist/*` artifacts
- 推送 `v*` tag 时会自动创建 GitHub Release
- Release 会附带：
  - `wheel`
  - `sdist`

## 连接配置导出

参考 `fast-note-sync-service` 的做法，`ssh-todolist-services` 现在由服务端负责产出“客户端该怎么连”的信息。

启动服务后，终端会打印一份建议的 app 配置 JSON，优先给出：

1. `--public-base-url` / `--public-ws-base-url` 指定的地址
2. 当前请求头里的 `Host` / `X-Forwarded-*`
3. 本机 Tailscale IPv4
4. 本机局域网 IPv4
5. `127.0.0.1`

同时新增公开接口：

- `GET /api/connect-config`: 返回建议连接配置，不包含真实 token
- `GET /api/connect-link`: 返回带 token 的导入链接，要求已通过服务端鉴权
- `GET /api/meta`: 返回运行元信息，并包含候选连接地址

典型返回示例：

```json
{
  "serverUrl": "http://100.x.x.x:8000",
  "token": "",
  "authRequired": true,
  "wsUrl": "ws://100.x.x.x:8001/ws",
  "wsPort": 8001,
  "wsPath": "/ws",
  "candidates": [
    {
      "kind": "tailscale",
      "source": "tailscale",
      "host": "100.x.x.x",
      "serverUrl": "http://100.x.x.x:8000",
      "wsUrl": "ws://100.x.x.x:8001/ws"
    }
  ]
}
```

## Tailscale 使用方式

最简单的接入方式：

1. 在服务端设备上启动 Tailscale
2. 运行服务：

```bash
conda run -n ssh-todolist python server.py --host 0.0.0.0 --port 8000 --token your-shared-token
```

3. 从终端打印的建议配置里取 `100.x.x.x`
4. 在 `ssh-todolist-app` 中填入：
   - 节点地址：`http://100.x.x.x:8000`
   - token：`your-shared-token`

也可以先手动访问：

```text
http://100.x.x.x:8000/api/connect-config
```

确认服务端当前推荐的连接地址。

## 设计说明

- 服务端和 app 继续保持完全分离，连接描述通过显式 JSON 契约传递
- Tailscale 地址发现、连接配置组装、HTTP 暴露分别位于独立模块，避免把网络细节塞进业务层
- 公开接口不会泄露真实 token；只有服务端本地终端输出会带上 token，方便运维复制

## 导入链接与分享

服务端现在也会生成适合手机导入的 `config64` 链接。

启动服务后，终端会额外打印：

- `config64`: app 导入配置的 URL-safe Base64 文本
- `deepLinkUrl`: Android App 直接导入链接，例如 `com.lyston11.sshtodolist://connect?config64=...`
- `webImportUrl`: Web App 导入链接，例如 `https://todo-app.example.com?config64=...`
- `qrValue`: 可直接拿去做二维码编码的文本
- `qrSvgUrl`: 直接返回 SVG 二维码的接口地址
- `shortText`: 适合复制到聊天工具或备忘录的短分享文案

如果你要从接口获取这些内容：

```text
GET /api/connect-link
Authorization: Bearer your-shared-token
```

如果你想直接取二维码 SVG：

```text
GET /api/connect-link/qr.svg?token=your-shared-token
```

如果你希望链接直接打开网页版 app，请启动服务时补 `--app-web-url`。

如果你希望链接直接唤起 Android App，请保留或自定义 `--app-deep-link-base`。

## 校验

```bash
cd ssh-todolist-services
conda run -n ssh-todolist python -m py_compile server.py backend/auth.py backend/network.py backend/connection.py backend/store.py backend/service.py backend/realtime.py backend/http_server.py
conda run -n ssh-todolist python -m unittest tests.test_auth tests.test_connection tests.test_store
```
