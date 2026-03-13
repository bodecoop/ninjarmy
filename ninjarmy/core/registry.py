# ninjarmy.core.registry.py
from ninjarmy.core.agent import Agent
from typing import Dict
from ninjarmy.agents.agent_spec import AgentSpec
from ninjarmy.core.model import load_agents, save_agent, delete_agent

class AgentRegistry:
    _agents: Dict[int, Agent] = {}

    @classmethod
    def hydrate(cls):
        for row in load_agents():
            try:
                spec = AgentSpec(id=row[0], name=row[1], role=row[2], task=row[3])
                cls._agents[spec.id] = Agent(spec)
            except Exception as e:
                print(f"Warning: skipping corrupt agent row {row}: {e}")

    @classmethod
    def register(cls, agent: Agent):
        if any(a.name == agent.name for a in cls._agents.values()):
            raise ValueError(f"An agent named '{agent.name}' already exists.")
        print(f"Registering agent {agent.get_id()}")
        cls._agents[agent.id] = agent
        save_agent(agent.spec)

    @classmethod
    def unregister(cls, id: int):
        if id not in cls._agents:
            raise ValueError(f"No agent with id {id} found in registry.")
        cls._agents.pop(id)
        delete_agent(id)

    @classmethod
    def get(cls, id):
        return cls._agents.get(id)

    @classmethod
    def all(cls):
        return list(cls._agents.values())
    
    @classmethod
    def agent_count(cls):
        return len(cls._agents)
    