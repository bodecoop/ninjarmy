# CLI — Command-line Entry Point

Built with [Click](https://click.palletsprojects.com/). Provides three commands for starting, serving, and cleaning up NinjArmy sessions.

## Commands

### `ninjarmy boot`
Launches the interactive TUI. Initializes the database and model state using the current working directory as the workspace root, then starts `NinjarmyApp`.

```bash
ninjarmy boot
```

### `ninjarmy server`
Starts the FastAPI web server. Initializes state, hydrates agents from the previous session, and runs Uvicorn.

```bash
ninjarmy server            # port 7337
ninjarmy server --port 8080
```

### `ninjarmy terminate`
Shuts down the active session — unregisters all agents from the database and marks the session as ended. Useful for cleaning up a stuck or orphaned session.

```bash
ninjarmy terminate
```

## Key File

| File | Responsibility |
|------|----------------|
| `main.py` | Click group and all command definitions |

## Adding a New Command

1. Add a new `@cli.command()` function in `main.py`
2. Call `model.init(os.getcwd())` first if the command needs database access
3. Register any new dependencies in `pyproject.toml` if needed

## Non-obvious Behaviors

- Both `boot` and `server` use the **current working directory** as the workspace root. Run them from the project directory you want agents to operate in.
- `Rich` tracebacks are installed on boot for readable error output in the terminal.
