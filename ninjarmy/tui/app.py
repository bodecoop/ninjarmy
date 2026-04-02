import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import HorizontalScroll, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, Input, RichLog
from rich.markdown import Markdown
from rich.text import Text
from textual.widget import Widget


def _render_tool_call(content: str) -> Text:
    """Format a tool call like: ⏺ tool_name(args)"""
    if "(" in content:
        name, rest = content.split("(", 1)
        args = rest.rstrip(")")
    else:
        name, args = content, ""
    t = Text()
    t.append("  ⏺ ", style="bold #00d4ff")
    t.append(name, style="bold #e0e0e0")
    t.append(f"({args})", style="#555555")
    return t


def _render_tool_result(content: str) -> Text:
    """Format a tool result like: ↳ {result} (truncated)"""
    preview = content if len(content) <= 120 else content[:120] + "…"
    t = Text()
    t.append("  ↳ ", style="#444444")
    t.append(preview, style="#555555")
    return t

from ninjarmy.core import context, model
from ninjarmy.core.agent import Agent
from ninjarmy.core.manager import ManagerAgent
from ninjarmy.core.registry import AgentRegistry



class ProjectSetupScreen(ModalScreen):
    """Modal screen shown on first boot to collect project name and description."""

    BINDINGS = [("enter", "submit", "Create Project")]

    def __init__(self, name = None, id = None, classes = None, manager: ManagerAgent = None):
        super().__init__(name, id, classes)
        self.manager = manager


    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("New Project", classes="dialog-title")
            yield Label("Project Name")
            yield Input(placeholder="my-project", id="name-input")
            yield Label("Description")
            yield Input(placeholder="What is this project?", id="desc-input")
            yield Label("", id="error-msg")
            yield Button("Create Project", variant="primary", id="submit-btn")

    def on_mount(self) -> None:
        self.query_one("#name-input", Input).focus()

    def action_submit(self) -> None:
        name = self.query_one("#name-input", Input).value.strip()
        desc = self.query_one("#desc-input", Input).value.strip()
        error = self.query_one("#error-msg", Label)
        if not name:
            error.update("Project name is required.")
            return
        context_path = model.STATE_PATH / f"{name}_project_context.md"
        context_path.write_text(desc, encoding="utf-8")
        model.start_session(name=name)
        self.dismiss({"name": name, "description": desc})

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            self.action_submit()


class AgentWidget(Widget):
    """A agent widget."""
    streaming_mode: bool = False

    def __init__(self, agent: Agent, **kwargs) -> None:
        super().__init__(**kwargs)
        self.agent = agent

    def compose(self) -> ComposeResult:
        """Create agent display."""
        yield Label(f"{self.agent.name}", classes="panel-header")
        yield Label(f"{self.agent.role}", classes="panel-subheader")
        yield RichLog(wrap=True, auto_scroll=True, markup=True)

    def on_mount(self) -> None:
        self.run_worker(self.agent.run(), exclusive=False)
        self.run_worker(self._drain_output(), exclusive=False)

    async def _drain_output(self) -> None:
        log = self.query_one(RichLog)
        buffer = ""
        while True:
            try:
                msg = await asyncio.wait_for(self.agent.output_queue.get(), timeout=0.5)
                if msg.type == "log":
                    buffer += msg.content
                    if self.streaming_mode:
                        log.write(buffer)
                        buffer = ""
                elif msg.type == "tool_call":
                    if buffer:
                        log.write(Markdown(buffer))
                        buffer = ""
                    log.write(_render_tool_call(msg.content))
                elif msg.type == "tool_result":
                    log.write(_render_tool_result(msg.content))
            except asyncio.TimeoutError:
                if buffer:
                    log.write(Markdown(buffer))
                    buffer = ""

class ManagerWidget(Widget):
    streaming_mode: bool = False

    def __init__(self, manager: ManagerAgent, **kwargs) -> None:
        super().__init__(**kwargs)
        self.manager = manager

    def compose(self) -> ComposeResult:
        yield Label("Manager", classes="panel-header")
        yield RichLog(id="manager-log", wrap=True, auto_scroll=True, markup=True)

    def on_mount(self) -> None:
        self.run_worker(self._drain_output(), exclusive=False)

    async def _drain_output(self) -> None:
        log = self.query_one("#manager-log", RichLog)
        buffer = ""
        while True:
            try:
                msg = await asyncio.wait_for(self.manager.output_queue.get(), timeout=0.5)
                if msg.type == "log":
                    buffer += msg.content
                    if self.streaming_mode:
                        log.write(buffer)
                        buffer = ""
                elif msg.type == "tool_call":
                    if buffer:
                        log.write(Markdown(buffer))
                        buffer = ""
                    log.write(_render_tool_call(msg.content))
                elif msg.type == "tool_result":
                    log.write(_render_tool_result(msg.content))
            except asyncio.TimeoutError:
                if buffer:
                    log.write(Markdown(buffer))
                    buffer = ""


class NinjarmyApp(App):
    """A Textual app to manage stopwatches."""

    CSS_PATH = Path(__file__).parent / "style.tcss"
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("ctrl+c", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self.manager = ManagerAgent.get()
        self.agents = AgentRegistry.all()

    def compose(self) -> ComposeResult:
        yield Header(name=self.manager.project_name)
        yield Horizontal(
            ManagerWidget(self.manager),
            HorizontalScroll(*[AgentWidget(a) for a in self.agents], id="agent-scroll")
        )
        yield Input(placeholder="Message the manager...", id="msg-input")
        # yield Footer()

    def on_mount(self) -> None:
        if not model.is_session_active():
            self.push_screen(ProjectSetupScreen(manager=self.manager), self._on_project_created)
        else:
            session = model.load_session()
            self.manager.project_name = session["name"]
            self.manager.system_prompt = self.manager.build_system_prompt()
            self.run_worker(self.manager.run(), exclusive=False)
        self.set_focus(self.query_one("#msg-input", Input))
        if not self.agents:
            self.query_one("#agent-scroll").display = False

    def _on_project_created(self, result: dict) -> None:
        self.manager.project_name = result["name"]
        self.manager.system_prompt = self.manager.build_system_prompt()
        self.run_worker(self.manager.run(), exclusive=False)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "msg-input":
            return
        msg = event.value.strip()
        if not msg:
            return
        event.input.clear()

        parts = msg.split()
        log = self.query_one("#manager-log", RichLog)

        log.write(f"[bold #f0a500]user$[/bold #f0a500] [#f0a500]{msg}[/#f0a500]")

        if parts[0] == "/agents":
            agents = AgentRegistry.all()
            if not agents:
                log.write("No agents hired.")
            else:
                for a in agents:
                    log.write(f"[{a.id}] {a.name} ({a.role}) — {a.task}")

        elif parts[0] == "/hire":
            if len(parts) != 4:
                log.write("Usage: /hire <name> <role> <task>")
            else:
                _, name, role, task = parts
                agent = self.manager.hire_agent(name=name, role=role, task=task)
                log.write(f"Hired {name} as {role} — {task}")
                scroll = self.query_one("#agent-scroll", HorizontalScroll)
                scroll.display = True
                scroll.mount(AgentWidget(agent))

        elif parts[0].startswith("/"):
            agent_name = parts[0][1:]
            agent = next((a for a in AgentRegistry.all() if a.name == agent_name), None)
            if agent:
                prompt_text = " ".join(parts[1:])
                if not prompt_text:
                    log.write(f"[#ff5555]Usage: /{agent_name} <prompt>[/#ff5555]")
                else:
                    agent.prompt(prompt_text)
                    log.write(f"[#555555]→ {agent_name}: {prompt_text}[/#555555]")
            else:
                log.write(f"[#ff5555]Unknown command or agent: {parts[0]}[/#ff5555]")

        else:
            self.manager.send_message(msg)


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