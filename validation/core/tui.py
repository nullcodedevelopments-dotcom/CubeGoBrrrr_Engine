from __future__ import annotations

import math
import sys
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text


# ── palette ────────────────────────────────────────────────────────────────────
_C = {
    "bg":           "grey7",
    "panel_border": "grey23",
    "green":        "chartreuse3",
    "red":          "red1",
    "yellow":       "yellow1",
    "cyan":         "bright_cyan",
    "blue":         "dodger_blue2",
    "magenta":      "medium_orchid1",
    "white":        "grey93",
    "dim":          "grey42",
    "header_bg":    "grey15",
}


# ══════════════════════════════════════════════════════════════════════════════
# ASCII Pie chart (block-character)
# ══════════════════════════════════════════════════════════════════════════════

def _render_pie(
    integrity:  float,
    failures:   float,
    warnings:   float,
    size:       int = 9,
) -> Text:
    """
    Render a pseudo-pie chart using Unicode braille / block characters.
    Returns a Rich Text object (multi-line).

    Three segments mapped to angles:
      integrity  → green  (starts at top, clockwise)
      warnings   → yellow
      failures   → red
    """
    diameter    = size * 2 + 1
    cx          = size
    cy          = size

    # Map percentages to radian spans
    total           = integrity + failures + warnings
    if total == 0:
        integrity = 100.0
    else:
        # normalise
        integrity   = (integrity / total) * 100
        failures    = (failures  / total) * 100
        warnings    = (warnings  / total) * 100

    def _angle(pct: float) -> float:
        return (pct / 100) * 2 * math.pi

    segments = [
        (_angle(integrity), _C["green"]),
        (_angle(warnings),  _C["yellow"]),
        (_angle(failures),  _C["red"]),
    ]

    # Build pixel grid  (2 rows per terminal row → use half-block ▀)
    grid: List[List[int]] = [[0] * (diameter) for _ in range(diameter)]

    start_angle = -math.pi / 2  # 12 o'clock

    for seg_idx, (span, _color) in enumerate(segments, start=1):
        end_angle   = start_angle + span
        steps       = max(360, int(span * 180 / math.pi * 2))
        for step in range(steps):
            theta   = start_angle + span * step / steps
            for r in range(1, size + 1):
                px = int(cx + r * math.cos(theta) + 0.5)
                py = int(cy + r * math.sin(theta) + 0.5)
                if 0 <= px < diameter and 0 <= py < diameter:
                    grid[py][px] = seg_idx
        start_angle = end_angle

    # Convert grid to Rich Text using half-block characters
    # Two rows per output line: top = upper half, bottom = lower half
    color_map = ["", _C["green"], _C["yellow"], _C["red"]]
    result = Text()

    for row in range(0, diameter - 1, 2):
        for col in range(diameter):
            top_seg = grid[row][col]
            bot_seg = grid[row + 1][col] if row + 1 < diameter else 0

            if top_seg == 0 and bot_seg == 0:
                result.append(" ")
            elif top_seg == bot_seg:
                result.append("█", style=Style(color=color_map[top_seg]))
            elif top_seg != 0 and bot_seg == 0:
                result.append("▀", style=Style(color=color_map[top_seg]))
            elif top_seg == 0 and bot_seg != 0:
                result.append("▄", style=Style(color=color_map[bot_seg]))
            else:
                result.append("▀", style=Style(color=color_map[top_seg], bgcolor=color_map[bot_seg]))
        result.append("\n")

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Terminal log panel (scrolling)
# ══════════════════════════════════════════════════════════════════════════════

class TerminalPanel:
    """Ring-buffer terminal log displayed inside the TUI."""

    MAX_LINES = 200

    def __init__(self) -> None:
        self._lines:    List[Text]  = []
        self._lock:     threading.Lock = threading.Lock()

    def append(self, line: Text | str) -> None:
        with self._lock:
            if isinstance(line, str):
                line = Text(line)
            self._lines.append(line)
            if len(self._lines) > self.MAX_LINES:
                self._lines = self._lines[-self.MAX_LINES:]

    def tail(self, n: int = 18) -> Text:
        with self._lock:
            visible = self._lines[-n:]
        out = Text()
        for ln in visible:
            out.append_text(ln)
            out.append("\n")
        return out


# ══════════════════════════════════════════════════════════════════════════════
# Main TUI
# ══════════════════════════════════════════════════════════════════════════════

class ValidationTUI:
    """
    Full-screen Rich TUI for the .validation scan.

    Layout:
    ┌─────────────────────────────────────────────────────────┐
    │                      HEADER                             │
    ├──────────────────────┬──────────────────────────────────┤
    │   PIE CHART          │  METRICS (integrity / fail / warn│
    ├──────────────────────┴──────────────────────────────────┤
    │                  PROGRESS BAR                           │
    ├─────────────────────────────────────────────────────────┤
    │              TERMINAL / LOG OUTPUT                      │
    ├─────────────────────────────────────────────────────────┤
    │               ISSUES TABLE                              │
    └─────────────────────────────────────────────────────────┘
    """

    REFRESH_RATE = 12  # fps

    def __init__(self, console: Optional[Console] = None) -> None:
        self._console       = console or Console()
        self._terminal      = TerminalPanel()
        self._live:         Optional[Live]      = None
        self._progress:     Optional[Progress]  = None
        self._task_id:      Optional[TaskID]    = None
        self._lock          = threading.Lock()

        # Scan state
        self._total_files   = 0
        self._done_files    = 0
        self._current_file  = Path("—")
        self._integrity     = 100.0
        self._failures      = 0.0
        self._warned        = 0.0
        self._error_count   = 0
        self._warn_count    = 0
        self._issues_rows:  List[Tuple[str, str, str, str, str]] = []
        self._scan_done     = False
        self._log_path:     Optional[Path] = None

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def start(self, total_files: int) -> None:
        self._total_files   = total_files
        self._progress      = self._make_progress()
        self._task_id       = self._progress.add_task(
            "[cyan]Scanning…",
            total=total_files,
        )
        self._live = Live(
            self._build_layout(),
            console=self._console,
            refresh_per_second=self.REFRESH_RATE,
            screen=True,
        )
        self._live.start()

    def stop(self) -> None:
        if self._live:
            self._live.stop()

    # ── update hooks (called from scanner thread) ──────────────────────────────

    def update_progress(self, done: int, total: int, current_file: Path) -> None:
        with self._lock:
            self._done_files    = done
            self._total_files   = total
            self._current_file  = current_file
        if self._progress and self._task_id is not None:
            self._progress.update(
                self._task_id,
                completed=done,
                description=f"[cyan]Scanning[/]  [dim]{current_file.name}[/]",
            )
        self._refresh()

    def update_metrics(
        self,
        integrity:      float,
        failure_pct:    float,
        warning_pct:    float,
        error_count:    int,
        warn_count:     int,
    ) -> None:
        with self._lock:
            self._integrity     = integrity
            self._failures      = failure_pct
            self._warned        = warning_pct
            self._error_count   = error_count
            self._warn_count    = warn_count
        self._refresh()

    def add_issue(
        self,
        file_path:  Path,
        line:       int,
        severity:   str,
        rule:       str,
        message:    str,
    ) -> None:
        sev_colors = {
            "ERROR":   _C["red"],
            "WARNING": _C["yellow"],
            "INFO":    _C["cyan"],
        }
        color = sev_colors.get(severity, _C["white"])
        row = (
            str(file_path.name),
            str(line),
            severity,
            rule,
            message[:72],
        )
        with self._lock:
            self._issues_rows.append(row)
            if len(self._issues_rows) > 100:
                self._issues_rows = self._issues_rows[-100:]

        self._terminal.append(
            Text.assemble(
                (f" {'E' if severity == 'ERROR' else 'W' if severity == 'WARNING' else 'I'} ", Style(color=color, bold=True)),
                (f" {file_path.name}:{line} ", Style(color=_C["dim"])),
                (f" {rule} ", Style(color=_C["magenta"])),
                (message[:60], Style(color=_C["white"])),
            )
        )
        self._refresh()

    def log_line(self, text: str | Text) -> None:
        self._terminal.append(text)
        self._refresh()

    def finish(self, log_path: Optional[Path] = None) -> None:
        with self._lock:
            self._scan_done = True
            self._log_path  = log_path
        if self._progress and self._task_id is not None:
            self._progress.update(
                self._task_id,
                description="[green]✓ Scan complete[/]",
                completed=self._total_files,
            )
        self._refresh()

    # ── layout builders ────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        if self._live:
            self._live.update(self._build_layout())

    def _make_progress(self) -> Progress:
        return Progress(
            SpinnerColumn(spinner_name="dots", style=_C["cyan"]),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(
                bar_width=None,
                style=Style(color=_C["blue"]),
                complete_style=Style(color=_C["green"]),
                finished_style=Style(color=_C["green"]),
            ),
            MofNCompleteColumn(),
            TextColumn("[dim]{task.percentage:>3.0f}%[/]"),
            TimeElapsedColumn(),
            console=self._console,
        )

    def _build_header(self) -> Panel:
        title = Text.assemble(
            ("  ◈  ", Style(color=_C["cyan"], bold=True)),
            (".VALIDATION", Style(color=_C["white"], bold=True)),
            ("  —  ", Style(color=_C["dim"])),
            ("codebase integrity scanner", Style(color=_C["dim"])),
            ("  ◈  ", Style(color=_C["cyan"], bold=True)),
        )
        return Panel(
            Align.center(title),
            style=Style(bgcolor=_C["header_bg"]),
            border_style=_C["panel_border"],
            padding=(0, 1),
        )

    def _build_pie_panel(self) -> Panel:
        with self._lock:
            integrity   = self._integrity
            failures    = self._failures
            warned      = self._warned

        pie = _render_pie(integrity, failures, warned, size=7)

        legend = Text()
        legend.append("\n")
        legend.append("  ██ ", Style(color=_C["green"]))
        legend.append(f"Integrity   {integrity:.1f}%\n", Style(color=_C["white"]))
        legend.append("  ██ ", Style(color=_C["red"]))
        legend.append(f"Failures    {failures:.1f}%\n", Style(color=_C["white"]))
        legend.append("  ██ ", Style(color=_C["yellow"]))
        legend.append(f"Look Into   {warned:.1f}%\n", Style(color=_C["white"]))

        content = Group(Align.center(pie), legend)
        return Panel(
            content,
            title="[bold]Pie Chart[/]",
            border_style=_C["panel_border"],
            padding=(0, 1),
        )

    def _build_metrics_panel(self) -> Panel:
        with self._lock:
            done        = self._done_files
            total       = self._total_files
            errors      = self._error_count
            warns       = self._warn_count
            integrity   = self._integrity
            done_flag   = self._scan_done
            log_path    = self._log_path

        t = Table.grid(padding=(0, 2))
        t.add_column(style="bold " + _C["dim"],  min_width=16)
        t.add_column(style=_C["white"],          min_width=12)

        bar_len     = 22
        filled      = int(integrity / 100 * bar_len)
        bar_fg      = _C["green"] if integrity >= 80 else (_C["yellow"] if integrity >= 50 else _C["red"])
        bar_text    = Text()
        bar_text.append("█" * filled, Style(color=bar_fg))
        bar_text.append("░" * (bar_len - filled), Style(color=_C["dim"]))

        t.add_row("Integrity",     bar_text)
        t.add_row("Files Scanned", Text(f"{done} / {total}", style=_C["cyan"]))
        t.add_row("Errors",        Text(str(errors), style=_C["red"] if errors else _C["green"]))
        t.add_row("Warnings",      Text(str(warns),  style=_C["yellow"] if warns else _C["green"]))
        t.add_row(
            "Status",
            Text("✓ DONE" if done_flag else "⟳ RUNNING",
                 style=_C["green"] if done_flag else _C["cyan"]),
        )
        if log_path:
            t.add_row("Log Saved", Text(str(log_path), style=_C["dim"]))

        return Panel(
            t,
            title="[bold]Metrics[/]",
            border_style=_C["panel_border"],
            padding=(0, 1),
        )

    def _build_progress_panel(self) -> Panel:
        assert self._progress is not None
        return Panel(
            self._progress,
            title="[bold]Progress[/]",
            border_style=_C["panel_border"],
            padding=(0, 1),
        )

    def _build_terminal_panel(self) -> Panel:
        content = self._terminal.tail(16)
        return Panel(
            content,
            title="[bold]Terminal Output[/]",
            border_style=_C["panel_border"],
            padding=(0, 1),
            height=20,
        )

    def _build_issues_table(self) -> Panel:
        with self._lock:
            rows = list(self._issues_rows[-20:])

        t = Table(
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold " + _C["cyan"],
            border_style=_C["dim"],
            expand=True,
        )
        t.add_column("File",        style=_C["white"],   max_width=24, no_wrap=True)
        t.add_column("Line",        style=_C["dim"],     max_width=6,  justify="right")
        t.add_column("Severity",    max_width=9)
        t.add_column("Rule",        style=_C["magenta"], max_width=32, no_wrap=True)
        t.add_column("Message",     style=_C["white"])

        for fname, line, sev, rule, msg in rows:
            sev_colors = {"ERROR": _C["red"], "WARNING": _C["yellow"], "INFO": _C["cyan"]}
            sev_text   = Text(sev, style=Style(color=sev_colors.get(sev, _C["white"]), bold=True))
            t.add_row(fname, line, sev_text, rule, msg)

        return Panel(
            t,
            title="[bold]Issues[/] [dim](last 20)[/]",
            border_style=_C["panel_border"],
            padding=(0, 0),
        )

    def _build_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header",   size=3),
            Layout(name="top",      size=13),
            Layout(name="progress", size=5),
            Layout(name="terminal", size=20),
            Layout(name="issues"),
        )
        layout["top"].split_row(
            Layout(name="pie",     ratio=2),
            Layout(name="metrics", ratio=3),
        )
        layout["header"].update(self._build_header())
        layout["pie"].update(self._build_pie_panel())
        layout["metrics"].update(self._build_metrics_panel())
        layout["progress"].update(self._build_progress_panel())
        layout["terminal"].update(self._build_terminal_panel())
        layout["issues"].update(self._build_issues_table())

        return layout
