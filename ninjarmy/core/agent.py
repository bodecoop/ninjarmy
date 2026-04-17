import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

import json
import yaml

import anthropic

_HISTORY_TOOL_RESULT_CAP = 2000  # chars stored per tool result in history
_MAX_TOOL_ITERATIONS = 25  # amount of times an agent can use tools per task

from ninjarmy.agents.agent_schema import AgentSpec
from ninjarmy.core.tools import make_agent_tools
from ninjarmy.core import model

_AGENTS_YAML = Path(__file__).parent.parent / "agents" / "agents.yaml"


def _load_role_prompt(role: str) -> str:
    try:
        data = yaml.safe_load(_AGENTS_YAML.read_text())
        roles = data.get("roles", {})
        entry = roles.get(role)
        if entry and "prompt" in entry:
            return entry["prompt"].strip()
    except Exception:
        pass
    return f"You are a {role} coding agent. Complete your task thoroughly and directly."


def get_valid_roles() -> list[str]:
    try:
        data = yaml.safe_load(_AGENTS_YAML.read_text())
        return list(data.get("roles", {}).keys())
    except Exception:
        return []


@dataclass
class AgentMessage:
    type: Literal["log", "tool_call", "tool_result", "system", "received", "route"]
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


class Agent:
    def __init__(self, spec: AgentSpec):
        self.spec = spec
        self.id: int = spec.id
        self.name: str = spec.name
        self.role: str = spec.role
        self.task: str = spec.task
        self.model: str = spec.model
        self.status: str = "stopped"
        self.output_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self.inbox: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        self.history: list[dict] = []

    def stop(self):
        self.status = "stopped"

    def start(self):
        self.status = "running"

    def prompt(self, msg: str, source: str = "user"):
        self.inbox.put_nowait((source, msg))

    def _build_system_prompt(self) -> str:
        role_prompt = _load_role_prompt(self.role)
        parts = [f"Your name is {self.name}.", role_prompt]
        if self.task:
            parts.append(f"Your current task: {self.task}")
        if model.STATE_PATH:
            board = model.STATE_PATH / "task_board.md"
            parts.append(
                f"Collaboration tools available to you:\n"
                f"- `claim_task(files)` — register files you're about to write to; warns if another agent has them\n"
                f"- `finish_task()` — mark your work done so others can use those files\n"
                f"- `save_context(content)` — save a summary of your findings for other agents to read. Keep it short and concise\n"
                f"- `read_context(agent_name)` — read another agent's saved findings\n"
                f"Always claim files before writing them. Save context when you finish significant work.\n"
                f"Task board is at: {board}"
            )
        return "\n\n".join(parts)

    async def _emit(self, msg: AgentMessage) -> None:
        await self.output_queue.put(msg)
        from ninjarmy.core.event_bus import EventBus
        EventBus.get().publish({
            "source": self.name,
            "source_type": "agent",
            "type": msg.type,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
        })

    async def run(self):
        try:
            await self._run()
        except Exception as e:
            await self._emit(AgentMessage(type="system", content=f"[fatal] Agent loop crashed: {e}"))

    async def _run(self):
        client = anthropic.AsyncAnthropic()
        system = self._build_system_prompt()
        agent_tools, agent_schemas = make_agent_tools(self.name)
        saved = model.load_history(self.name)
        if saved:
            self.history = saved
            await self._emit(AgentMessage(type="system", content=f"[ready] {self.name} is online. (history restored)"))
        else:
            await self._emit(AgentMessage(type="system", content=f"[ready] {self.name} is online."))
        while True:
            if self.status == "stopped":
                await asyncio.sleep(0.5)
                continue

            try:
                source, msg = await asyncio.wait_for(self.inbox.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if self.status == "stopped":
                await self._emit(AgentMessage(type="system", content="[stopped] Agent is stopped. Message discarded."))
                continue

            if source == "manager":
                await self._emit(AgentMessage(type="received", content=f"<- Manager: {msg}"))

            self.history.append({"role": "user", "content": msg})
            full_text = ""
            tool_iterations = 0
            while True:
                if self.status == "stopped":
                    await self._emit(AgentMessage(type="system", content="[stopped] Agent halted mid-task."))
                    break

                tool_iterations += 1
                if tool_iterations > _MAX_TOOL_ITERATIONS:
                    await self._emit(AgentMessage(type="system", content=f"[safety] Tool loop exceeded {_MAX_TOOL_ITERATIONS} iterations. Stopping."))
                    break

                final_message = None
                for attempt in range(3):
                    try:
                        async with client.messages.stream(
                            model=self.model,
                            max_tokens=8192,
                            tools=agent_schemas,
                            system=system,
                            messages=self.history,
                        ) as stream:
                            async for delta in stream.text_stream:
                                full_text += delta
                                await self._emit(AgentMessage(type="log", content=delta))
                            final_message = await stream.get_final_message()
                        break
                    except anthropic.RateLimitError:
                        wait = 5 * (2 ** attempt)
                        await self._emit(AgentMessage(type="system", content=f"[rate limit] Waiting {wait}s before retry ({attempt + 1}/3)..."))
                        await asyncio.sleep(wait)
                    except Exception as e:
                        await self._emit(AgentMessage(type="system", content=f"[error] API call failed: {e}"))
                        break
                if final_message is None:
                    await self._emit(AgentMessage(type="system", content="[error] API call failed after 3 retries."))
                    break

                if final_message.stop_reason == "end_turn":
                    self.history.append({"role": "assistant", "content": full_text})
                    model.save_history(self.name, self.history)
                    break

                elif final_message.stop_reason == "tool_use":
                    self.history.append({"role": "assistant", "content": final_message.content})
                    tool_results = []
                    for block in final_message.content:
                        if block.type != "tool_use":
                            continue
                        await self._emit(AgentMessage(type="tool_call", content=f"{block.name}({block.input})"))
                        result = agent_tools[block.name](**block.input)
                        await self._emit(AgentMessage(type="tool_result", content=str(result)))
                        # Truncate large results (e.g. file reads) before storing in history
                        result_str = json.dumps(result)
                        if len(result_str) > _HISTORY_TOOL_RESULT_CAP:
                            truncated = result_str[:_HISTORY_TOOL_RESULT_CAP]
                            result_str = truncated + f'... [truncated, full length: {len(result_str)} chars]"'
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_str,
                        })
                    self.history.append({"role": "user", "content": tool_results})
                    full_text = ""

                elif final_message.stop_reason == "max_tokens":
                    self.history.append({"role": "assistant", "content": full_text})
                    await self._emit(AgentMessage(type="system", content="[max tokens] Response cut off — continuing..."))
                    self.history.append({"role": "user", "content": "Continue."})
                    full_text = ""
                    # tool_iterations acts as the continuation cap — loop will stop at _MAX_TOOL_ITERATIONS

                else:
                    self.history.append({"role": "assistant", "content": full_text})
                    await self._emit(AgentMessage(type="system", content=f"[safety] Unexpected stop reason: {final_message.stop_reason!r}. Stopping."))
                    break
