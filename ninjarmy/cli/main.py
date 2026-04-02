# ninjarmy/cli/main.py
import click
from ninjarmy.core.registry import AgentRegistry
from ninjarmy.core.manager import ManagerAgent
from ninjarmy.core import model
from ninjarmy.core.model import is_session_active, end_session
from ninjarmy.core.context import generate_project_context, save_context
from ninjarmy.cli.agent_cli import agents
from rich.traceback import install
from ninjarmy.tui.app import NinjarmyApp
import os
install(show_locals=True)

@click.group()
@click.version_option("0.1.0")
def cli():
    """
    NinjArmy cli
    """
    pass

cli.add_command(agents)

@cli.command()
def boot():
    """Start an interactive manager session."""
    root = os.getcwd()
    model.init(root)
    ManagerAgent.get().set_working_dir(root)
    NinjarmyApp().run()

@cli.command()
def terminate():
    """Disconnects all agents and clears the session."""
    if not is_session_active():
        click.echo("No active session to terminate.")
        return
    AgentRegistry.hydrate()
    for agent in AgentRegistry.all():
        click.echo(f"Shutting down {agent.name} - id:{agent.id}")
        AgentRegistry.unregister(agent.id)
    end_session()
    click.echo("Session terminated.")

if __name__ == "__main__":
    cli()
