from __future__ import annotations
from pathlib import Path
from typing import Optional, Set
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Checkbox, DirectoryTree, Input, Label, Static
from ..widgets.issue_table import IssueTable, IssueSelected
from ..widgets.metrics_bar import MetricsBar
from ...core.models import ScanReport, Severity, ValidationIssue
from ..theme import THEME

class ResultsScreen(Screen):
    BINDINGS = [
        Binding("d", "app.switch_screen('dashboard')", "Dashboard", show=True),
        Binding("s", "app.run_scan",                   "Re-scan",   show=True),
        Binding("l", "app.switch_screen('logs')",      "Logs",      show=True),
    ]

    def compose(self) -> ComposeResult:
        yield MetricsBar(id="results-metrics")
        with Horizontal(id="results-filter-bar"):
            yield Input(placeholder="Filter message…", id="filter-input")
            yield Checkbox("ERR",  True, id="cb-error")
            yield Checkbox("WARN", True, id="cb-warn")
            yield Checkbox("INFO", True, id="cb-info")
            yield Button("Re-scan",  id="btn-rescan",  classes="btn-green")
            yield Button("Dashboard",id="btn-dash",    classes="btn-dim")
        with Horizontal(id="results-main"):
            with Vertical(id="results-left"):
                yield Label("  Files", classes="label-accent")
                yield DirectoryTree(path=str(Path(".")), id="results-tree")
            with Vertical(id="results-right"):
                yield IssueTable(id="results-table")
                with Vertical(id="detail-panel", classes="detail-panel"):
                    yield Label("Select an issue to view details", classes="label-dim", id="detail-label")
                    yield Static("", id="detail-body")

    def on_mount(self) -> None:
        report: Optional[ScanReport] = getattr(self.app, "last_report", None)
        if report:
            self._apply_report(report)

    def _apply_report(self, report: ScanReport) -> None:
        tbl = self.query_one("#results-table", IssueTable)
        tbl.load_report(report)
        bar = self.query_one("#results-metrics", MetricsBar)
        bar.update_metrics(
            integrity   = report.integrity_pct,
            errors      = report.total_errors,
            warnings    = report.total_warnings,
            files       = report.total_files,
            scanned     = report.total_files,
            duration_s  = report.duration_s,
            status      = "DONE" if report.total_errors == 0 else "FAILED",
        )
        target = getattr(self.app, "target_dir", Path("."))
        tree = self.query_one("#results-tree", DirectoryTree)
        tree.path = str(target)

    def on_issue_selected(self, event: IssueSelected) -> None:
        self._show_detail(event.issue)

    def _show_detail(self, issue: ValidationIssue) -> None:
        sev_color = {Severity.ERROR: "red", Severity.WARNING: "yellow", Severity.INFO: "cyan"}.get(issue.severity, "white")
        label = self.query_one("#detail-label", Label)
        label.update(
            f"[bold {sev_color}]{issue.severity.value}[/]  "
            f"[magenta]{issue.rule}[/]  "
            f"[dim]{issue.file_path.name}:{issue.line}[/]"
        )
        body   = self.query_one("#detail-body", Static)
        lines  = [f"  {issue.message}\n"]
        if issue.context_lines:
            lines.append("")
            for i, ctx_line in enumerate(issue.context_lines):
                ln_num = issue.context_start + i
                ind = ">>>" if ln_num == issue.line else "   "
                color = sev_color if ln_num == issue.line else "dim"
                lines.append(f"  [{color}]{ln_num:>4} {ind} {ctx_line.rstrip()}[/]")
            lines.append("")
        if issue.suggested_fix:
            lines.append(f"  [bold green]✦ Fix:[/] [green]{issue.suggested_fix}[/]")
        body.update("\n".join(lines))

    def _active_severities(self) -> Set[Severity]:
        active = set()
        if self.query_one("#cb-error",  Checkbox).value: active.add(Severity.ERROR)
        if self.query_one("#cb-warn",   Checkbox).value: active.add(Severity.WARNING)
        if self.query_one("#cb-info",   Checkbox).value: active.add(Severity.INFO)
        return active

    def on_checkbox_changed(self, _) -> None:
        self.query_one("#results-table", IssueTable).filter_severity(self._active_severities())

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-input":
            self.query_one("#results-table", IssueTable).filter_text(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-rescan":
            self.app.action_run_scan(None)  # type: ignore[attr-defined]
        elif event.button.id == "btn-dash":
            self.app.switch_screen("dashboard")
