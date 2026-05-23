from __future__ import annotations
from rich.table import Table
from rich.text import Text
from textual.reactive import reactive
from textual.widget import Widget
from ..theme import THEME

class MetricsBar(Widget):
    DEFAULT_CSS = "MetricsBar { height: 3; dock: top; background: #0d0d0d; border-bottom: solid #333333; padding: 0 2; }"
    integrity:  reactive[float] = reactive(100.0)
    errors:     reactive[int]   = reactive(0)
    warnings:   reactive[int]   = reactive(0)
    files:      reactive[int]   = reactive(0)
    scanned:    reactive[int]   = reactive(0)
    duration_s: reactive[float] = reactive(0.0)
    status:     reactive[str]   = reactive("IDLE")

    def render(self):
        bar_len   = 24
        filled    = int(self.integrity / 100 * bar_len)
        bar_color = THEME["green"] if self.integrity >= 80 else THEME["yellow"] if self.integrity >= 50 else THEME["red"]
        bar = Text("█" * filled, style=bar_color) + Text("░" * (bar_len - filled), style=THEME["dim"])
        pct = Text(f" {self.integrity:.1f}%", style=f"bold {bar_color}")
        e_color = THEME["red"]    if self.errors   else THEME["green"]
        w_color = THEME["yellow"] if self.warnings  else THEME["green"]
        status_color = {"IDLE": THEME["dim"], "SCANNING": THEME["cyan"], "DONE": THEME["green"], "FAILED": THEME["red"]}.get(self.status, THEME["white"])
        t = Table.grid(padding=(0, 3), expand=True)
        for _ in range(6):
            t.add_column(ratio=1)
        t.add_row(
            Text.assemble(("Integrity ", THEME["dim"]), bar, pct),
            Text.assemble(("Files ",    THEME["dim"]), (f"{self.scanned}/{self.files}", THEME["cyan"])),
            Text.assemble(("Errors ",   THEME["dim"]), (str(self.errors),   f"bold {e_color}")),
            Text.assemble(("Warnings ", THEME["dim"]), (str(self.warnings), f"bold {w_color}")),
            Text.assemble(("Duration ", THEME["dim"]), (f"{self.duration_s:.1f}s", THEME["white"])),
            Text(self.status, style=f"bold {status_color}"),
        )
        return t

    def update_metrics(self, integrity: float, errors: int, warnings: int, files: int, scanned: int, duration_s: float, status: str) -> None:
        self.integrity = integrity; self.errors = errors; self.warnings = warnings
        self.files = files; self.scanned = scanned; self.duration_s = duration_s; self.status = status
