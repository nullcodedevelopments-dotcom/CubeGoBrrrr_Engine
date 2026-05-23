from __future__ import annotations
from typing import List, Optional
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Label, Static
from ...core.script_loader import ScriptMeta

class RunScriptRequest(Message):
    def __init__(self, meta: ScriptMeta) -> None:
        super().__init__()
        self.meta = meta

class ScriptPanel(Widget):
    DEFAULT_CSS = "ScriptPanel { border: round #333333; background: #1a1a1a; padding: 1; height: auto; max-height: 18; }"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._scripts: List[ScriptMeta] = []

    def compose(self) -> ComposeResult:
        yield Label("  Custom Scripts", classes="label-accent")
        yield Static("─" * 30, classes="label-dim")
        yield Vertical(id="script-buttons")

    async def load_scripts(self, scripts: List[ScriptMeta]) -> None:
        self._scripts = scripts
        container = self.query_one("#script-buttons", Vertical)
        await container.remove_children()
        if not scripts:
            await container.mount(Label("  No custom scripts found", classes="script-panel--empty"))
            return
        global_scripts  = [s for s in scripts if s.is_global]
        project_scripts = [s for s in scripts if not s.is_global]
        if global_scripts:
            await container.mount(Label("  Global", classes="script-panel--section-label"))
            for meta in global_scripts:
                btn = Button(f"▶  {meta.name}", classes="btn-dim")
                btn._script_meta = meta  # type: ignore[attr-defined]
                await container.mount(btn)
        if project_scripts:
            await container.mount(Label("  Project-local", classes="script-panel--section-label"))
            for meta in project_scripts:
                btn = Button(f"▶  {meta.name}", classes="btn-yellow")
                btn._script_meta = meta  # type: ignore[attr-defined]
                await container.mount(btn)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        meta = getattr(event.button, "_script_meta", None)
        if meta is not None:
            self.post_message(RunScriptRequest(meta))
