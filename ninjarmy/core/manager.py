from ninjarmy.agents.agent_spec import AgentSpec, AgentCreateSpec
from ninjarmy.core.agent import Agent
from ninjarmy.core.registry import AgentRegistry

class ManagerAgent:
    _instance = None

    def __init__(self):
        self.agent_ids = 0
    
    def hire_agent(self, spec: AgentCreateSpec) -> Agent:
        self.agent_ids += 1
        agent = Agent(AgentSpec(name=spec.name, role=spec.role, task=spec.task, id=self.agent_ids))
        AgentRegistry.register(agent)
        agent.start()
        return agent

    @classmethod
    def get(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance