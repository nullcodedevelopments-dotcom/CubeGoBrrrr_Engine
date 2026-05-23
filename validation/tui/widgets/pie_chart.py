from __future__ import annotations
import math
from rich.align import Align
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from textual.reactive import reactive
from textual.widget import Widget
from ..theme import THEME

def _render_pie(integrity: float, failures: float, warnings: float, size: int = 7) -> Text:
    diameter = size * 2 + 1
    cx = cy = size
    total = integrity + failures + warnings
    if total == 0:
        integrity = 100.0; failures = 0.0; warnings = 0.0
    else:
        f = 100 / total
        integrity *= f; failures *= f; warnings *= f

    def _ang(pct: float) -> float:
        return (pct / 100) * 2 * math.pi

    segments = [(_ang(integrity), THEME["green"]), (_ang(warnings), THEME["yellow"]), (_ang(failures), THEME["red"])]
    grid = [[0] * diameter for _ in range(diameter)]
    start = -math.pi / 2
    for seg_idx, (span, _) in enumerate(segments, 1):
        steps = max(360, int(span * 180 / math.pi * 2))
        for step in range(steps):
            theta = start + span * step / max(steps, 1)
            for r in range(1, size + 1):
                px = int(cx + r * math.cos(theta) + 0.5)
                py = int(cy + r * math.sin(theta) + 0.5)
                if 0 <= px < diameter and 0 <= py < diameter:
                    grid[py][px] = seg_idx
        start += span

    color_map = ["", THEME["green"], THEME["yellow"], THEME["red"]]
    result = Text()
    for row in range(0, diameter - 1, 2):
        for col in range(diameter):
            top = grid[row][col]
            bot = grid[row + 1][col] if row + 1 < diameter else 0
            if top == 0 and bot == 0:
                result.append(" ")
            elif top == bot:
                result.append("█", style=Style(color=color_map[top]))
            elif top != 0 and bot == 0:
                result.append("▀", style=Style(color=color_map[top]))
            elif top == 0 and bot != 0:
                result.append("▄", style=Style(color=color_map[bot]))
            else:
                result.append("▀", style=Style(color=color_map[top], bgcolor=color_map[bot]))
        result.append("\n")
    return result

class PieChartWidget(Widget):
    DEFAULT_CSS = "PieChartWidget { width: 35%; height: 100%; border: round #333333; background: #1a1a1a; padding: 1 2; }"
    integrity: reactive[float] = reactive(100.0)
    failures:  reactive[float] = reactive(0.0)
    warnings:  reactive[float] = reactive(0.0)

    def render(self):
        pie = _render_pie(self.integrity, self.failures, self.warnings, size=6)
        legend = Text("\n")
        legend.append("  ██ ", Style(color=THEME["green"]))
        legend.append(f"Integrity  {self.integrity:.1f}%\n", THEME["white"])
        legend.append("  ██ ", Style(color=THEME["red"]))
        legend.append(f"Failures   {self.failures:.1f}%\n", THEME["white"])
        legend.append("  ██ ", Style(color=THEME["yellow"]))
        legend.append(f"Look Into  {self.warnings:.1f}%\n", THEME["white"])
        from rich.console import Group
        return Panel(Group(Align.center(pie), legend), title="[bold cyan]Codebase Health[/]", border_style=THEME["border"])

    def update(self, integrity: float, failures: float, warnings: float) -> None:
        self.integrity = integrity; self.failures = failures; self.warnings = warnings
