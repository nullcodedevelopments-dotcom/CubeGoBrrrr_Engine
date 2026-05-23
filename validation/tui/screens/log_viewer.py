from __future__ import annotations
import re
from pathlib import Path
from typing import List, Optional, Tuple
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, ListItem, ListView, RichLog, Static
from ..theme import THEME

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(s: str) -> str:
    return _ANSI_RE.sub("", s)


def _parse_log_summary(path: Path) -> Tuple[int, int, int]:
    """Return (errors, warnings, files) from last 30 lines of a log."""
    e = w = f = 0
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[-30:]:
            clean = _strip_ansi(line)
            m = re.search(r"Errors:\s+(\d+)", clean)
            if m: e = int(m.group(1))
            m = re.search(r"Warnings:\s+(\d+)", clean)
            if m: w = int(m.group(1))
            m = re.search(r"Files:\s+(\d+)", clean)
            if m: f = int(m.group(1))
    except OSError:
        pass
    return e, w, f


class LogViewerScreen(Screen):
    BINDINGS = [
        Binding("d",      "app.switch_screen('dashboard')", "Dashboard", show=True),
        Binding("escape", "app.switch_screen('dashboard')", "Back",      show=True),
        Binding("ctrl+f", "focus_search",                   "Search",    show=True),
    ]

    def __init__(self, open_path: Optional[Path] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._open_path     = open_path
        self._current_path: Optional[Path] = None
        self._all_lines:    List[str] = []

    def compose(self) -> ComposeResult:
        with Horizontal(id="log-viewer-main"):
            with Vertical(id="log-list-pane"):
                yield Label("  Log Files", classes="label-accent")
                yield Static("─" * 24, classes="label-dim")
                yield ListView(id="log-list")
                with Horizontal(id="log-list-actions"):
                    yield Button("Delete", id="btn-delete", classes="btn-red")
                    yield Button("Copy", id="btn-copy-log", classes="btn-dim")
            with Vertical(id="log-viewer-pane"):
                yield Input(placeholder="Search log…", id="log-search")
                # Keep all lines so the user can view entire log files.
                yield RichLog(id="log-content", highlight=False, markup=False, max_lines=None)

    async def on_mount(self) -> None:
        await self._populate_list()
        if self._open_path:
            self._load_log(self._open_path)

    async def _populate_list(self) -> None:
        log_dir: Optional[Path] = getattr(self.app, "log_dir", None)
        lv = self.query_one("#log-list", ListView)
        await lv.clear()
        if not log_dir or not log_dir.is_dir():
            return
        logs = sorted(log_dir.glob("*.log"), reverse=True)
        for log_path in logs:
            e, w, f = _parse_log_summary(log_path)
            date_str = log_path.stem.replace("scan_", "").replace("_", " ", 1)
            e_style  = f"bold {THEME['red']}"    if e else f"bold {THEME['green']}"
            w_style  = f"bold {THEME['yellow']}" if w else f"bold {THEME['green']}"
            label_text = Text.assemble(
                (f"{date_str}  ", THEME["white"]),
                (f"E:{e} ", e_style),
                (f"W:{w}", w_style),
            )
            item = ListItem(Label(label_text))
            item._log_path = log_path  # type: ignore[attr-defined]
            lv.append(item)

    def _load_log(self, path: Path) -> None:
        self._current_path = path
        viewer = self.query_one("#log-content", RichLog)
        viewer.clear()
        try:
            self._all_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            viewer.write(Text("Could not read log file.", style="bold red"))
            return
        query = self.query_one("#log-search", Input).value.lower()
        self._render_lines(query)

    def _render_lines(self, query: str = "") -> None:
        viewer = self.query_one("#log-content", RichLog)
        viewer.clear()
        for raw_line in self._all_lines:
            if query and query not in _strip_ansi(raw_line).lower():
                continue
            try:
                viewer.write(Text.from_ansi(raw_line))
            except Exception:
                viewer.write(Text(raw_line))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        path = getattr(event.item, "_log_path", None)
        if path:
            self._load_log(path)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "log-search" and self._current_path:
            self._render_lines(event.value.lower())

    def action_focus_search(self) -> None:
        self.query_one("#log-search", Input).focus()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-delete" and self._current_path:
            try:
                self._current_path.unlink()
                self._current_path = None
                self.query_one("#log-content", RichLog).clear()
                await self._populate_list()
            except OSError:
                pass
        elif event.button.id == "btn-copy-log":
            if not self._current_path:
                self.app.notify("Select a log file first.", severity="warning")
                return
            text = "\n".join(self._all_lines)
            self.app.copy_to_clipboard(text)
            self.app.notify(f"Copied log: {self._current_path.name}", severity="information")
