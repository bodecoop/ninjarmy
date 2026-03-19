import os
from pathlib import Path
import anthropic
import ninjarmy

_CONTEXT_PATH = Path(ninjarmy.__file__).parent / "state" / "context.md"

_SYSTEM_PROMPT = """\
You are a project context builder for an AI agent orchestration system.
Given a user's project description, produce a concise, structured context document in Markdown.
Include: project goal, key domain concepts, likely tasks agents will perform, and any constraints or priorities.
Be specific and actionable — this document will be given to AI agents as their project context.
"""

_DEBUG_CONTEXT = """\
# Debug Project Context

**Goal:** Build a web scraper for e-commerce price tracking.

**Domain Concepts:** products, prices, retailers, scrape jobs

**Agent Tasks:** scrape product pages, normalize data, detect price changes

**Constraints:** rate-limit requests, handle pagination
"""

def generate_project_context(project: str) -> str:
    if os.getenv("NINJARMY_DEBUG"):
        return _DEBUG_CONTEXT
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        # thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": project}],
    )
    return next(block.text for block in response.content if block.type == "text")

def save_context(context: str) -> None:
    _CONTEXT_PATH.parent.mkdir(exist_ok=True)
    _CONTEXT_PATH.write_text(context, encoding="utf-8")

def load_context() -> str | None:
    if _CONTEXT_PATH.exists():
        return _CONTEXT_PATH.read_text(encoding="utf-8")
    return None