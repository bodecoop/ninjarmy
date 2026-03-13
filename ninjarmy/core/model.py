import sqlite3
from datetime import datetime, UTC
from pathlib import Path
import ninjarmy
from ninjarmy.agents.agent_spec import AgentSpec

DB_PATH =Path(ninjarmy.__file__).parent / "state" / "state.sql"
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
        project TEXT
    )
""")
conn.commit()


def start_session(project: str = ""):
    conn.execute(
        "INSERT OR REPLACE INTO session (id, active, started_at, project) VALUES (1, 1, ?, ?)",
        (datetime.now(UTC).isoformat(), project)
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