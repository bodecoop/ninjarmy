# ninjarmy/cli/agents.py

import click
import yaml
from pathlib import Path
import ninjarmy
from ninjarmy.core.manager import ManagerAgent
from ninjarmy.core.registry import AgentRegistry
from ninjarmy.core.model import is_session_active
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
    help=f"Chose from this list of roles {agents_list['agents']}"
)
@click.option("--task", required=False, default="", help="Task description")
def start(name, role, task):
    """Startup a new agent"""
    if not is_session_active():
        click.echo("No active session. Run 'ninjarmy boot' first.")
        return
    manager = ManagerAgent.get()
    if role not in agents_list['agents']:
        click.echo(f"ERROR: role - {role} does not exist in agents list:\n{agents_list['agents']}")
        return
    try:
        agent = manager.hire_agent(spec=AgentCreateSpec(
            name=name,
            role=role,
            task=task
        ))
    except (ValueError, RuntimeError) as e:
        click.echo(f"ERROR: {e}")
        return
    click.echo(f"Starting '{name}' with id: {agent.get_id():04d}...")

@agents.command()
@click.option("--id", required=True, default=None, help="Agent ID")
def stop(id):
    "Stop an agent running"
    agent_id = int(id)
    agent = AgentRegistry.get(agent_id)
    if not agent:
        click.echo(f"No agent exists with id: {id}")
        return
    agent.stop()
    AgentRegistry.unregister(agent_id)
    click.echo(f"Stopped and removed agent {id}.")

@agents.command()
def list():
    """List running agents."""
    all_agents = AgentRegistry.all()
    if not all_agents:
        click.echo("No agents registered.")
        return
    click.echo(f"{'ID':<6} {'NAME':<16} {'ROLE':<14} {'STATUS':<10} TASK")
    click.echo("-" * 70)
    for a in all_agents:
        click.echo(f"{a.id:<6} {a.name:<16} {a.role:<14} {a.get_status():<10} {a.task}")

# agent kill
# agent update
# agent logs