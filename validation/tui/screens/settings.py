from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Input, Label, Static

_CONFIG_PATH = Path.home() / ".validation_config.json"

_DEFAULTS: Dict[str, Any] = {
    "target_dir":       ".",
    "log_dir":          ".validation_logs",
    "max_file_kb":      512,
    "extensions":       ["py", "js", "css", "html", "htm"],
    "exclude_patterns": ["node_modules", ".git", "__pycache__", "venv", ".venv"],
    "show_quality_warnings": True,
}

def load_config() -> Dict[str, Any]:
    if _CONFIG_PATH.exists():
        try:
            return {**_DEFAULTS, **json.loads(_CONFIG_PATH.read_text())}
        except Exception:
            pass
    return dict(_DEFAULTS)

def save_config(cfg: Dict[str, Any]) -> None:
    _CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


class SettingsScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.switch_screen('dashboard')", "Back",    show=True),
        Binding("ctrl+s", "save",                           "Save",    show=True),
    ]

    def compose(self) -> ComposeResult:
        cfg = load_config()
        yield Label("  ⚙  Settings", classes="label-accent")
        yield Static("─" * 40, classes="label-dim")
        with ScrollableContainer():
            with Vertical(classes="panel"):
                yield Label("Target Directory", classes="label-dim")
                yield Input(value=cfg.get("target_dir", "."), id="inp-target")
                yield Label("Log Directory", classes="label-dim")
                yield Input(value=cfg.get("log_dir", ".validation_logs"), id="inp-logdir")
                yield Label("Max File Size (KB)", classes="label-dim")
                yield Input(value=str(cfg.get("max_file_kb", 512)), id="inp-maxkb")
            with Vertical(classes="panel"):
                yield Label("Extensions to scan", classes="label-dim")
                exts = cfg.get("extensions", _DEFAULTS["extensions"])
                for ext in ["py", "js", "css", "html", "htm"]:
                    yield Checkbox(f".{ext}", ext in exts, id=f"cb-ext-{ext}")
            with Vertical(classes="panel"):
                yield Label("Exclude patterns (comma separated)", classes="label-dim")
                pats = ", ".join(cfg.get("exclude_patterns", _DEFAULTS["exclude_patterns"]))
                yield Input(value=pats, id="inp-exclude")
            with Vertical(classes="panel"):
                yield Label("Scan Behavior", classes="label-dim")
                yield Checkbox(
                    "Show code-quality warnings",
                    bool(cfg.get("show_quality_warnings", True)),
                    id="cb-quality-warn",
                )
            with Horizontal():
                yield Button("Save",  id="btn-save",  classes="btn-green")
                yield Button("Reset", id="btn-reset", classes="btn-yellow")
                yield Button("Back",  id="btn-back",  classes="btn-dim")

    def action_save(self) -> None:
        self._save()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            self._save()
        elif event.button.id == "btn-reset":
            defaults = dict(_DEFAULTS)
            save_config(defaults)
            self._apply_to_app(defaults)
            self.app.switch_screen("settings")
        elif event.button.id == "btn-back":
            self.app.switch_screen("dashboard")

    def _save(self) -> None:
        exts = [e for e in ["py", "js", "css", "html", "htm"] if self.query_one(f"#cb-ext-{e}", Checkbox).value]
        pats = [p.strip() for p in self.query_one("#inp-exclude", Input).value.split(",") if p.strip()]
        cfg = {
            "target_dir":       self.query_one("#inp-target", Input).value.strip(),
            "log_dir":          self.query_one("#inp-logdir", Input).value.strip(),
            "max_file_kb":      int(self.query_one("#inp-maxkb", Input).value.strip() or "512"),
            "extensions":       exts,
            "exclude_patterns": pats,
            "show_quality_warnings": self.query_one("#cb-quality-warn", Checkbox).value,
        }
        save_config(cfg)
        self._apply_to_app(cfg)
        self.app.switch_screen("dashboard")

    def _apply_to_app(self, cfg: Dict[str, Any]) -> None:
        # Push new settings to app runtime state so the next scan uses them.
        self.app.target_dir = Path(cfg["target_dir"]).resolve()           # type: ignore[attr-defined]
        self.app.log_dir = Path(cfg["log_dir"])                           # type: ignore[attr-defined]
        self.app.max_file_kb = int(cfg.get("max_file_kb", 512))           # type: ignore[attr-defined]
        self.app.extensions = list(cfg.get("extensions", []))             # type: ignore[attr-defined]
        self.app.exclude_patterns = list(cfg.get("exclude_patterns", [])) # type: ignore[attr-defined]
        self.app.show_quality_warnings = bool(                              # type: ignore[attr-defined]
            cfg.get("show_quality_warnings", True)
        )
