from ninjarmy.agents.agent_spec import AgentSpec

class Agent:
    def __init__(self, spec: AgentSpec):
        self.spec = spec
        self.id: int = spec.id
        self.name: str = spec.name
        self.role: str = spec.role
        self.task: str = spec.task
        self.status: str = "stopped"

    def stop(self):
        self.status = "stopped"

    def start(self):
        self.status = "running"

    def get_status(self) -> str:
        return self.status
    def get_id(self) -> int:
        return self.id