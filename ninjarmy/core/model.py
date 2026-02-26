import sqlite3
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
conn.commit()

def save_agent(spec: AgentSpec):
    conn.execute(
        "INSERT INTO agents (id, name, role, task) VALUES ? ? ? ?",
        (spec.id, spec.name, spec.role, spec.task)
    )
    conn.commit()

def load_agents():
    rows = conn.execute("SELECT * FROM agents").fetchall()
    return rows