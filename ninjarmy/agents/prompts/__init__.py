from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent

def load_role_promts(role: str) -> str:
    path = _PROMPTS_DIR / f"{role}.md"
    return path.read_text() if path.exists() else None