import asyncio
import json
import os
import anthropic
from ninjarmy.agents.agent_schema import AgentSpec, ManagerSpec
from ninjarmy.core.agent import Agent, AgentMessage, get_valid_roles
from ninjarmy.core.registry import AgentRegistry
from ninjarmy.core.tools import MANAGER_TOOLS, MANAGER_TOOL_SCHEMAS
from ninjarmy.core import model

DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "claude-haiku-4-5")
NINJARMY_DEBUG = os.getenv("NINJARMY_DEBUG", 0)
MANAGER_MAX_TOOL_ITERATIONS = 25

class ManagerAgent:
    _instance = None

    def __init__(self, spec: ManagerSpec):
        existing = AgentRegistry.all()
        self.project_name = "todolist"
        self.agent_ids = max((a.id for a in existing), default=0)
        self.model: str = spec.model
        self.output_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()
        self.inbox: asyncio.Queue[str] = asyncio.Queue()
        self.history: list[dict] = []
        self.system_prompt: str = self.build_system_prompt()
        self.root: str = None

    def set_working_dir(self, root: str):
        self.root = root

    def hire_agent(self, name: str, task: str, role: str) -> Agent:
        valid = get_valid_roles()
        if valid and role not in valid:
            raise ValueError(f"Unknown role '{role}'. Available roles: {', '.join(valid)}")
        self.agent_ids += 1
        agent = Agent(AgentSpec(name=name, role=role, task=task, id=self.agent_ids, model=DEFAULT_MODEL))
        AgentRegistry.register(agent)
        agent.start()
        from ninjarmy.core.event_bus import EventBus
        EventBus.get().publish({"type": "agent_hired", "name": name, "role": role, "task": task})
        return agent

    def fire_agent(self, agent_id: int) -> None:
        agent = AgentRegistry.get(agent_id)
        if agent is None:
            raise ValueError(f"No agent with id {agent_id}.")
        agent.stop()
        AgentRegistry.unregister(agent_id)

    def build_system_prompt(self) -> str:
        task_board_path = model.STATE_PATH / "task_board.md" if model.STATE_PATH else ".ninjarmy/task_board.md"
        instructions = (
            "You are the Manager Agent coordinating a team of AI coding agents.\n\n"
            "Your role is to understand what the user wants and delegate work to the right agents. "
            "You have file tools for reading the codebase, `send_to_agent` to dispatch tasks, and `view_active_agents` to see your team.\n\n"
            "When delegating:\n"
            "- Use `view_active_agents` to see who is available before assigning work.\n"
            f"- Read the task board at `{task_board_path}` to see what files agents are already working on — avoid sending two agents to the same files.\n"
            "- Use `send_to_agent` to assign tasks. Be specific: include the exact file(s) to touch, what change to make, and explicit scope boundaries.\n"
            "- Always tell agents what NOT to do: 'Do not create any new files. Only modify the function I specified.'\n"
            "- Keep delegations focused — one clear task per agent, not open-ended exploration.\n"
            "- After delegating, briefly tell the user what you've assigned and to whom.\n\n"
            "When using tools, minimize commentary between calls. Act directly."
        )
        context_path = model.STATE_PATH / f"{self.project_name}_project_context.md"
        project_context = context_path.read_text() if context_path.exists() else ""
        if project_context:
            return instructions + "\n\n## Project Context\n" + project_context
        return instructions

    def send_message(self, msg: str) -> None:
        self.inbox.put_nowait(msg)

    async def _emit(self, msg: "AgentMessage") -> None:
        await self.output_queue.put(msg)
        from ninjarmy.core.event_bus import EventBus
        EventBus.get().publish({
            "source": "manager",
            "source_type": "manager",
            "type": msg.type,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
        })

    async def run(self) -> None:
        client = anthropic.AsyncAnthropic()
        while True:
            try:
                msg = await asyncio.wait_for(self.inbox.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            self.history.append({"role": "user", "content": msg})

            full_text = ""
            tool_iterations = 0
            while True:
                tool_iterations += 1
                if tool_iterations > MANAGER_MAX_TOOL_ITERATIONS:
                    await self._emit(AgentMessage(type="system", content="[safety] Tool loop exceeded 10 iterations. Stopping."))
                    break

                try:
                    async with client.messages.stream(
                        model=self.model,
                        max_tokens=2048,
                        tools=MANAGER_TOOL_SCHEMAS,
                        system=self.system_prompt,
                        messages=self.history,
                    ) as stream:
                        async for delta in stream.text_stream:
                            full_text += delta
                            await self._emit(AgentMessage(type="log", content=delta))
                        final_message = await stream.get_final_message()
                except Exception as e:
                    await self._emit(AgentMessage(type="system", content=f"[error] API call failed: {e}"))
                    break

                if final_message.stop_reason == "end_turn":
                    self.history.append({"role": "assistant", "content": full_text})
                    break

                elif final_message.stop_reason == "tool_use":
                    self.history.append({"role": "assistant", "content": final_message.content})
                    tool_results = []
                    for block in final_message.content:
                        if block.type != "tool_use":
                            continue
                        await self._emit(AgentMessage(type="tool_call", content=f"{block.name}({block.input})"))
                        try:
                            result = MANAGER_TOOLS[block.name](**block.input)
                        except Exception as e:
                            result = {"error": f"Tool '{block.name}' raised an exception: {e}"}
                        # Emit a route message when the manager delegates to an agent
                        # if block.name == "send_to_agent":
                            # agent_name = block.input.get("agent_name", "?")
                            # message = block.input.get("message", "")
                            # await self._emit(AgentMessage(type="route", content=f"-> {agent_name}: {message}"))
                        await self._emit(AgentMessage(type="tool_result", content=str(result)))
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })
                    self.history.append({"role": "user", "content": tool_results})
                    full_text = ""

                elif final_message.stop_reason == "max_tokens":
                    self.history.append({"role": "assistant", "content": full_text})
                    await self._emit(AgentMessage(type="system", content="[safety] Response cut off: max tokens reached."))
                    break

                else:
                    self.history.append({"role": "assistant", "content": full_text})
                    await self._emit(AgentMessage(type="system", content=f"[safety] Unexpected stop reason: {final_message.stop_reason!r}. Stopping."))
                    break

    @classmethod
    def get(cls) -> "ManagerAgent":
        if not cls._instance:
            cls._instance = cls(ManagerSpec())
        return cls._instance
