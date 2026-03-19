from __future__ import annotations

from pathlib import Path

import yaml

import ninjarmy
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Input, Label

from ninjarmy.agents.agent_spec import AgentCreateSpec
from ninjarmy.core.manager import ManagerAgent
from ninjarmy.core.model import end_session
from ninjarmy.core.registry import AgentRegistry
from ninjarmy.tui.widgets import AgentPanel, ManagerPanel

_AGENTS_YAML = Path(ninjarmy.__file__).parent / "agents" / "agents.yaml"

AGENTS_PER_PAGE = 3


class NinjArmyApp(App):
    CSS_PATH = Path(__file__).parent / "styles.tcss"

    BINDINGS = [
        Binding("ctrl+right", "next_page", "Next page", show=True),
        Binding("ctrl+left", "prev_page", "Prev page", show=True),
    ]

    def __init__(self, manager: ManagerAgent) -> None:
        super().__init__()
        self.manager = manager
        self._page = 0
        self._known_agent_ids: set[int] = set()
        with open(_AGENTS_YAML) as f:
            self._valid_roles: list[str] = yaml.safe_load(f)["agents"]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-area"):
            yield ManagerPanel(id="manager-panel")
            with Vertical(id="agent-area"):
                yield Label("", id="page-bar")
                with Horizontal(id="agent-grid"):
                    pass
        yield Input(
            placeholder="> msg  |  @agent msg  |  /hire name role [-- task]  |  /fire name  |  /roles  |  /next  |  /prev  |  /exit",
            id="prompt-bar",
        )

    async def on_mount(self) -> None:
        self.title = "NinjArmy"
        # self.sub_title = self.project
        panel = self.query_one(ManagerPanel)
        # panel.log_event(f"Session started · project: [bold]{self.project}[/bold]")
        panel.log_event(f"Roles: [dim]{', '.join(self._valid_roles)}[/dim]")
        await self._refresh_grid()
        self.set_interval(0.5, self._poll_agents)
        self.query_one("#prompt-bar", Input).focus()

    # ── Agent registry watcher ────────────────────────────────────

    async def _poll_agents(self) -> None:
        current_ids = {a.id for a in AgentRegistry.all()}
        if current_ids == self._known_agent_ids:
            return
        added = current_ids - self._known_agent_ids
        removed = self._known_agent_ids - current_ids
        panel = self.query_one(ManagerPanel)
        for aid in added:
            agent = AgentRegistry.get(aid)
            if agent:
                panel.log_event(f"[green]+ hired:[/green] {agent.name} ({agent.role})")
        for aid in removed:
            panel.log_event(f"[red]- fired:[/red] agent id {aid}")
        self._known_agent_ids = current_ids
        total = len(current_ids)
        max_page = max(0, (total - 1) // AGENTS_PER_PAGE) if total else 0
        if self._page > max_page:
            self._page = max_page
        await self._refresh_grid()

    # ── Grid rendering ────────────────────────────────────────────

    async def _refresh_grid(self) -> None:
        agents = AgentRegistry.all()
        total = len(agents)
        total_pages = max(1, -(-total // AGENTS_PER_PAGE))
        page_agents = agents[self._page * AGENTS_PER_PAGE: (self._page + 1) * AGENTS_PER_PAGE]

        page_bar = self.query_one("#page-bar", Label)
        if total == 0:
            page_bar.update("[dim]No agents · use /hire to add one[/dim]")
        else:
            tabs = "  ".join(
                f"[bold][{i + 1}][/bold]" if i == self._page else f"[dim][{i + 1}][/dim]"
                for i in range(total_pages)
            )
            page_bar.update(f" Page {self._page + 1}/{total_pages}  {tabs}  · ctrl+← / ctrl+→")

        grid = self.query_one("#agent-grid", Horizontal)
        await grid.remove_children()
        if page_agents:
            await grid.mount(*[AgentPanel(agent) for agent in page_agents])

    # ── Page navigation actions ───────────────────────────────────

    async def action_next_page(self) -> None:
        agents = AgentRegistry.all()
        total_pages = max(1, -(-len(agents) // AGENTS_PER_PAGE))
        if self._page < total_pages - 1:
            self._page += 1
            await self._refresh_grid()

    async def action_prev_page(self) -> None:
        if self._page > 0:
            self._page -= 1
            await self._refresh_grid()

    # ── Prompt input handler ──────────────────────────────────────

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.clear()
        panel = self.query_one(ManagerPanel)

        if text in ("/exit", "/quit"):
            panel.log_event("[yellow]Ending session…[/yellow]")
            end_session()
            self.exit()
        elif text == "/next":
            await self.action_next_page()
        elif text == "/prev":
            await self.action_prev_page()
        elif text.startswith("/hire"):
            await self._cmd_hire(text, panel)
        elif text.startswith("/fire"):
            await self._cmd_fire(text, panel)
        elif text == "/roles":
            panel.log_event(f"Roles: [dim]{', '.join(self._valid_roles)}[/dim]")
        elif text.startswith("@"):
            await self._cmd_mention(text, panel)
        else:
            agents = AgentRegistry.all()
            if not agents:
                panel.log_event("[yellow]No agents to broadcast to.[/yellow]")
            else:
                panel.log_event(f"[cyan]broadcast →[/cyan] {text}")
                for agent in agents:
                    await agent.inbox.put(text)

    # ── Slash command helpers ─────────────────────────────────────

    async def _cmd_hire(self, text: str, panel: ManagerPanel) -> None:
        parts = text.split(" -- ", maxsplit=1)
        task = parts[1].strip() if len(parts) > 1 else ""
        tokens = parts[0].split()
        if len(tokens) < 3:
            panel.log_event("[red]Usage: /hire name role [-- task][/red]")
            return
        name, role = tokens[1], tokens[2]
        if role not in self._valid_roles:
            panel.log_event(f"[red]Unknown role '{role}'. Valid: {', '.join(self._valid_roles)}[/red]")
            return
        try:
            agent = self.manager.hire_agent(AgentCreateSpec(name=name, role=role, task=task))
            panel.log_event(f"[green]Hired {agent.name} (id:{agent.id:04d}) as {role}[/green]")
        except (ValueError, RuntimeError) as e:
            panel.log_event(f"[red]Error: {e}[/red]")

    async def _cmd_fire(self, text: str, panel: ManagerPanel) -> None:
        tokens = text.split()
        if len(tokens) < 2:
            panel.log_event("[red]Usage: /fire name[/red]")
            return
        name = tokens[1]
        agent = next((a for a in AgentRegistry.all() if a.name == name), None)
        if agent is None:
            panel.log_event(f"[red]No agent named '{name}'.[/red]")
            return
        try:
            self.manager.fire_agent(agent.id)
            panel.log_event(f"[red]Fired {name}[/red]")
        except (ValueError, RuntimeError) as e:
            panel.log_event(f"[red]Error: {e}[/red]")

    async def _cmd_mention(self, text: str, panel: ManagerPanel) -> None:
        space_idx = text.find(" ")
        if space_idx == -1:
            panel.log_event("[red]Usage: @agentname message[/red]")
            return
        name = text[1:space_idx]
        message = text[space_idx + 1:].strip()
        agent = next((a for a in AgentRegistry.all() if a.name == name), None)
        if agent is None:
            panel.log_event(f"[red]No agent named '{name}'.[/red]")
            return
        panel.log_event(f"[cyan]→ {name}:[/cyan] {message}")
        await agent.inbox.put(message)
