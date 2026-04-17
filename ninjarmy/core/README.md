# Core — Agent Orchestration Engine

This is the heart of NinjArmy. It manages agent and manager lifecycles, handles tool execution, persists state, and broadcasts events to the UI.

## Key Files

| File | Responsibility |
|------|----------------|
| `agent.py` | Worker agent — async loop, Claude API calls, tool execution |
| `manager.py` | Manager agent — singleton coordinator, delegates tasks to workers |
| `tools.py` | All tool implementations (file I/O, collaboration primitives, manager tools) |
| `model.py` | SQLite persistence for sessions, agents, and message history |
| `registry.py` | In-memory agent registry (ID → Agent) |
| `event_bus.py` | Pub-sub event bus for broadcasting activity to UI clients |
| `context.py` | Generates project context documents via Claude API |

## Data Flow

```
User input
  → ManagerAgent.send_message()
  → ManagerAgent._run() [Claude API + tool loop]
  → (if send_to_agent tool used)
  → Agent.prompt() [enqueued to agent inbox]
  → Agent._run() [Claude API + tool loop]
  → All activity → EventBus.publish(event)
  → TUI / WebSocket clients
```

## Agent Loop (`agent.py`)

Each agent runs an independent async loop:
1. Wait up to 1 second for a message on its `inbox` queue
2. Call the Claude API with the full message history (streaming)
3. Execute any tool calls returned, append results to history
4. Repeat until `end_turn` or `max_tokens` stop reason
5. Persist the last 20 messages to disk

**Safety caps:** Agents are limited to 25 tool iterations per task. The manager is capped at 10. Exceeding the cap returns an error to the model.

**Rate limit resilience:** On `RateLimitError`, agents retry up to 3 times with exponential backoff (5s → 10s → 20s).

**History truncation:** Tool results larger than 2000 characters are trimmed before being stored in history to prevent token bloat.

## Tools (`tools.py`)

Tools are plain functions that return dicts — they never raise exceptions. Errors are always `{"error": "message"}`.

| Tool | Available to | Description |
|------|-------------|-------------|
| `read_file` | All agents | Read a file within the workspace |
| `write_file` | All agents | Write or append to a file |
| `list_directory` | All agents | List directory contents |
| `create_directory` | All agents | Create a directory |
| `claim_task` | All agents | Claim files on the task board |
| `finish_task` | All agents | Release file claims |
| `save_context` | All agents | Write shared context to disk |
| `read_context` | All agents | Read another agent's saved context |
| `send_to_agent` | Manager only | Route a message to a named agent |
| `view_active_agents` | Manager only | List all running agents |

**Path safety:** Every file tool validates the path is inside the workspace root via `_check_path()`. Paths outside the root are rejected.

Use `make_agent_tools(agent_name)` to get the tool dict and JSON schemas for a given agent.

## Task Board

The task board (`.ninjarmy/task_board.md`) prevents write conflicts between parallel agents. Before working on files, an agent calls `claim_task(files)`. If another agent has those files marked as "working", the claim is rejected. `finish_task()` releases the claim.

## EventBus (`event_bus.py`)

Simple pub-sub. Each subscriber gets its own `asyncio.Queue`. Publishing is synchronous (`put_nowait`) so it never blocks.

```python
q = EventBus.subscribe()   # get a queue
EventBus.publish({"type": "log", "agent": "tester", "text": "..."})
EventBus.unsubscribe(q)
```

## Persistence (`model.py`)

All state is stored in `.ninjarmy/state.db` (SQLite) and JSON files:

- **Sessions** — tracked in DB; only one active at a time
- **Agents** — saved to DB on hire; loaded back on `server`/`boot` restart
- **Message history** — last 20 messages per agent in `.ninjarmy/{name}_history.json`
- **Project context** — `.ninjarmy/{project_name}_project_context.md`
- **Agent context** — `.ninjarmy/{agent_name}_context.md` (for `save_context`/`read_context`)

`_serialize_message()` strips SDK-specific fields (e.g., `parsed_output`, `citations`) that the Claude API rejects when messages are echoed back.

## Adding a New Tool

1. Implement the function in `tools.py` — return a dict, never raise
2. Add a JSON schema entry (name, description, input_schema) to the appropriate schema list
3. Add it to `make_agent_tools()` or the manager tools dict as appropriate
4. Publish an `EventBus` event if the tool changes workspace state
