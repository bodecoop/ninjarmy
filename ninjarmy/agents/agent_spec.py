from pydantic import BaseModel, field_validator


class AgentCreateSpec(BaseModel):
    name: str
    role: str
    task: str = ""

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Agent name must not be blank.")
        return v.strip()

class AgentSpec(AgentCreateSpec):
    id: int