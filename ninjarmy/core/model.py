import sqlite3
from datetime import datetime, UTC
from pathlib import Path

from ninjarmy.agents.agent_schema import AgentSpec

STATE_PATH: Path = None
DB_PATH: Path = None
conn: sqlite3.Connection = None


def init(root: str) -> None:
    global STATE_PATH, DB_PATH, conn
    STATE_PATH = Path(root) / ".ninjarmy"
    DB_PATH = STATE_PATH / "state.db"
    STATE_PATH.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            task TEXT,
            model TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            active INTEGER NOT NULL DEFAULT 0,
            started_at TEXT,
            name TEXT,
            context TEXT
        )
    """)
    conn.commit()


def start_session(name: str = ""):
    context_path = STATE_PATH / f"{name}_project_context.md"
    context = context_path.read_text(encoding="utf-8") if context_path.exists() else None
    conn.execute(
        "INSERT OR REPLACE INTO session (id, active, started_at, name, context) VALUES (1, 1, ?, ?, ?)",
        (datetime.now(UTC).isoformat(), name, context)
    )
    conn.commit()
    init_task_board()

def load_session() -> dict | None:
    row = conn.execute("SELECT name FROM session WHERE id = 1 AND active = 1").fetchone()
    return {"name": row[0]} if row else None

def end_session():
    conn.execute("UPDATE session SET active = 0 WHERE id = 1")
    conn.execute("DELETE FROM agents")
    conn.commit()

def is_session_active() -> bool:
    row = conn.execute("SELECT active FROM session WHERE id = 1").fetchone()
    return bool(row and row[0])

def save_agent(spec: AgentSpec):
    try:
        conn.execute(
            "INSERT INTO agents (id, name, role, task, model) VALUES (?, ?, ?, ?, ?)",
            (spec.id, spec.name, spec.role, spec.task, spec.model)
        )
        conn.commit()
    except sqlite3.Error as e:
        raise RuntimeError(f"Failed to save agent '{spec.name}' to database: {e}") from e

def load_agents():
    rows = conn.execute("SELECT * FROM agents").fetchall()
    return rows

def delete_agent(id: int):
    conn.execute("DELETE FROM agents WHERE id = ?", (id,))
    conn.commit()


# Only these keys are accepted by the API when sending messages back.
# The SDK adds extra fields like `parsed_output`, `citations`, etc. on
# returned objects that are NOT valid as inputs — strip them here.
_BLOCK_ALLOWED_KEYS = {
    "text":        {"type", "text"},
    "tool_use":    {"type", "id", "name", "input"},
    "tool_result": {"type", "tool_use_id", "content", "is_error"},
}


def _clean_block(block: dict) -> dict:
    """Remove SDK-only fields that the API rejects when echoed back."""
    allowed = _BLOCK_ALLOWED_KEYS.get(block.get("type"))
    if allowed is None:
        return block
    return {k: v for k, v in block.items() if k in allowed}


def _serialize_message(msg: dict) -> dict:
    """Convert a history message to a JSON-safe dict.
    Assistant messages from tool_use turns have list content containing
    Anthropic SDK objects (ToolUseBlock, TextBlock) that must be converted
    to plain dicts before serialization."""
    content = msg.get("content")
    if not isinstance(content, list):
        return msg
    serialized = []
    for block in content:
        if isinstance(block, dict):
            serialized.append(_clean_block(block))
        elif hasattr(block, "model_dump"):
            serialized.append(_clean_block(block.model_dump()))
        else:
            serialized.append({"type": "text", "text": str(block)})
    return {**msg, "content": serialized}


def save_history(name: str, history: list) -> None:
    import json
    serializable = [_serialize_message(m) for m in history[-20:]]
    path = STATE_PATH / f"{name}_history.json"
    path.write_text(json.dumps(serializable), encoding="utf-8")


def load_history(name: str) -> list | None:
    import json
    path = STATE_PATH / f"{name}_history.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def init_task_board() -> None:
    path = STATE_PATH / "task_board.md"
    if not path.exists():
        path.write_text("# Task Board\n\n", encoding="utf-8")
