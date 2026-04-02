import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

import json

import anthropic

from ninjarmy.agents.agent_schema import AgentSpec
from ninjarmy.core.tools import TOOLS, TOOL_SCHEMAS
from ninjarmy.core import model


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
        self.history: list[dict] = []

    def stop(self):
        self.status = "stopped"

    def start(self):
        self.status = "running"

    def prompt(self, msg: str):
        # send message to agent API with agent context
        context_path = model.STATE_PATH / f"{self.id}_context.md"
        agent_context = context_path.read_text(encoding="utf-8") if context_path.exists() else None

        self.inbox.put_nowait(msg)

    async def run(self):
        # async loop, consumes inbox, streams to output_queue
        client = anthropic.AsyncAnthropic()
        system = f"You are {self.name}, a {self.role} agent. Your task: {self.task}. When using tools, minimize commentary between calls. Act directly."
        while True:
            try:
                msg = await asyncio.wait_for(self.inbox.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            self.history.append({"role": "user", "content": msg})
            full_text = ""
            while True:
                async with client.messages.stream(
                    model=self.model,
                    max_tokens=2048,
                    tools=TOOL_SCHEMAS,
                    system=system,
                    messages=self.history,
                ) as stream:
                    async for delta in stream.text_stream:
                        full_text += delta
                        await self.output_queue.put(AgentMessage(type="log", content=delta))
                    final_message = await stream.get_final_message()

                if final_message.stop_reason == "end_turn":
                    self.history.append({"role": "assistant", "content": full_text})
                    break

                if final_message.stop_reason == "tool_use":
                    self.history.append({"role": "assistant", "content": final_message.content})
                    tool_results = []
                    for block in final_message.content:
                        if block.type != "tool_use":
                            continue
                        await self.output_queue.put(AgentMessage(type="tool_call", content=f"{block.name}({block.input})"))
                        result = TOOLS[block.name](**block.input)
                        await self.output_queue.put(AgentMessage(type="tool_result", content=str(result)))
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })
                    self.history.append({"role": "user", "content": tool_results})
                    full_text = ""