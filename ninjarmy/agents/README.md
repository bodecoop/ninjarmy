# Agents — Role Definitions

This module defines the schema for agent specs and the YAML role templates that shape each agent's behavior.

## Key Files

| File | Responsibility |
|------|----------------|
| `agent_schema.py` | Pydantic models for `AgentSpec` and `ManagerSpec` |
| `agents.yaml` | Role prompt templates — one entry per agent role |

## Adding a New Role

Open `agents.yaml` and add a new entry under `roles:`:

```yaml
roles:
  your-role-name:
    prompt: |
      You are a [description]. Your job is to [specific responsibility].
      [Any constraints or focus areas...]
      Do only what was asked. Do not create documentation, reports, or extra files unless explicitly requested.
      When using tools, minimize commentary between calls. Act directly.
```

The last two lines are a convention across all roles — they keep agents focused and prevent token waste. Keep them.

Once added, the role is immediately available:

```
/hire myagent your-role-name Do the thing
```

## Built-in Roles

| Role | Focus |
|------|-------|
| `tester` | Write thorough pytest tests; focuses on edge cases and failure modes |
| `optimizer` | Profile and improve performance; targets complexity, I/O, allocations |
| `brute-force` | Get things working fast; correctness over elegance |
| `janitor` | Refactor and clean up without changing behavior |
| `architect` | Design systems; produces file structure and interface proposals |
| `custom` | General-purpose agent |

## AgentSpec Schema

```python
class AgentSpec(BaseModel):
    id: str          # unique agent ID
    name: str        # human-readable name (must be unique in registry)
    role: str        # must match a key in agents.yaml
    task: str        # task description passed to the agent
    model: str       # Claude model ID
```

If the role key doesn't exist in `agents.yaml`, the agent falls back to a generic `"{role} coding agent"` prompt.
