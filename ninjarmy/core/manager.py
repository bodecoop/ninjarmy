import asyncio
import json
import os
import anthropic
from ninjarmy.agents.agent_schema import AgentSpec, ManagerSpec
from ninjarmy.core.agent import Agent, AgentMessage
from ninjarmy.core.registry import AgentRegistry
from ninjarmy.core.tools import TOOLS, TOOL_SCHEMAS
from ninjarmy.core import model

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "claude-haiku-4-5")
NINJARMY_DEBUG = os.getenv("NINJARMY_DEBUG", 0)

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
        self.root: str = None

    def set_working_dir(self, root: str):
        self.root = root

    def hire_agent(self, name: str, task: str, role: str) -> Agent:
        self.agent_ids += 1
        agent = Agent(AgentSpec(name=name, role=role, task=task, id=self.agent_ids, model=DEFAULT_MODEL))
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
        instructions = "You are the Manager Agent coordinating a team of AI coding agents. Help the user plan and delegate development tasks. When using tools, minimize commentary between calls. Act directly."
        context_path = model.STATE_PATH / f"{self.project_name}_project_context.md"
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
                while True:
                    async with client.messages.stream(
                        model=self.model,
                        max_tokens=2048,
                        tools=TOOL_SCHEMAS,
                        system=self.system_prompt,
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

        
    @classmethod
    def get(cls) -> "ManagerAgent":
        if not cls._instance:
            cls._instance = cls(ManagerSpec())
        return cls._instance