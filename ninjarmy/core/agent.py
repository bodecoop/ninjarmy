import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from typing import Literal

import anthropic

import ninjarmy
from ninjarmy.agents.agent_schema import AgentSpec


@dataclass
class AgentMessage:
    type: Literal["log", "tool_call", "tool_result", "system"]
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


class Agent:
    def __init__(self, spec: AgentSpec):
        self.spec = spec # this feels redundant
        self.id: int = spec.id
        self.name: str = spec.name
        self.role: str = spec.role
        self.task: str = spec.task
        self.model: str = spec.model
        self.status: str = "stopped"
        self.output_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self.inbox: asyncio.Queue[str] = asyncio.Queue()

    def stop(self):
        self.status = "stopped"

    def start(self):
        self.status = "running"

    def prompt(self, msg: str):
        # send message to agent API with agent context
        STATE_PATH = Path(ninjarmy.__file__).parent / "state"
        context_path = Path(STATE_PATH / f"{self.id}_context.md")
        agent_context = context_path.read_text(encoding="utf-8") if context_path.exists() else None

        self.inbox.put_nowait(msg)

    async def run(self):
        # async loop, consumes inbox, streams to output_queue
        pass