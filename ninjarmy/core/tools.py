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


TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "create_directory": create_directory,
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