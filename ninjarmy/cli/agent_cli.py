# ninjarmy/cli/agents.py

import click
import yaml
from pathlib import Path
import ninjarmy
from ninjarmy.core.manager import ManagerAgent
from ninjarmy.core.registry import AgentRegistry
from ninjarmy.agents.agent_spec import AgentSpec, AgentCreateSpec

AGENTS_YAML = (Path(ninjarmy.__file__).parent/"agents"/"agents.yaml")

with open(AGENTS_YAML) as f:
    agents_list = yaml.load(f, Loader=yaml.SafeLoader)

@click.group()
def agents():
    """Manage AI agents"""
    pass

@agents.command()
@click.option("--name", required=True, help="Agent name")
@click.option(
    "--role",
    required=True,
    type=click.Choice(agents_list['agents']),
    help=f"Chose from this list of roles{agents_list['agents']}"
)
@click.option("--task", required=False, help="Task description")
def start(name, role, task):
    """Startup a new agent"""
    manager = ManagerAgent.get()
    agent = manager.hire_agent(spec=AgentCreateSpec(
        name=name,
        role=role,
        task=task
    ))
    click.echo(f"Starting '{name}' with id: {agent.get_id():04d}...")

@agents.command()
@click.option("--id", required=True, default=None, help="Agent ID")
def stop(id):
    "Stop an agent running"
    agent = AgentRegistry.get(id)
    if not agent:
        click.echo(f"No agent exists with id: {id}")
    # agent.stop()
    AgentRegistry.unregister(id)

@agents.command()
def list():
    """List running agents."""
    print(AgentRegistry.agent_count())

# agent kill
# agent update
# agent logs