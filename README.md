# NinjArmy

**NinjArmy** is a local-first, open-source platform for orchestrating multiple AI coding agents. You build a team, assign roles, and watch them work in parallel - coordinated by a Manager AI that routes tasks and synthesizes results. Its vibe coding with more structure.

---

## What it does

- **Manager AI** maintains project context and delegates work to your team
- **Specialized agents** with distinct roles: Tester, Optimizer, Brute Force, Janitor, Architect, or Custom agents defined by you
- **Parallel execution** — agents work simultaneously, not sequentially
- **Agent-to-agent routing** — manager dispatches tasks directly to named agents
- **Persistent memory** — agents save history and context between sessions
- **Task board** — agents claim files before writing to avoid conflicts
- **Bring your own keys** — runs on Anthropic's Claude API, no cloud lock-in

---

## Install


Clone and install locally:

```bash
git clone https://github.com/bodecoop/ninjarmy.git
cd ninjarmy
pip install .
```

Set your API key:

```bash
export ANTHROPIC_API_KEY=...
# or add it to a .env file in your project directory
```

Launch from any project directory:

```bash
cd your-project
ninjarmy boot
```

---

## Quick start

On first boot, a setup screen asks for a project name and what agents should know about your codebase. After that, you're in the terminal UI.

**Hire agents:**
```
/hire main-tester tester write tests for the auth module
/hire core-dev optimizer improve performance in utils.py
```

**Let the manager coordinate:**
```
review the auth module and delegate fixes to the team
```

The manager reads your codebase, decides what to do, and routes tasks directly to main-tester and core-dev. You see routing events in real time.

**Talk directly to an agent:**
```
/main-tester focus on the login edge cases
```

**View active agents:**
```
/agents
```

**Stop an agent:**
```
/stop main-tester
/restart main-tester
```

---

## Agent roles

| Role | What it does |
|------|-------------|
| `tester` | Writes thorough tests — happy path, edge cases, error handling |
| `optimizer` | Finds bottlenecks and applies targeted performance improvements |
| `brute-force` | Gets things working fast — correctness over elegance |
| `janitor` | Refactors, removes dead code, enforces consistency |
| `architect` | Designs systems — proposes structure, interfaces, and trade-offs |
| `custom` | General-purpose — good for tasks that don't fit a specific role |

---

## All commands

| Command | Description |
|---------|-------------|
| `/hire <name> <role> <task...>` | Hire a new agent |
| `/agents` | List all active agents |
| `/stop <name\|all>` | Stop an agent or all agents |
| `/restart <name\|all>` | Resume a stopped agent |
| `/<name> <message>` | Send a message directly to an agent |
| `/help` | Show command reference |

Plain text (no `/`) goes to the Manager.

---

## How it works

User communicates with the manager, who can view active agents and delegate tasks accordingly

Agents write to a shared task board (`.ninjarmy/task_board.md`) when they claim files, preventing two agents from clobbering the same file.

---

## Project structure

```
.ninjarmy/              # per-project state (gitignored)
├── state.db            # agent and session records
├── task_board.md       # live task ownership
├── <name>_history.json # agent conversation history
└── <name>_context.md   # agent-written summaries

ninjarmy/
├── agents/             # role definitions (agents.yaml)
├── core/               # agent, manager, tools, registry
├── tui/                # Textual terminal UI
└── cli/                # entry points
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required |
| `DEFAULT_MODEL` | `claude-haiku-4-5` | Model for all agents |
| `NINJARMY_DEBUG` | `0` | Enable debug logging |

---

## Requirements

- Python 3.10+
- An Anthropic API key

---

## License

MIT

## More

ninjarmy/tui/README.md
ninjarmy/server/README.md
ninjarmy/core/README.md
ninjarmy/agents/README.md
ninjarmy/cli/README.md