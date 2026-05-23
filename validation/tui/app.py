from __future__ import annotations
import sys
from pathlib import Path
from typing import List, Optional
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header
from .screens.dashboard import DashboardScreen
from .screens.scan import ScanScreen
from .screens.results import ResultsScreen
from .screens.log_viewer import LogViewerScreen
from .screens.settings import SettingsScreen, load_config
from .screens.startup_warning import StartupWarningScreen
from .theme import APP_CSS
from ..core.models import ScanReport
from ..core.script_loader import ScriptLoader, ScriptMeta
from ..core.startup_integrity import StartupIntegrityReport, ensure_startup_integrity

_GLOBAL_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


class ValidationApp(App):
    """
    .validation — interactive Textual TUI.

    Screens: Dashboard → Scan → Results → Log Viewer → Settings
    """

    CSS             = APP_CSS
    TITLE           = ".validation"
    SUB_TITLE       = "codebase integrity scanner"

    SCREENS = {
        "dashboard": DashboardScreen,
        "scan":      ScanScreen,
        "results":   ResultsScreen,
        "logs":      LogViewerScreen,
        "settings":  SettingsScreen,
    }

    BINDINGS = [
        Binding("d",      "switch_screen('dashboard')", "Dashboard", show=True),
        Binding("s",      "run_scan",                   "Scan",      show=True),
        Binding("r",      "switch_screen('results')",   "Results",   show=True),
        Binding("l",      "switch_screen('logs')",      "Logs",      show=True),
        Binding("comma",  "switch_screen('settings')",  "Settings",  show=True),
        Binding("q",      "quit",                        "Quit",      show=True),
    ]

    def __init__(
        self,
        target_dir:     Path                    = Path("."),
        log_dir:        Optional[Path]          = None,
        extensions:     Optional[List[str]]     = None,
        project_scripts_dir: Optional[Path]     = None,
        startup_report: Optional[StartupIntegrityReport] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        cfg = load_config()
        bootstrap = startup_report or ensure_startup_integrity(
            target_dir=target_dir.resolve(),
            log_dir=log_dir,
            project_scripts_dir=project_scripts_dir or (target_dir.resolve() / ".validation_scripts"),
        )
        self.startup_report: StartupIntegrityReport = bootstrap
        self.target_dir:    Path                    = bootstrap.target_dir
        self.log_dir:       Path                    = bootstrap.log_dir
        self.extensions:    Optional[List[str]]     = extensions or cfg.get("extensions")
        self.max_file_kb:   int                     = int(cfg.get("max_file_kb", 512))
        self.exclude_patterns: List[str]            = list(cfg.get("exclude_patterns", ["node_modules", ".git", "__pycache__", "venv", ".venv"]))
        self.show_quality_warnings: bool            = bool(cfg.get("show_quality_warnings", True))
        self.last_report:   Optional[ScanReport]    = None
        self.script_loader: ScriptLoader            = ScriptLoader(
            global_dir  = _GLOBAL_SCRIPTS_DIR,
            project_dir = bootstrap.project_scripts_dir,
        )

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        # Initial screen must be pushed from the default screen context.
        self.push_screen("dashboard")
        if self.startup_report.has_changes:
            self.push_screen(StartupWarningScreen(self.startup_report))

    # ── screen actions ─────────────────────────────────────────────────────────

    def action_run_scan(self, extensions: Optional[List[str]] = None) -> None:
        """Switch to ScanScreen and start a scan with optional extension filter."""
        self.push_screen(ScanScreen(extensions=extensions or self.extensions))

    def action_run_script(self, meta: ScriptMeta) -> None:
        """Run a custom script through ScanScreen."""
        self.push_screen(ScanScreen(extensions=None, script_meta=meta))

    def action_open_log(self, log_path: Path) -> None:
        """Push LogViewerScreen open to a specific log file."""
        self.push_screen(LogViewerScreen(open_path=log_path))

    # ── hooks ──────────────────────────────────────────────────────────────────

    def post_scan_hook(self, report: ScanReport) -> None:
        """Called by ScanScreen when scan finishes. Stores report, pushes Results."""
        self.last_report = report
        self.push_screen(ResultsScreen())


def launch_tui(
    target_dir:             Path                = Path("."),
    log_dir:                Optional[Path]      = None,
    extensions:             Optional[List[str]] = None,
    project_scripts_dir:    Optional[Path]      = None,
    startup_report:         Optional[StartupIntegrityReport] = None,
) -> int:
    """Public entry point — launch the ValidationApp and return exit code."""
    bootstrap = startup_report or ensure_startup_integrity(
        target_dir=target_dir,
        log_dir=log_dir,
        project_scripts_dir=project_scripts_dir or (target_dir / ".validation_scripts"),
    )
    if bootstrap.has_failures:
        joined = "; ".join(f"{path}: {reason}" for path, reason in bootstrap.failed_dirs)
        raise RuntimeError(f"Startup integrity check failed: {joined}")

    app = ValidationApp(
        target_dir          = bootstrap.target_dir,
        log_dir             = bootstrap.log_dir,
        extensions          = extensions,
        project_scripts_dir = bootstrap.project_scripts_dir,
        startup_report      = bootstrap,
    )
    app.run()
    return 0 if (app.last_report is None or app.last_report.total_errors == 0) else 1
