# TUI — Terminal User Interface

Built with [Textual](https://textual.textualize.io/). Provides a real-time terminal dashboard for controlling agents and watching their output live.

## Layout

```
┌─────────────────────────────────────────────────────┐
│  Header                                             │
├──────────────┬──────────────────────────────────────┤
│  Manager     │  Agent panels (scrollable)           │
│  panel       │  (one per hired agent)               │
├──────────────┴──────────────────────────────────────┤
│  Message input                                      │
└─────────────────────────────────────────────────────┘
```

## Key Files

| File | Responsibility |
|------|----------------|
| `app.py` | Main Textual app, all widgets and command handling |
| `style.tcss` | Dark theme stylesheet (Textual CSS) |

## Important Classes

### `NinjarmyApp`
The root Textual app. On mount it either shows `ProjectSetupScreen` (first run) or hydrates the existing session and starts all agent loops.

### `ProjectSetupScreen`
Modal dialog that collects a project name and description on first boot. Saves context to disk and starts the session before the main app continues.

### `AgentWidget` / `ManagerWidget`
Each widget owns a `RichLog` and an async drain worker (`_drain_output`) that reads from the agent's `output_queue` and renders events to the log in real time. Output is buffered and flushed as Markdown paragraphs — individual characters are not rendered one at a time.

## Commands

| Input | Action |
|-------|--------|
| `/hire <name> <role> <task>` | Hire a new agent and mount its panel |
| `/agents` | List active agents |
| `/stop [name\|all]` | Stop agent(s) |
| `/restart [name\|all]` | Restart agent(s) |
| `/<agent-name> <message>` | Message a specific agent directly |
| Any other text | Sent to the manager |

## Non-obvious Behaviors

- **Output buffering:** Text accumulates in a string buffer and is flushed as a Markdown block on events like `tool_call` or `system`. This avoids rendering individual characters and keeps the log readable.
- **Dynamic panel mounting:** Calling `/hire` mounts a new `AgentWidget` into the scroll container at runtime — no restart needed.
- **Agent restart with history:** When an agent is restarted, it loads the last 20 messages from disk so it isn't starting blind.

## Styling

`style.tcss` is a Textual CSS file. Colors use Textual's CSS variable system (`$primary`, `$background`, etc.). The dark-cyan theme and panel borders are all defined here — no Python-side style logic. If you're adding a new widget, add its styles to this file.
