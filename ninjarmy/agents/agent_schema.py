from pydantic import BaseModel, field_validator

class AgentSpec(BaseModel):
    id: int
    name: str
    role: str
    task: str = ""
    model: str

class ManagerSpec(BaseModel):
    model: str = "claude-haiku-4-5"