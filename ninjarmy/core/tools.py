from pathlib import Path


def _check_path(path: str) -> tuple[Path | None, dict | None]:
    """Resolve path and verify it's within the workspace root.
    Returns (resolved_path, None) on success or (None, error_dict) on failure.
    """
    from ninjarmy.core.manager import ManagerAgent
    root = Path(ManagerAgent.get().root).resolve()
    resolved = Path(path).resolve()
    if not str(resolved).startswith(str(root)):
        return None, {"error": "Path outside of workspace"}
    return resolved, None


def read_file(path: str):
    """Read the contents of a file at the given path.

    Args:
        path: Absolute or relative path to the file. Must be within the workspace root.

    Returns:
        On success: {"content": str, "size_bytes": int}
        On failure: {"error": str}
    """
    file, err = _check_path(path)
    if err:
        return err
    if not file.exists():
        return {"error": "File not found"}
    if file.is_dir():
        return {"error": f"'{path}' is a directory, not a file. Use list_directory to see its contents."}
    content = file.read_text()
    return {"content": content, "size_bytes": len(content.encode())}


def write_file(path: str, content: str, append: bool = False):
    """Write or append content to a file. Creates the file if it does not exist.

    Args:
        path: Absolute or relative path to the file. Must be within the workspace root.
        content: Text content to write.
        append: If True, append to the file instead of overwriting. Fails if file does not exist.

    Returns:
        On success: {"success": True, "path": str, "size_bytes": int}
        On failure: {"error": str}
    """
    file, err = _check_path(path)
    if err:
        return err
    if not file.exists() and append:
        return {"error": "File not found"}
    if append:
        with file.open("a") as f:
            f.write(content)
    else:
        file.write_text(content)
    from ninjarmy.core.event_bus import EventBus
    EventBus.get().publish({"type": "file_changed", "path": str(file)})
    return {"success": True, "path": str(file), "size_bytes": len(content.encode())}


def list_directory(path: str):
    """List the immediate contents of a directory (non-recursive).

    Args:
        path: Absolute or relative path to the directory. Must be within the workspace root.

    Returns:
        On success: {"entries": [{"name": str, "type": "file"|"directory", "size_bytes": int}]}
        On failure: {"error": str}
    """
    directory, err = _check_path(path)
    if err:
        return err
    if not directory.exists():
        return {"error": "Directory not found"}
    entries = []
    for f in directory.iterdir():
        if f.is_file():
            entries.append({"name": f.name, "type": "file", "size_bytes": f.stat().st_size})
        elif f.is_dir():
            entries.append({"name": f.name, "type": "directory"})
    return {"entries": entries}


def create_directory(path: str):
    """Create a new directory, including any missing intermediate directories.

    Args:
        path: Absolute or relative path of the directory to create. Must be within the workspace root.

    Returns:
        On success: {"success": True, "path": str}
        On failure: {"error": str}
    """
    directory, err = _check_path(path)
    if err:
        return err
    if directory.exists():
        return {"error": "Directory already exists"}
    directory.mkdir(parents=True)
    return {"success": True, "path": str(directory)}


def send_to_agent(agent_name: str, message: str):
    """Send a message to a named agent on behalf of the manager.

    Args:
        agent_name: The name of the agent to send the message to.
        message: The message or task to send to the agent.

    Returns:
        On success: {"success": True, "agent": str}
        On failure: {"error": str}
    """
    from ninjarmy.core.registry import AgentRegistry
    agents = AgentRegistry.all()
    agent = next((a for a in agents if a.name == agent_name), None)
    if agent is None:
        names = [a.name for a in agents]
        return {"error": f"No agent named '{agent_name}'. Available: {names}"}
    agent.prompt(message, source="manager")
    print(agent.name, agent.output_queue)
    return {"success": True, "agent": agent_name}

def view_active_agents():
    """List information about all active agents.

    Args:
        None

    Returns:
        On success: {"agents": [{"name": str, "role": str, "task": str, "status": str}]}
    """
    from ninjarmy.core.registry import AgentRegistry
    agents = AgentRegistry.all()
    return {
        "agents": [
            {"name": a.name, "role": a.role, "task": a.task, "status": a.status}
            for a in agents
        ]
    }


def read_context(agent_name: str):
    """Read another agent's saved context file to see their findings and progress.

    Args:
        agent_name: The name of the agent whose context you want to read.

    Returns:
        On success: {"content": str}
        On failure: {"error": str}
    """
    from ninjarmy.core import model
    path = model.STATE_PATH / f"{agent_name}_context.md"
    if not path.exists():
        return {"error": f"No context file found for agent '{agent_name}'."}
    return {"content": path.read_text(encoding="utf-8")}


def make_agent_tools(agent_name: str) -> tuple[dict, list]:
    """Create agent-specific tools that capture the agent's identity."""
    from ninjarmy.core import model

    def save_context(content: str):
        """Save a summary of your findings or progress to your context file.
        Other agents can read this with read_context. Use this to share key
        discoveries, decisions, or status updates.

        Args:
            content: The context or summary to save.

        Returns:
            {"success": True}
        """
        path = model.STATE_PATH / f"{agent_name}_context.md"
        path.write_text(content, encoding="utf-8")
        return {"success": True}

    def claim_task(files: str):
        """Register the files you are about to work on in the shared task board.
        Call this before writing to any files so other agents know not to touch them.

        Args:
            files: Comma-separated list of file paths you are claiming.

        Returns:
            {"success": True} or {"error": str} if a file is already claimed.
        """
        board_path = model.STATE_PATH / "task_board.md"
        lines = board_path.read_text(encoding="utf-8").splitlines() if board_path.exists() else ["# Task Board", ""]
        # Check for conflicts
        claimed_files = {f.strip() for f in files.split(",")}
        for line in lines:
            parts = line.split("|")
            if len(parts) == 3:
                owner, status, existing = parts[0].strip(), parts[1].strip(), parts[2].strip()
                if owner != agent_name and status == "working":
                    overlap = claimed_files & {f.strip() for f in existing.split(",")}
                    if overlap:
                        return {"error": f"{owner} is already working on: {', '.join(overlap)}"}
        # Remove any existing entry for this agent and add new one
        lines = [l for l in lines if not l.startswith(f"{agent_name} |")]
        lines.append(f"{agent_name} | working | {files}")
        board_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {"success": True}

    def finish_task():
        """Mark your claimed task as done on the task board. Call this when you
        have finished your work so other agents know the files are free.

        Returns:
            {"success": True}
        """
        board_path = model.STATE_PATH / "task_board.md"
        if not board_path.exists():
            return {"success": True}
        lines = board_path.read_text(encoding="utf-8").splitlines()
        updated = []
        for line in lines:
            if line.startswith(f"{agent_name} | working |"):
                files = line.split("|", 2)[2].strip()
                updated.append(f"{agent_name} | done | {files}")
            else:
                updated.append(line)
        board_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
        return {"success": True}

    tools = {
        **TOOLS,
        "save_context": save_context,
        "read_context": read_context,
        "claim_task": claim_task,
        "finish_task": finish_task,
    }

    schemas = TOOL_SCHEMAS + [
        {
            "name": "save_context",
            "description": "Save a summary of your findings or progress. Other agents can read this with read_context.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "The context or summary to save."},
                },
                "required": ["content"],
            },
        },
        {
            "name": "read_context",
            "description": "Read another agent's saved context file to see their findings and progress.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "The name of the agent whose context you want to read."},
                },
                "required": ["agent_name"],
            },
        },
        {
            "name": "claim_task",
            "description": "Register the files you are about to work on. Warns if another agent already claimed them.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "files": {"type": "string", "description": "Comma-separated list of file paths you are claiming."},
                },
                "required": ["files"],
            },
        },
        {
            "name": "finish_task",
            "description": "Mark your claimed task as done on the task board so other agents know the files are free.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]

    return tools, schemas


TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "create_directory": create_directory,
}

MANAGER_TOOLS = {
    **TOOLS,
    "send_to_agent": send_to_agent,
    "view_active_agents": view_active_agents,
}

TOOL_SCHEMAS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file. Must be within the workspace root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative path to the file."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write or append content to a file. Creates the file if it does not exist. Must be within the workspace root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative path to the file."},
                "content": {"type": "string", "description": "Text content to write."},
                "append": {"type": "boolean", "description": "If true, append instead of overwrite. Fails if file does not exist."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_directory",
        "description": "List the immediate contents of a directory (non-recursive). Must be within the workspace root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative path to the directory."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "create_directory",
        "description": "Create a new directory, including any missing intermediate directories. Must be within the workspace root.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative path of the directory to create."},
            },
            "required": ["path"],
        },
    },
]

MANAGER_TOOL_SCHEMAS = TOOL_SCHEMAS + [
    {
        "name": "send_to_agent",
        "description": "Send a task or message to a specific agent by name. Use this to delegate work to agents on your team. The agent will immediately start working on what you send.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {"type": "string", "description": "The name of the agent to send the message to."},
                "message": {"type": "string", "description": "The task or message to send to the agent."},
            },
            "required": ["agent_name", "message"],
        },
    },
    {
        "name": "view_active_agents",
        "description": "List all currently active agents and their details (name, role, task, status). Use this to see who is on your team before delegating work.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]