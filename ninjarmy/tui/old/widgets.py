from __future__ import annotations

import asyncio
from datetime import datetime

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Label, RichLog

from ninjarmy.core.agent import Agent, AgentMessage


class AgentPanel(Widget):
    def __init__(self, agent: Agent, **kwargs) -> None:
        super().__init__(**kwargs)
        self.agent = agent

    def compose(self) -> ComposeResult:
        status = "[green]RUN[/green]" if self.agent.status == "running" else "[red]STP[/red]"
        yield Label(f" {self.agent.name}  ·  {self.agent.role}  ·  {status}", classes="panel-header")
        yield RichLog(wrap=True, markup=True)

    def on_mount(self) -> None:
        self.set_interval(0.1, self._drain_queue)

    def _drain_queue(self) -> None:
        log = self.query_one(RichLog)
        while True:
            try:
                msg: AgentMessage = self.agent.output_queue.get_nowait()
                ts = msg.timestamp.strftime("%H:%M:%S")
                if msg.type == "tool_call":
                    log.write(f"[dim]{ts}[/dim] [yellow]▶ {msg.content}[/yellow]")
                elif msg.type == "tool_result":
                    log.write(f"[dim]{ts}[/dim] [cyan]  ↳ {msg.content}[/cyan]")
                elif msg.type == "system":
                    log.write(f"[dim]{ts}[/dim] [bold]{msg.content}[/bold]")
                else:
                    log.write(f"[dim]{ts}[/dim] {msg.content}")
            except asyncio.QueueEmpty:
                break


class ManagerPanel(Widget):
    def compose(self) -> ComposeResult:
        yield Label(" MANAGER", classes="panel-header")
        yield RichLog(wrap=True, markup=True)

    def log_event(self, message: str) -> None:
        log = self.query_one(RichLog)
        ts = datetime.now().strftime("%H:%M:%S")
        log.write(f"[dim]{ts}[/dim] {message}")
