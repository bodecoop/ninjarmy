from pydantic import BaseModel


class AgentCreateSpec(BaseModel):
    name: str
    role: str
    task: str

class AgentSpec(AgentCreateSpec):
    id: int