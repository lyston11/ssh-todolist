# Focus List

一个基于 Tailscale 局域网同步的 todolist。

项目协作规则见 [CLAUDE.md](./CLAUDE.md)。

## 版本

`v0.01` 是项目的第一个可运行版本，目标是验证一套最小但完整的跨设备同步方案：

- 以一台设备作为同步节点
- 通过 Tailscale 在同一虚拟局域网内访问
- 支持 Web、Android、macOS 通过浏览器共享同一个待办列表
- 后端提供 REST API + WebSocket 实时同步
- 数据使用 SQLite 本地持久化

## 开发环境

项目开发环境固定为 `conda` 的 `ssh-todolist` 环境，不使用 `base`。

推荐命令：

```bash
conda activate ssh-todolist
```

如果你不想切换当前 shell，也可以直接这样运行：

```bash
conda run -n ssh-todolist python server.py --host 0.0.0.0 --port 8000
```

## 当前架构

- 一台设备运行 `server.py`，作为同步节点
- 服务端使用 Python + SQLite 持久化任务
- Web 前端由同一个服务直接提供
- WebSocket 服务负责把任务变更实时推送到其他设备
- Android、Mac、其他 Web 端通过同一个 Tailscale 地址访问
- 前端保留 REST API 写操作，列表同步通过 WebSocket 完成

## 代码结构

- `server.py`: 启动入口，只负责组装服务
- `backend/store.py`: SQLite 数据存储
- `backend/http_server.py`: HTTP API 和静态文件服务
- `backend/realtime.py`: WebSocket 连接和广播
- `app.js`: 前端状态和同步逻辑

## 功能

- 添加任务
- 编辑任务
- 标记完成 / 取消完成
- 删除任务
- 按状态筛选
- 清除已完成任务
- SQLite 持久化
- 通过局域网 / Tailscale 实时同步

## 使用方式

1. 在你想作为同步节点的设备上启动服务：

```bash
conda run -n ssh-todolist python server.py --host 0.0.0.0 --port 8000
```

默认会同时启动：

- HTTP: `8000`
- WebSocket: `8001`

2. 查询这台设备的 Tailscale IP：

```bash
tailscale ip -4
```

3. 在 Android、Mac 或其他浏览器里访问：

```text
http://<这台设备的tailscale-ip>:8000
```

## 本地开发

如果你只想在当前电脑调试，启动服务后访问：

```text
http://127.0.0.1:8000
```
