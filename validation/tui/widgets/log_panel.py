from __future__ import annotations
from rich.text import Text
from textual.widgets import RichLog
from ...core.models import ValidationIssue
from ..theme import THEME, severity_color

class LogPanel(RichLog):
    DEFAULT_CSS = "LogPanel { height: 1fr; border: round #333333; background: #0d0d0d; }"

    def __init__(self, **kwargs):
        super().__init__(max_lines=500, highlight=False, markup=False, **kwargs)

    def write_ansi(self, raw: str) -> None:
        for line in raw.splitlines():
            try:
                self.write(Text.from_ansi(line))
            except Exception:
                self.write(Text(line))

    def write_issue(self, issue: ValidationIssue) -> None:
        sev_color = severity_color(issue.severity.value)
        label     = f"[{issue.severity.value:<7}]"
        line_ref  = f"{issue.file_path.name}:{issue.line}"
        msg_line  = Text.assemble(
            (label,             f"bold {sev_color}"),
            (f" {line_ref} ",   THEME["dim"]),
            (f"[{issue.rule}] ",THEME["magenta"]),
            (issue.message,     THEME["white"]),
        )
        self.write(msg_line)
        if issue.suggested_fix:
            self.write(Text.assemble(("  ✦ Fix: ", THEME["green"]), (issue.suggested_fix, THEME["green"])))

    def write_section(self, title: str) -> None:
        self.write(Text("─" * 60, style=THEME["dim"]))
        self.write(Text(f"  {title}", style=f"bold {THEME['cyan']}"))
        self.write(Text("─" * 60, style=THEME["dim"]))

    def clear_and_reset(self) -> None:
        self.clear()
        self.write(Text(".VALIDATION  —  Terminal Output", style=f"bold {THEME['cyan']}"))
        self.write(Text("─" * 60, style=THEME["dim"]))
