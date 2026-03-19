import sqlite3
from datetime import datetime, UTC
from pathlib import Path
import ninjarmy
from ninjarmy.agents.agent_schema import AgentSpec

DB_PATH =Path(ninjarmy.__file__).parent / "state" / "state.sql"
STATE_PATH =Path(ninjarmy.__file__).parent / "state"
DB_PATH.parent.mkdir(exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        role TEXT,
        task TEXT
    )
""")
conn.execute("""
    CREATE TABLE IF NOT EXISTS session (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        active INTEGER NOT NULL DEFAULT 0,
        started_at TEXT,
        name TEXT
        context TEXT
    )
""")
conn.commit()


def start_session(name: str = ""):
    context_path = Path(STATE_PATH / f"{name}_project_context.md")
    context = context_path.read_text(encoding="utf-8") if context_path.exists() else None
    conn.execute(
        "INSERT OR REPLACE INTO session (id, active, started_at, name, context) VALUES (1, 1, ?, ?, ?)",
        (datetime.now(UTC).isoformat(), name, context)
    )
    conn.commit()

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
            "INSERT INTO agents (id, name, role, task) VALUES (?, ?, ?, ?)",
            (spec.id, spec.name, spec.role, spec.task)
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