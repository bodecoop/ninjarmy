import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from ninjarmy.core.event_bus import EventBus
from ninjarmy.core.manager import ManagerAgent
from ninjarmy.core.registry import AgentRegistry
from ninjarmy.core import model

STATIC = Path(__file__).parent / "static"

_SKIP_DIRS = {".git", "__pycache__", ".ninjarmy", "node_modules", ".venv", "venv",
              ".mypy_cache", ".pytest_cache", "dist", "build"}
_SKIP_SUFFIXES = (".egg-info", ".egg-link")


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = ManagerAgent.get()
    asyncio.create_task(manager.run())
    for agent in AgentRegistry.all():
        asyncio.create_task(agent.run())
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


@app.get("/")
def root():
    return HTMLResponse((STATIC / "index.html").read_text())


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    bus = EventBus.get()
    queue = bus.subscribe()
    # Send the current agent list on connect so the UI can render existing panels
    agents = [
        {"name": a.name, "role": a.role, "task": a.task, "status": a.status}
        for a in AgentRegistry.all()
    ]
    await websocket.send_json({"type": "init", "agents": agents})
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        bus.unsubscribe(queue)


@app.get("/api/session")
def get_session():
    session = model.load_session()
    return {"name": session["name"] if session else "", "active": session is not None}


@app.get("/api/agents")
def get_agents():
    return [
        {"id": a.id, "name": a.name, "role": a.role, "task": a.task, "status": a.status}
        for a in AgentRegistry.all()
    ]


@app.post("/api/input")
async def send_input(body: dict):
    msg = body.get("message", "").strip()
    if not msg:
        return {"ok": False, "error": "empty message"}
    ManagerAgent.get().send_message(msg)
    return {"ok": True}


@app.get("/api/files")
def get_file_tree():
    root = Path(ManagerAgent.get().root).resolve()

    def walk(p: Path, depth: int = 0) -> list:
        if depth > 8:
            return []
        entries = []
        try:
            children = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            return []
        for child in children:
            if child.name in _SKIP_DIRS or child.name.startswith("."):
                continue
            if any(child.name.endswith(s) for s in _SKIP_SUFFIXES):
                continue
            rel = str(child.relative_to(root))
            if child.is_dir():
                entries.append({
                    "name": child.name,
                    "type": "dir",
                    "path": rel,
                    "children": walk(child, depth + 1),
                })
            else:
                entries.append({"name": child.name, "type": "file", "path": rel})
        return entries

    return walk(root)


@app.get("/api/files/{path:path}")
def read_file(path: str):
    root = Path(ManagerAgent.get().root).resolve()
    full = (root / path).resolve()
    if not str(full).startswith(str(root)):
        return {"error": "path outside workspace"}
    if not full.exists():
        return {"error": "not found"}
    if full.is_dir():
        return {"error": "path is a directory"}
    try:
        content = full.read_text(errors="replace")
    except Exception as e:
        return {"error": str(e)}
    return {"content": content, "path": path}


@app.put("/api/files/{path:path}")
def write_file(path: str, body: dict):
    root = Path(ManagerAgent.get().root).resolve()
    full = (root / path).resolve()
    if not str(full).startswith(str(root)):
        return {"error": "path outside workspace"}
    try:
        full.write_text(body.get("content", ""))
    except Exception as e:
        return {"error": str(e)}
    return {"ok": True}


@app.post("/api/hire")
async def hire_agent(body: dict):
    name = body.get("name", "").strip()
    role = body.get("role", "custom").strip()
    task = body.get("task", "").strip()
    if not name:
        return {"ok": False, "error": "name is required"}
    try:
        agent = ManagerAgent.get().hire_agent(name=name, task=task, role=role)
        asyncio.create_task(agent.run())
        return {"ok": True, "name": name}
    except ValueError as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/stop/{name}")
def stop_agent(name: str):
    agents = AgentRegistry.all()
    if name == "all":
        for a in agents:
            a.stop()
        EventBus.get().publish({"type": "agents_stopped", "name": "all"})
        return {"ok": True}
    agent = next((a for a in agents if a.name == name), None)
    if not agent:
        return {"ok": False, "error": f"No agent named '{name}'"}
    agent.stop()
    EventBus.get().publish({"type": "agent_status", "name": name, "status": "stopped"})
    return {"ok": True}


@app.post("/api/restart/{name}")
def restart_agent(name: str):
    agents = AgentRegistry.all()
    if name == "all":
        for a in agents:
            a.start()
        EventBus.get().publish({"type": "agents_restarted", "name": "all"})
        return {"ok": True}
    agent = next((a for a in agents if a.name == name), None)
    if not agent:
        return {"ok": False, "error": f"No agent named '{name}'"}
    agent.start()
    EventBus.get().publish({"type": "agent_status", "name": name, "status": "running"})
    return {"ok": True}


@app.post("/api/agent/{name}")
async def message_agent(name: str, body: dict):
    msg = body.get("message", "").strip()
    if not msg:
        return {"ok": False, "error": "empty message"}
    agent = next((a for a in AgentRegistry.all() if a.name == name), None)
    if not agent:
        return {"ok": False, "error": f"No agent named '{name}'"}
    agent.prompt(msg, source="user")
    return {"ok": True}
