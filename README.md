# ssh-todolist-services

`ssh-todolist-services` 是 Focus List 的独立同步服务工程。

## 职责

- 提供 Todo / List 的 REST API
- 提供 WebSocket 实时快照广播
- 使用 SQLite 做本地持久化
- 作为 Tailscale 局域网中的同步节点

## 目录

- `server.py`: 服务启动入口
- `backend/store.py`: SQLite 存储
- `backend/service.py`: 业务逻辑和校验
- `backend/http_server.py`: HTTP API、CORS、可选静态目录挂载
- `backend/realtime.py`: WebSocket 广播
- `tests/test_store.py`: 服务端回归测试
- `data/`: 默认 SQLite 数据目录

## 运行

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

## 校验

```bash
cd ssh-todolist-services
conda run -n ssh-todolist python -m py_compile server.py backend/auth.py backend/store.py backend/service.py backend/realtime.py backend/http_server.py
conda run -n ssh-todolist python -m unittest tests.test_store tests.test_auth
```
