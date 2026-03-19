import asyncio
import os
from pathlib import Path

import anthropic
import ninjarmy
from ninjarmy.agents.agent_schema import AgentSpec, ManagerSpec
from ninjarmy.core.agent import Agent, AgentMessage
from ninjarmy.core.registry import AgentRegistry

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "claude-haiku-4-5")
STATE_PATH =Path(ninjarmy.__file__).parent / "state"

class ManagerAgent:
    _instance = None

    def __init__(self, spec: ManagerSpec):
        existing = AgentRegistry.all()
        self.project_name = "todolist"
        self.agent_ids = max((a.id for a in existing), default=0) # initalizes id counter
        self.model: str = spec.model
        self.output_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self.inbox: asyncio.Queue[str] = asyncio.Queue()
        self.history: list[dict] = []
        self.system_prompt: str = self.build_system_prompt()

    def hire_agent(self, spec: AgentSpec) -> Agent:
        self.agent_ids += 1
        agent = Agent(AgentSpec(name=spec.name, role=spec.role, task=spec.task, id=self.agent_ids, model=DEFAULT_MODEL))
        AgentRegistry.register(agent)
        agent.start()
        # start agent.run s an asyncio task
        return agent

    def fire_agent(self, agent_id: int) -> None:
        agent = AgentRegistry.get(agent_id)
        if agent is None:
            raise ValueError(f"No agent with id {agent_id}.")
        agent.stop()
        AgentRegistry.unregister(agent_id)

    def build_system_prompt(self) -> str:
        instructions = "You are the Manager Agent coordinating a team of AI coding agents. Help the user plan and delegate development tasks."
        context_path = Path(STATE_PATH / f"{self.project_name}_project_context.md")
        project_context = context_path.read_text() if context_path.exists() else ""
        if project_context:
            return instructions + "\n\n ## Project Context \n" + project_context
        return instructions

    def send_message(self, msg: str) -> None:
        self.inbox.put_nowait(msg)

    async def run(self) -> None:
            client = anthropic.AsyncAnthropic()
            while True:
                try:
                    msg = await asyncio.wait_for(self.inbox.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue # check status again

                self.history.append({"role": "user", "content": msg})

                full_text = ""
                async with client.messages.stream(
                    model=self.model,
                    max_tokens=2048,
                    # thinking={"type": "adaptive"},
                    system=self.system_prompt,
                    messages=self.history,
                ) as stream:
                    async for delta in stream.text_stream:
                        full_text += delta
                        await self.output_queue.put(AgentMessage(type="log", content=delta))

                self.history.append({"role": "assistant", "content": full_text})

        
    @classmethod
    def get(cls) -> "ManagerAgent":
        if not cls._instance:
            cls._instance = cls(ManagerSpec())
        return cls._instance