from __future__ import annotations
from pathlib import Path
from typing import List, Optional
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, DataTable, Label, Static
from ..widgets.pie_chart import PieChartWidget
from ..widgets.metrics_bar import MetricsBar
from ..widgets.script_panel import ScriptPanel, RunScriptRequest
from ...core.models import ScanReport
from ...core.script_loader import ScriptMeta, ScriptLoader
from ..theme import THEME

class DashboardScreen(Screen):
    BINDINGS = [
        Binding("s", "app.run_scan",                 "Scan",     show=True),
        Binding("r", "app.switch_screen('results')", "Results",  show=True),
        Binding("l", "app.switch_screen('logs')",    "Log View", show=True),
    ]

    def compose(self) -> ComposeResult:
        yield MetricsBar(id="metrics-bar")
        with Horizontal(id="dash-main"):
            with Vertical(id="dash-left"):
                yield PieChartWidget(id="pie-chart")
                with Vertical(id="lang-buttons", classes="panel"):
                    yield Label("  Run Validators", classes="label-accent")
                    yield Static("─" * 26, classes="label-dim")
                    yield Button("⬡  Full Scan",   id="btn-all",  classes="btn-green")
                    yield Button("⬡  Python",       id="btn-py",   classes="btn-dim")
                    yield Button("⬡  JavaScript",   id="btn-js",   classes="btn-dim")
                    yield Button("⬡  CSS",          id="btn-css",  classes="btn-dim")
                    yield Button("⬡  HTML",         id="btn-html", classes="btn-dim")
            with Vertical(id="dash-right"):
                yield ScriptPanel(id="script-panel")
                with Vertical(id="recent-logs-panel", classes="panel"):
                    yield Label("  Recent Scans", classes="label-accent")
                    yield Static("─" * 26, classes="label-dim")
                    yield DataTable(id="recent-logs-table", show_cursor=True)

    async def on_mount(self) -> None:
        # Setup recent logs table
        tbl = self.query_one("#recent-logs-table", DataTable)
        tbl.add_columns("Date", "Files", "Errors", "Warnings")
        tbl.cursor_type = "row"

        await self._refresh_from_app_state()

    async def on_screen_resume(self) -> None:
        await self._refresh_from_app_state()

    async def _refresh_from_app_state(self) -> None:
        self._refresh_recent_logs()
        await self._refresh_scripts()

        # If we already have a report from a previous scan, populate metrics
        report: Optional[ScanReport] = getattr(self.app, "last_report", None)
        if report:
            self._apply_report(report)

    async def _refresh_scripts(self) -> None:
        loader: Optional[ScriptLoader] = getattr(self.app, "script_loader", None)
        if loader is None:
            return
        scripts: List[ScriptMeta] = loader.discover()
        await self.query_one("#script-panel", ScriptPanel).load_scripts(scripts)

    def _refresh_recent_logs(self) -> None:
        log_dir: Optional[Path] = getattr(self.app, "log_dir", None)
        tbl = self.query_one("#recent-logs-table", DataTable)
        tbl.clear()
        if not log_dir or not log_dir.is_dir():
            return
        logs = sorted(log_dir.glob("*.log"), reverse=True)[:8]
        for log_path in logs:
            e_count, w_count, file_count = _parse_log_summary(log_path)
            date_str = log_path.stem.replace("scan_", "").replace("_", " ", 1)
            from rich.text import Text
            from ..theme import THEME
            e_txt = Text(str(e_count), style=f"bold {THEME['red']}"    if e_count else f"bold {THEME['green']}")
            w_txt = Text(str(w_count), style=f"bold {THEME['yellow']}" if w_count else f"bold {THEME['green']}")
            tbl.add_row(date_str, str(file_count), e_txt, w_txt, key=str(log_path))

    def _apply_report(self, report: ScanReport) -> None:
        bar = self.query_one("#metrics-bar", MetricsBar)
        bar.update_metrics(
            integrity  = report.integrity_pct,
            errors     = report.total_errors,
            warnings   = report.total_warnings,
            files      = report.total_files,
            scanned    = report.total_files,
            duration_s = report.duration_s,
            status     = "DONE" if report.total_errors == 0 else "FAILED",
        )
        pie = self.query_one("#pie-chart", PieChartWidget)
        pie.update(report.integrity_pct, report.failure_pct, report.warning_pct)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        ext_map = {
            "btn-all":  None,
            "btn-py":   ["py"],
            "btn-js":   ["js"],
            "btn-css":  ["css"],
            "btn-html": ["html", "htm"],
        }
        btn_id = event.button.id or ""
        if btn_id in ext_map:
            self.app.action_run_scan(ext_map[btn_id])  # type: ignore[attr-defined]

    def on_run_script_request(self, event: RunScriptRequest) -> None:
        self.app.action_run_script(event.meta)  # type: ignore[attr-defined]

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value:
            log_path = Path(event.row_key.value)
            if log_path.exists():
                self.app.action_open_log(log_path)  # type: ignore[attr-defined]


def _parse_log_summary(log_path: Path):
    """Quick scan of the last 30 lines for summary counts."""
    e_count = w_count = f_count = 0
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[-30:]:
            import re, re as _re
            # Strip ANSI
            clean = re.sub(r"\x1b\[[0-9;]*m", "", line)
            if "Errors:" in clean:
                m = re.search(r"Errors:\s+(\d+)", clean)
                if m:
                    e_count = int(m.group(1))
            if "Warnings:" in clean:
                m = re.search(r"Warnings:\s+(\d+)", clean)
                if m:
                    w_count = int(m.group(1))
            if "Files:" in clean:
                m = re.search(r"Files:\s+(\d+)", clean)
                if m:
                    f_count = int(m.group(1))
    except OSError:
        pass
    return e_count, w_count, f_count
