# ninjarmy/cli/main.py
import click
from ninjarmy.core.registry import AgentRegistry
from ninjarmy.core.manager import ManagerAgent
from ninjarmy.core.model import is_session_active, end_session
from ninjarmy.cli.agent_cli import agents
from rich.traceback import install
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
    ManagerAgent.get().run_repl()

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


cli.add_command(agents)

if __name__ == "__main__":
    cli()
