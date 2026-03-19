# ninjarmy/cli/main.py
import click
from ninjarmy.core.registry import AgentRegistry
from ninjarmy.core.manager import ManagerAgent
from ninjarmy.core.model import is_session_active, end_session, start_session
from ninjarmy.core.context import generate_project_context, save_context
from ninjarmy.cli.agent_cli import agents
from rich.traceback import install
from ninjarmy.tui.app import NinjarmyApp
install(show_locals=True)

@click.group()
@click.version_option("0.1.0")
def cli():
    """
    NinjArmy cli
    """
    pass

@cli.command()
def boot():
    """Start an interactive manager session."""
    if is_session_active():
        click.echo("Session already active. Run 'ninjarmy terminate' to shut down first.")
        return
    # project = input("Describe your project: ").strip()
    # start_session(project=project)
    # click.echo("Generating project context...")
    # context = generate_project_context(project)
    # save_context(context)
    click.echo("Launching TUI...")
    NinjarmyApp().run()

@cli.command()
def terminate():
    """Disconnects all agents and clears the session."""
    if not is_session_active():
        click.echo("No active session to terminate.")
        return
    AgentRegistry.hydrate()
    for agent in AgentRegistry.all():
        AgentRegistry.unregister(agent.get_id())
        click.echo(f"Shutting down {agent.get_name()} - id:{agent.get_id()}")
    end_session()
    click.echo("Session terminated.")

if __name__ == "__main__":
    cli()
