# ninjarmy.core.registry.py
from ninjarmy.core.agent import Agent
from typing import Dict
from ninjarmy.agents.agent_spec import AgentSpec
from ninjarmy.core.model import load_agents, save_agent

class AgentRegistry:
    _agents: Dict[int, Agent] = {}

    @classmethod
    def hydrate(cls):
        for row in load_agents():
            spec = AgentSpec(id=row[0], name=row[1], role=row[2], task=row[3])
            cls._agents[spec.id] = Agent(spec)

    @classmethod
    def register(cls, agent: Agent):
        print(f"Registering agent {agent.get_id()}")
        cls._agents[agent.id] = agent

    @classmethod
    def unregister(cls, id: int):
        cls._agents.pop(id)

    @classmethod
    def get(cls, id):
        return cls._agents.get(id)

    @classmethod
    def all(cls):
        return list(cls._agents.values())
    
    @classmethod
    def agent_count(cls):
        return len(cls._agents)
    