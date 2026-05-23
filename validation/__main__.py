#!/usr/bin/env python3
"""
.validation — codebase integrity scanner
Usage:
    python -m validation [TARGET_DIR] [OPTIONS]

Options:
    --ext py js css html   Restrict scan to specific extensions
    --no-tui               Plain stdout output (no TUI)
    --textual              Launch interactive Textual TUI (default when terminal detected)
    --log-dir PATH         Override log directory
    --exclude PATTERNS     Space-separated dir names to exclude
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from .core.logger import ValidationLogger
from .core.models import ScanReport
from .core.scanner import Scanner, ScanOptions
from .core.startup_integrity import ensure_startup_integrity


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="validation", description=".validation — multi-language codebase integrity scanner")
    p.add_argument("target", nargs="?", default=".", help="Directory to scan (default: current directory)")
    p.add_argument("--ext",      "-e",  nargs="+", metavar="EXT",  help="Extensions to scan, e.g. --ext py js")
    p.add_argument("--no-tui",          action="store_true",        help="Plain stdout, no TUI")
    p.add_argument("--textual",         action="store_true",        help="Launch Textual interactive TUI")
    p.add_argument("--log-dir",         default=None, metavar="PATH")
    p.add_argument("--exclude",         nargs="+", default=None, metavar="PAT")
    return p


def run(
    target_dir:     Path,
    extensions:     Optional[List[str]]     = None,
    exclude:        Optional[List[str]]     = None,
    log_dir:        Optional[Path]          = None,
    use_tui:        bool                    = True,
) -> ScanReport:
    startup_report = ensure_startup_integrity(
        target_dir=target_dir,
        log_dir=log_dir,
        project_scripts_dir=target_dir / ".validation_scripts",
    )
    if startup_report.has_failures:
        joined = "; ".join(f"{path}: {reason}" for path, reason in startup_report.failed_dirs)
        raise RuntimeError(f"Startup integrity check failed: {joined}")

    log_dir  = startup_report.log_dir
    logger   = ValidationLogger(log_dir=log_dir, session_name="scan")
    console  = Console()
    options  = ScanOptions(
        target_dir       = target_dir,
        extensions       = ([f".{e.lstrip('.')}" for e in extensions] if extensions else None),
        exclude_patterns = exclude,
        log_dir          = log_dir,
    )
    scanner  = Scanner(options, logger)
    files    = scanner.discover_files()
    total    = len(files)

    if not use_tui:
        console.print(f"[cyan]Discovered {total} file(s) to scan.[/]")

    scan_report             = ScanReport(target_dir=target_dir)
    scan_report.started_at  = time.time()

    for idx, file_path in enumerate(files, start=1):
        if not use_tui:
            pct = idx / max(total, 1) * 100
            console.print(f"[dim][{idx}/{total}] {pct:.0f}%[/]  {file_path}")
        file_report = scanner.scan_file(file_path)
        scan_report.file_reports.append(file_report)
        logger.file_header(file_path, file_report.error_count, file_report.warning_count)

    scan_report.finished_at = time.time()
    logger.summary(
        total      = scan_report.total_files,
        errors     = scan_report.total_errors,
        warnings   = scan_report.total_warnings,
        clean      = len(scan_report.clean_files),
        integrity  = scan_report.integrity_pct,
        duration_s = scan_report.duration_s,
    )
    log_path = logger.close()

    if not use_tui:
        _print_plain_summary(console, scan_report, log_path)

    return scan_report


def _print_plain_summary(console: Console, report: ScanReport, log_path: Path) -> None:
    console.print()
    console.rule("[bold cyan]SCAN SUMMARY[/]")
    console.print(f"  Files:      [white]{report.total_files}[/]")
    console.print(f"  Errors:     [red]{report.total_errors}[/]")
    console.print(f"  Warnings:   [yellow]{report.total_warnings}[/]")
    console.print(f"  Integrity:  [green]{report.integrity_pct:.1f}%[/]")
    console.print(f"  Duration:   [cyan]{report.duration_s:.2f}s[/]")
    console.print(f"  Log:        [dim]{log_path}[/]")
    console.rule()


def run_all_python(directory: Path, **kwargs) -> ScanReport:
    return run(directory, extensions=["py"], **kwargs)

def run_all_javascript(directory: Path, **kwargs) -> ScanReport:
    return run(directory, extensions=["js"], **kwargs)

def run_all_css(directory: Path, **kwargs) -> ScanReport:
    return run(directory, extensions=["css"], **kwargs)

def run_all_html(directory: Path, **kwargs) -> ScanReport:
    return run(directory, extensions=["html", "htm"], **kwargs)


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args   = parser.parse_args(argv)
    target = Path(args.target).resolve()

    if not target.is_dir():
        print(f"[ERROR] '{target}' is not a directory.", file=sys.stderr)
        return 1

    exts      = args.ext if args.ext else None
    log_dir   = Path(args.log_dir).resolve() if args.log_dir else None
    exclude   = args.exclude or None
    use_textual = args.textual
    no_tui    = args.no_tui
    startup_report = ensure_startup_integrity(
        target_dir=target,
        log_dir=log_dir,
        project_scripts_dir=target / ".validation_scripts",
    )
    if startup_report.has_failures:
        console = Console()
        console.print("[bold red]Startup integrity check failed.[/]")
        for path, reason in startup_report.failed_dirs:
            console.print(f"  [red]- {path}[/]  [dim]({reason})[/]")
        return 1

    log_dir = startup_report.log_dir

    # Textual TUI (interactive)
    if use_textual or (not no_tui and sys.stdout.isatty()):
        try:
            from .tui.app import launch_tui
            return launch_tui(
                target_dir  = target,
                log_dir     = log_dir,
                extensions  = exts,
                project_scripts_dir = startup_report.project_scripts_dir,
                startup_report = startup_report,
            )
        except ImportError:
            Console().print("[yellow]textual not installed — falling back to plain output.[/]")

    # Plain / legacy output
    report = run(
        target_dir  = target,
        extensions  = exts,
        exclude     = exclude,
        log_dir     = log_dir,
        use_tui     = False,
    )
    return 0 if report.total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
