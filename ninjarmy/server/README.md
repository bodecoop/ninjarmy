# Server — Web UI & API

Built with [FastAPI](https://fastapi.tiangolo.com/). Serves a web-based UI and exposes a REST + WebSocket API for controlling agents remotely.

Start it with:

```bash
ninjarmy server          # default port 7337
ninjarmy server --port 8080
```

## Key Files

| File | Responsibility |
|------|----------------|
| `app.py` | FastAPI app, all routes, WebSocket handler, lifespan management |

The static web UI lives in `ninjarmy/static/` (HTML/CSS/JS served from `/`).

## Endpoints

### REST

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve web UI |
| `GET` | `/api/session` | Current session name and active status |
| `GET` | `/api/agents` | List agents (id, name, role, task, status) |
| `POST` | `/api/input` | Send message to manager |
| `GET` | `/api/files` | Recursive file tree of workspace |
| `GET` | `/api/files/{path}` | Read a file |
| `PUT` | `/api/files/{path}` | Write a file |
| `POST` | `/api/hire` | Hire a new agent |
| `POST` | `/api/stop/{name}` | Stop agent(s) — `all` is valid |
| `POST` | `/api/restart/{name}` | Restart agent(s) |
| `POST` | `/api/agent/{name}` | Send message to a specific agent |

### WebSocket

**`/ws`** — Real-time event stream.

On connect, the server immediately sends:
```json
{ "type": "init", "agents": [...] }
```
This lets the client render existing agent panels before the first event arrives. After that, all `EventBus` events are forwarded to the client as JSON.

## Lifespan

On startup, the server creates asyncio tasks for the manager and all registered agents, then starts Uvicorn. On shutdown, all tasks are cancelled. Agents are hydrated from the database on `ninjarmy server` boot.

## Non-obvious Behaviors

- **Path safety:** All file read/write endpoints validate the requested path is inside the workspace root. Requests outside the root are rejected.
- **File tree depth limit:** `/api/files` skips directories deeper than 8 levels and skips `.git`, `node_modules`, `__pycache__`, `.ninjarmy`, and `.egg-info` to avoid traversing dependency trees.
- **WebSocket init payload:** The initial `{"type": "init", ...}` message is separate from the event stream — the client must handle both.

## Adding a New Endpoint

1. Add the route to `app.py`
2. If it triggers state changes, publish an event via `EventBus.publish({...})` so connected WebSocket clients can react
3. Keep path validation: use `_check_path()` from `core/tools.py` for any file operations
