"""tui/theme.py — Single source of truth for all Textual CSS and color tokens."""
from __future__ import annotations
from typing import Dict

THEME: Dict[str, str] = {
    "green":            "#5fd700",
    "red":              "#ff0000",
    "yellow":           "#ffd700",
    "cyan":             "#00ffff",
    "blue":             "#1e90ff",
    "magenta":          "#da70d6",
    "white":            "#eeeeee",
    "dim":              "#666666",
    "surface":          "#111111",
    "surface-raised":   "#1a1a1a",
    "surface-header":   "#0d0d0d",
    "border":           "#333333",
    "border-bright":    "#555555",
    "sev-error":        "#ff0000",
    "sev-warning":      "#ffd700",
    "sev-info":         "#00ffff",
    "accent":           "#1e90ff",
    "accent-dim":       "#104e8b",
}

def severity_color(sev: str) -> str:
    return {"ERROR": THEME["sev-error"], "WARNING": THEME["sev-warning"], "INFO": THEME["sev-info"]}.get(sev.upper(), THEME["white"])

APP_CSS = """
Screen { background: #111111; color: #eeeeee; }
Header { background: #0d0d0d; color: #00ffff; text-style: bold; height: 1; dock: top; }
Footer { background: #0d0d0d; color: #666666; height: 1; dock: bottom; }
.panel { border: round #333333; background: #1a1a1a; padding: 0 1; margin: 0 0 1 0; }
Button { background: #1a1a1a; border: tall #333333; color: #eeeeee; min-width: 18; margin: 0 1 0 0; }
Button:hover { background: #252525; border: tall #555555; }
Button:focus { border: tall #1e90ff; }
.btn-green { border: tall #5fd700; color: #5fd700; }
.btn-green:hover { background: #1a2a00; color: #7fff00; }
.btn-red { border: tall #ff0000; color: #ff0000; }
.btn-red:hover { background: #2a0000; }
.btn-yellow { border: tall #ffd700; color: #ffd700; }
.btn-yellow:hover { background: #2a2200; }
.btn-dim { border: tall #444444; color: #888888; }
DataTable { background: #111111; color: #eeeeee; height: 1fr; }
DataTable > .datatable--header { background: #0d0d0d; color: #00ffff; text-style: bold; }
DataTable > .datatable--cursor { background: #1e3a5f; color: #ffffff; }
DataTable > .datatable--hover { background: #1a1a2e; }
ProgressBar > .bar--bar { color: #1e90ff; }
ProgressBar > .bar--complete { color: #5fd700; }
Input { background: #1a1a1a; border: tall #333333; color: #eeeeee; }
Input:focus { border: tall #1e90ff; }
ListView { background: #111111; color: #eeeeee; height: 1fr; }
ListItem { background: #111111; padding: 0 1; }
ListItem:hover { background: #1a1a2e; }
ListView > ListItem.--highlight { background: #1e3a5f; }
RichLog { background: #0d0d0d; color: #eeeeee; height: 1fr; border: round #333333; padding: 0 1; }
.severity-error { color: #ff0000; text-style: bold; }
.severity-warning { color: #ffd700; text-style: bold; }
.severity-info { color: #00ffff; }
MetricsBar { background: #0d0d0d; height: 3; dock: top; padding: 0 2; border-bottom: solid #333333; }
PieChartWidget { width: 35%; height: 100%; border: round #333333; background: #1a1a1a; padding: 1 2; }
ScriptPanel { border: round #333333; background: #1a1a1a; padding: 1; height: auto; max-height: 16; }
.script-panel--empty { color: #666666; text-style: italic; padding: 1 2; }
.script-panel--section-label { color: #666666; text-style: bold; padding: 0 1; margin-top: 1; }
LogPanel { height: 1fr; border: round #333333; background: #0d0d0d; }
DirectoryTree { background: #111111; color: #eeeeee; height: 1fr; border: round #333333; width: 30%; }
.detail-panel { background: #1a1a1a; border: round #333333; height: 10; padding: 0 1; }
.detail-panel--fix { color: #5fd700; text-style: bold; }
.detail-panel--rule { color: #da70d6; }
ScrollBar { background: #1a1a1a; color: #333333; }
Label { color: #eeeeee; }
.label-dim { color: #666666; }
.label-accent { color: #00ffff; text-style: bold; }
.label-green { color: #5fd700; text-style: bold; }
.label-red { color: #ff0000; text-style: bold; }
.label-yellow { color: #ffd700; text-style: bold; }
#startup-warning-root { align: center middle; }
#startup-warning-dialog { width: 96; max-width: 96%; height: auto; padding: 1 2; }
#startup-warning-message { color: #eeeeee; padding: 1 0; }
#startup-warning-actions { height: auto; padding-top: 1; }
"""
