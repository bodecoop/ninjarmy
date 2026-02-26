# ninjarmy/cli/main.py
import click
from ninjarmy.core.registry import AgentRegistry
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
    """Creates a manager agent"""
    AgentRegistry.hydrate()
    click.echo("Booting up a new session...")

cli.add_command(agents)

if __name__ == "__main__":
    cli()
