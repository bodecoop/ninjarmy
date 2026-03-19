import asyncio
from pathlib import Path

import ninjarmy
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, HorizontalScroll, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, Input, RichLog
from textual.widget import Widget

from ninjarmy.core import context, model
from ninjarmy.core.agent import Agent
from ninjarmy.core.manager import ManagerAgent
from ninjarmy.core.registry import AgentRegistry

STATE_PATH = Path(ninjarmy.__file__).parent / "state"


class ProjectSetupScreen(ModalScreen):
    """Modal screen shown on first boot to collect project name and description."""

    BINDINGS = [("enter", "submit", "Create Project")]

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("New Project", classes="dialog-title")
            yield Label("Project Name")
            yield Input(placeholder="my-project", id="name-input")
            yield Label("Description")
            yield Input(placeholder="What is this project?", id="desc-input")
            yield Label("", id="error-msg")
            yield Button("Create Project", variant="primary", id="submit-btn")

    def action_submit(self) -> None:
        name = self.query_one("#name-input", Input).value.strip()
        desc = self.query_one("#desc-input", Input).value.strip()
        error = self.query_one("#error-msg", Label)
        if not name:
            error.update("Project name is required.")
            return
        context_path = STATE_PATH / f"{name}_project_context.md"
        context_path.write_text(desc, encoding="utf-8")
        model.start_session(name=name)
        self.dismiss({"name": name, "description": desc})

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            self.action_submit()


class AgentWidget(Widget):
    """A agent widget."""
    def __init__(self, agent: Agent, **kwargs) -> None:
        super().__init__(**kwargs)
        self.agent = agent

    def compose(self) -> ComposeResult:
        """Create agent display."""
        yield Label(f"{self.agent.get_name}", classes="panel-header")
        yield Label(f"{self.agent.get_id}", classes="panel-subheader")
        yield VerticalScroll()

class ManagerWidget(Widget):
    def __init__(self, manager: ManagerAgent, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = manager

    def compose(self) -> ComposeResult:
        yield Label("Manager", classes="panel-header")
        yield RichLog(id="manager-log", wrap=True)

    def on_mount(self) -> None:
        self.run_worker(self._drain_output(), exclusive=False)

    async def _drain_output(self) -> None:
        log = self.query_one("#manager-log", RichLog)
        while True:
            try:
                msg = self.manager.output_queue.get_nowait()
                log.write(msg.content)
            except asyncio.QueueEmpty:
                await asyncio.sleep(0.05)


class NinjarmyApp(App):
    """A Textual app to manage stopwatches."""

    # CSS_PATH = Path(__file__).parent / "style.tcss"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("ctrl+c", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self.manager = ManagerAgent.get()
        self.agents = AgentRegistry.all()

    def compose(self) -> ComposeResult:
        yield Header()
        yield ManagerWidget(self.manager)
        yield HorizontalScroll(*[AgentWidget(a) for a in self.agents])
        yield Input(placeholder="Message the manager...", id="msg-input")
        yield Footer()

    def on_mount(self) -> None:
        if not model.is_session_active():
            self.push_screen(ProjectSetupScreen(), self._on_project_created)
        else:
            self.run_worker(self.manager.run(), exclusive=False)

    def _on_project_created(self, result: dict) -> None:
        self.manager.project_name = result["name"]
        self.manager.system_prompt = self.manager.build_system_prompt()
        self.run_worker(self.manager.run(), exclusive=False)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value.strip():
            self.manager.send_message(event.value.strip())
            event.input.clear()


    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.theme = (
            "textual-dark" if self.theme == "textual-light" else "textual-light"
        )

    def action_quit(self) -> None:
        """An action to quit the app."""
        self.exit()

if __name__ == "__main__":
    app = NinjarmyApp()
    app.run()