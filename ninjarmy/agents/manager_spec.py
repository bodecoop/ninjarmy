from pydantic import BaseModel

class ManagerSpec(BaseModel):
    id: int
    name: str
    role: str
    model: str
    task: str
    output_schema: dict

# Core Loop

# Recieve goal

# Plan

# 'Hire' Agents

# Get outputs

# Synthesize results, decide on next action