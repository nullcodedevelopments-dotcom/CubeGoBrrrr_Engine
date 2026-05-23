from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from ...core.startup_integrity import StartupIntegrityReport


class StartupWarningScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("escape", "proceed", "Proceed", show=True),
        Binding("q", "close_application", "Close", show=True),
    ]

    def __init__(self, report: StartupIntegrityReport, **kwargs) -> None:
        super().__init__(**kwargs)
        self._report = report

    def compose(self) -> ComposeResult:
        with Vertical(id="startup-warning-root"):
            with Vertical(id="startup-warning-dialog", classes="panel"):
                yield Label("  Startup Integrity Notice", classes="label-yellow")
                yield Static(self._build_message(), id="startup-warning-message")
                with Horizontal(id="startup-warning-actions"):
                    yield Button("Close Application", id="btn-warning-close", classes="btn-red")
                    yield Button("Proceed Anyway", id="btn-warning-proceed", classes="btn-yellow")

    def _build_message(self) -> str:
        lines: list[str] = [
            "Validation startup checks detected missing required directories and created them:",
            "",
        ]
        for path in self._report.created_dirs:
            lines.append(f"- {path}")

        lines.extend(["", "If you plan to use custom scripts, add real script files to:"])
        lines.append(f"- {self._report.project_scripts_dir}")
        lines.append("")
        lines.append(
            "Then relaunch the application so the dashboard script list can refresh from startup state."
        )
        lines.append("")
        lines.append("You can proceed now, or close the application and relaunch after adding scripts.")
        return "\n".join(lines)

    def action_proceed(self) -> None:
        self.dismiss(True)

    def action_close_application(self) -> None:
        self.app.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-warning-close":
            self.action_close_application()
        elif event.button.id == "btn-warning-proceed":
            self.action_proceed()
