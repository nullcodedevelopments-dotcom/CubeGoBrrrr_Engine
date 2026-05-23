from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.text import Text

# ── ANSI codes for the plain log file ─────────────────────────────────────────
_ANSI = {
    "reset":    "\033[0m",
    "bold":     "\033[1m",
    "red":      "\033[38;5;196m",
    "yellow":   "\033[38;5;220m",
    "green":    "\033[38;5;82m",
    "cyan":     "\033[38;5;51m",
    "blue":     "\033[38;5;39m",
    "magenta":  "\033[38;5;201m",
    "grey":     "\033[38;5;240m",
    "white":    "\033[97m",
    "dim":      "\033[2m",
}

def _a(code: str, text: str) -> str:
    """Wrap text in ANSI color code."""
    return f"{_ANSI.get(code, '')}{text}{_ANSI['reset']}"


# ── severity color maps ────────────────────────────────────────────────────────
_SEVERITY_RICH = {
    "ERROR":   "bold red",
    "WARNING": "bold yellow",
    "INFO":    "bold cyan",
}
_SEVERITY_ANSI = {
    "ERROR":   "red",
    "WARNING": "yellow",
    "INFO":    "cyan",
}


class ValidationLogger:
    """
    Dual-output logger:
      • Rich terminal console — colored, formatted for live display
      • ANSI log file — color-coded, human-readable, replayable

    All session output is accumulated and flushed to the log file when
    `close()` / `save_report()` is called.
    """

    def __init__(self, log_dir: Path, session_name: Optional[str] = None) -> None:
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = session_name or "scan"
        self.log_path = self.log_dir / f"{name}_{ts}.log"

        # Rich console for terminal output — stderr so it doesn't polute pipe output
        self.console = Console(stderr=False, highlight=False)

        # Internal Python logger (no handlers — we route manually)
        self._logger = logging.getLogger(f"validation.{ts}")
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False

        # Buffer of raw ANSI lines written to the log file
        self._log_lines: list[str] = []
        self._file_open = True

        # Write log header
        self._write_log_header()

    # ── public interface ───────────────────────────────────────────────────────

    def info(self, msg: str) -> None:
        self._emit("INFO", msg)

    def warn(self, msg: str) -> None:
        self._emit("WARNING", msg)

    def error(self, msg: str) -> None:
        self._emit("ERROR", msg)

    def debug(self, msg: str) -> None:
        ts = _a("grey", f"[{self._ts()}]")
        dim = _a("dim", msg)
        self._append_raw(f"{ts} {_a('grey', 'DBG')} {dim}")

    def separator(self, char: str = "─", width: int = 72) -> None:
        line = _a("grey", char * width)
        self._append_raw(line)

    def section(self, title: str) -> None:
        self.separator("─")
        self._append_raw(_a("bold", f"  {title}"))
        self.separator("─")

    def file_header(self, file_path: Path, error_count: int, warn_count: int) -> None:
        path_str = _a("white", str(file_path))
        if error_count > 0:
            badge = _a("red", f"✗ {error_count}E {warn_count}W")
        elif warn_count > 0:
            badge = _a("yellow", f"⚠ {warn_count}W")
        else:
            badge = _a("green", "✓ CLEAN")

        self.separator("─")
        self._append_raw(f"  FILE: {path_str}  {badge}")
        self.separator("─")

    def issue(
        self,
        severity:       str,
        line:           int,
        col:            int,
        rule:           str,
        message:        str,
        suggested_fix:  Optional[str],
        context_lines:  list[str],
        context_start:  int,
    ) -> None:
        sev_color   = _SEVERITY_ANSI.get(severity, "white")
        ts          = _a("grey", f"[{self._ts()}]")
        sev_label   = _a(sev_color, f"[{severity:<7}]")
        loc         = _a("blue", f"Line {line}" + (f", Col {col}" if col > 0 else ""))
        rule_label  = _a("magenta", f"| {rule}")

        self._append_raw(f"\n{ts} {sev_label} {loc} {rule_label}")
        self._append_raw(f"  {_a('white', message)}")

        # Context lines (surrounding code)
        if context_lines:
            self._append_raw("")
            for idx, ctx_line in enumerate(context_lines):
                ln_num      = context_start + idx
                indicator   = ">>>" if ln_num == line else "   "
                color       = sev_color if ln_num == line else "grey"
                ln_str      = _a("dim", f"{ln_num:>4}")
                ind_str     = _a(color, indicator)
                code_str    = _a("white" if ln_num == line else "dim", ctx_line.rstrip())
                self._append_raw(f"  {ln_str} {ind_str} {code_str}")
            self._append_raw("")

        # Suggested fix
        if suggested_fix:
            prefix  = _a("green", "  ✦ Fix: ")
            fix_txt = _a("green", suggested_fix)
            self._append_raw(f"{prefix}{fix_txt}")

    def scan_start(self, file_path: Path, validator: str) -> None:
        ts = _a("grey", f"[{self._ts()}]")
        v  = _a("cyan", f"[{validator}]")
        p  = _a("dim", str(file_path))
        self._append_raw(f"{ts} {v} Scanning {p}")

    def scan_pass(self, file_path: Path, validator: str, ms: float) -> None:
        ts  = _a("grey", f"[{self._ts()}]")
        v   = _a("cyan", f"[{validator}]")
        chk = _a("green", "✓ PASS")
        t   = _a("grey", f"({ms:.0f}ms)")
        self._append_raw(f"{ts} {v} {chk} {_a('dim', str(file_path))} {t}")

    def scan_fail(self, file_path: Path, validator: str, e_count: int, w_count: int, ms: float) -> None:
        ts  = _a("grey", f"[{self._ts()}]")
        v   = _a("cyan", f"[{validator}]")
        if e_count > 0:
            badge = _a("red", f"✗ {e_count} error(s), {w_count} warning(s)")
        else:
            badge = _a("yellow", f"⚠ {w_count} warning(s)")
        t = _a("grey", f"({ms:.0f}ms)")
        self._append_raw(f"{ts} {v} {badge} {_a('dim', str(file_path))} {t}")

    def summary(
        self,
        total: int,
        errors: int,
        warnings: int,
        clean: int,
        integrity: float,
        duration_s: float,
    ) -> None:
        self.separator("═", 72)
        self._append_raw(_a("bold", "  SCAN SUMMARY"))
        self.separator("═", 72)

        bar_len = 40
        filled  = int(integrity / 100 * bar_len)
        bar     = _a("green", "█" * filled) + _a("grey", "░" * (bar_len - filled))

        self._append_raw(f"  Integrity:  {bar}  {_a('green', f'{integrity:.1f}%')}")
        self._append_raw(f"  Files:      {_a('white', str(total))}")
        self._append_raw(f"  Errors:     {_a('red', str(errors))}")
        self._append_raw(f"  Warnings:   {_a('yellow', str(warnings))}")
        self._append_raw(f"  Clean:      {_a('green', str(clean))}")
        self._append_raw(f"  Duration:   {_a('cyan', f'{duration_s:.2f}s')}")
        self.separator("═", 72)

    def save(self) -> Path:
        """Write all buffered lines to the log file. Returns path."""
        if self._file_open:
            content = "\n".join(self._log_lines)
            self.log_path.write_text(content, encoding="utf-8")
        return self.log_path

    def close(self) -> Path:
        path = self.save()
        self._file_open = False
        return path

    # ── internal helpers ───────────────────────────────────────────────────────

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _emit(self, level: str, msg: str) -> None:
        ts          = _a("grey", f"[{self._ts()}]")
        sev_color   = _SEVERITY_ANSI.get(level, "white")
        label       = _a(sev_color, f"[{level:<7}]")
        self._append_raw(f"{ts} {label} {msg}")

    def _append_raw(self, line: str) -> None:
        self._log_lines.append(line)

    def _write_log_header(self) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.separator("═", 72)
        self._append_raw(_a("bold", f"  .VALIDATION — SCAN REPORT"))
        self._append_raw(_a("grey",  f"  Generated: {now}"))
        self._append_raw(_a("grey",  f"  Log path:  {self.log_path}"))
        self.separator("═", 72)
        self._append_raw("")
