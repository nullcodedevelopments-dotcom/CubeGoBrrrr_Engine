from __future__ import annotations
import time
from pathlib import Path
from typing import List, Optional
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Label, ProgressBar, Static
from textual.worker import Worker, WorkerCancelled
from textual import work
from ..widgets.log_panel import LogPanel
from ..widgets.issue_table import IssueTable, IssueSelected
from ..widgets.metrics_bar import MetricsBar
from ...core.logger import ValidationLogger
from ...core.models import FileReport, ScanReport, Severity, ValidationIssue, ValidatorResult
from ...core.scanner import Scanner, ScanOptions
from ...core.script_loader import ScriptMeta
from ..theme import THEME

class ScanScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel_scan", "Cancel", show=True),
        Binding("d",      "app.switch_screen('dashboard')", "Dashboard", show=True),
    ]

    def __init__(
        self,
        extensions: Optional[List[str]] = None,
        script_meta: Optional[ScriptMeta] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._extensions    = extensions
        self._script_meta   = script_meta
        self._scan_worker:  Optional[Worker] = None
        self._start_time    = 0.0
        self._report:       Optional[ScanReport] = None

    def compose(self) -> ComposeResult:
        yield MetricsBar(id="scan-metrics")
        with Vertical(id="scan-body"):
            with Horizontal(id="scan-status-row"):
                yield Label("Preparing scan…", id="scan-status-label")
                yield Button("Cancel", id="btn-cancel", classes="btn-red")
            yield ProgressBar(id="scan-progress", total=100, show_eta=False)
            yield LogPanel(id="scan-log")
            yield IssueTable(id="scan-issue-table")

    def on_mount(self) -> None:
        log = self.query_one("#scan-log", LogPanel)
        log.clear_and_reset()
        self._start_time = time.time()
        self._scan_worker = self._run_scan()

    def action_cancel_scan(self) -> None:
        if self._scan_worker:
            self._scan_worker.cancel()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.action_cancel_scan()

    @work(thread=True, exclusive=True)
    def _run_scan(self) -> Optional[ScanReport]:
        target_dir: Path         = getattr(self.app, "target_dir", Path("."))
        log_dir:    Path         = getattr(self.app, "log_dir", target_dir / ".validation_logs")
        script_meta: Optional[ScriptMeta] = self._script_meta
        scan_exts:  Optional[List[str]] = self._extensions if self._extensions is not None else getattr(self.app, "extensions", None)
        exclude_patterns: Optional[List[str]] = getattr(self.app, "exclude_patterns", None)
        max_file_kb: int = int(getattr(self.app, "max_file_kb", 512))
        include_quality_warnings: bool = bool(getattr(self.app, "show_quality_warnings", True))
        logger      = ValidationLogger(log_dir=log_dir, session_name="scan")

        if script_meta is not None:
            return self._run_custom_script(script_meta, target_dir, logger)

        options     = ScanOptions(
            target_dir               = target_dir,
            extensions               = ([f".{e.lstrip('.')}" for e in scan_exts] if scan_exts else None),
            exclude_patterns         = exclude_patterns,
            max_file_size_kb         = max_file_kb,
            log_dir                  = log_dir,
            include_quality_warnings = include_quality_warnings,
        )
        scanner     = Scanner(options, logger)
        files       = scanner.discover_files()
        total       = len(files)

        self.app.call_from_thread(self._on_discovered, total)

        report = ScanReport(target_dir=target_dir)
        report.started_at = time.time()

        for idx, file_path in enumerate(files, 1):
            self.app.call_from_thread(self._on_progress, idx, total, file_path)
            file_report = scanner.scan_file(file_path)
            report.file_reports.append(file_report)
            logger.file_header(file_path, file_report.error_count, file_report.warning_count)
            for issue in file_report.all_issues:
                self.app.call_from_thread(self._on_issue, issue)
            self.app.call_from_thread(self._on_metrics, report)

        report.finished_at = time.time()
        logger.summary(
            total=report.total_files, errors=report.total_errors,
            warnings=report.total_warnings, clean=len(report.clean_files),
            integrity=report.integrity_pct, duration_s=report.duration_s,
        )
        log_path = logger.close()
        self.app.call_from_thread(self._on_complete, report, log_path)
        return report

    def _run_custom_script(
        self,
        script_meta: ScriptMeta,
        target_dir: Path,
        logger: ValidationLogger,
    ) -> Optional[ScanReport]:
        self.app.call_from_thread(self._on_discovered, 1)
        self.app.call_from_thread(self._on_progress, 1, 1, script_meta.path)

        report = ScanReport(target_dir=target_dir)
        report.started_at = time.time()
        file_report = FileReport(file_path=target_dir)

        loader = getattr(self.app, "script_loader", None)
        if loader is None:
            result = ValidatorResult(
                validator_name=f"script.{script_meta.path.stem}",
                file_path=target_dir,
                issues=[
                    ValidationIssue(
                        file_path=target_dir,
                        line=0,
                        col=0,
                        severity=Severity.ERROR,
                        rule=f"script.{script_meta.path.stem}.loader_missing",
                        message="Script loader is unavailable.",
                        suggested_fix="Restart the app and try again.",
                    )
                ],
            )
        else:
            logger.section(f"RUNNING SCRIPT: {script_meta.name}")
            result = loader.run_script(script_meta, target_dir, logger)

        file_report.results.append(result)
        report.file_reports.append(file_report)

        logger.file_header(target_dir, file_report.error_count, file_report.warning_count)
        for issue in file_report.all_issues:
            self.app.call_from_thread(self._on_issue, issue)
        self.app.call_from_thread(self._on_metrics, report)

        report.finished_at = time.time()
        logger.summary(
            total=report.total_files,
            errors=report.total_errors,
            warnings=report.total_warnings,
            clean=len(report.clean_files),
            integrity=report.integrity_pct,
            duration_s=report.duration_s,
        )
        log_path = logger.close()
        self.app.call_from_thread(self._on_complete, report, log_path)
        return report

    def _on_discovered(self, total: int) -> None:
        label = self.query_one("#scan-status-label", Label)
        label.update(f"Discovered [bold cyan]{total}[/] file(s) — starting…")
        self.query_one("#scan-progress", ProgressBar).update(total=max(total, 1))
        log = self.query_one("#scan-log", LogPanel)
        log.write_section(f"Discovered {total} file(s)")

    def _on_progress(self, done: int, total: int, current_file: Path) -> None:
        label = self.query_one("#scan-status-label", Label)
        label.update(f"[{done}/{total}]  [dim]{current_file.name}[/]")
        self.query_one("#scan-progress", ProgressBar).advance(1)
        log = self.query_one("#scan-log", LogPanel)
        from rich.text import Text
        log.write(Text.assemble(("→ ", THEME["dim"]), (str(current_file), THEME["dim"])))

    def _on_issue(self, issue: ValidationIssue) -> None:
        self.query_one("#scan-log",         LogPanel   ).write_issue(issue)
        self.query_one("#scan-issue-table", IssueTable ).append_issue(issue)

    def _on_metrics(self, report: ScanReport) -> None:
        elapsed = time.time() - self._start_time
        self.query_one("#scan-metrics", MetricsBar).update_metrics(
            integrity   = report.integrity_pct,
            errors      = report.total_errors,
            warnings    = report.total_warnings,
            files       = report.total_files,
            scanned     = report.total_files,
            duration_s  = elapsed,
            status      = "SCANNING",
        )

    def _on_complete(self, report: ScanReport, log_path: Path) -> None:
        self._report = report
        label = self.query_one("#scan-status-label", Label)
        label.update(f"[bold green]✓ Scan complete[/]  — log saved to [dim]{log_path}[/]")
        bar = self.query_one("#scan-metrics", MetricsBar)
        bar.update_metrics(
            integrity   = report.integrity_pct,
            errors      = report.total_errors,
            warnings    = report.total_warnings,
            files       = report.total_files,
            scanned     = report.total_files,
            duration_s  = report.duration_s,
            status      = "DONE" if report.total_errors == 0 else "FAILED",
        )
        self.app.post_scan_hook(report)  # type: ignore[attr-defined]

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.is_cancelled:
            label = self.query_one("#scan-status-label", Label)
            label.update("[bold yellow]⚠ Scan cancelled[/]")
