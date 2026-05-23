from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .models import FileReport, ScanReport, Severity, ValidatorResult
from .base_validator import BaseValidator
from .logger import ValidationLogger


# ── language registry ──────────────────────────────────────────────────────────
_EXT_MAP: Dict[str, str] = {
    ".py":   "python",
    ".js":   "javascript",
    ".css":  "css",
    ".html": "html",
    ".htm":  "html",
}


def _load_validators(language: str) -> List[BaseValidator]:
    """Lazy-import validator lists to avoid circular imports."""
    if language == "python":
        from ..validators.py.checks import ALL_VALIDATORS
    elif language == "javascript":
        from ..validators.js.checks import ALL_VALIDATORS
    elif language == "css":
        from ..validators.css.checks import ALL_VALIDATORS
    elif language == "html":
        from ..validators.html.checks import ALL_VALIDATORS
    else:
        return []
    return ALL_VALIDATORS          # type: ignore[return-value]


# ── scan options ───────────────────────────────────────────────────────────────

class ScanOptions:
    def __init__(
        self,
        target_dir:         Path,
        extensions:         Optional[List[str]]     = None,
        exclude_patterns:   Optional[List[str]]     = None,
        max_file_size_kb:   int                     = 512,
        log_dir:            Optional[Path]          = None,
        include_quality_warnings: bool              = True,
    ) -> None:
        self.target_dir         = target_dir
        self.extensions         = extensions or list(_EXT_MAP.keys())
        self.exclude_patterns   = exclude_patterns or ["node_modules", ".git", "__pycache__", "venv", ".venv"]
        self.max_file_size_kb   = max_file_size_kb
        self.log_dir            = log_dir or (target_dir / ".validation_logs")
        self.include_quality_warnings = include_quality_warnings


# ── progress callback type ─────────────────────────────────────────────────────
ProgressCallback = Callable[[int, int, Path], None]


# ══════════════════════════════════════════════════════════════════════════════
# Scanner
# ══════════════════════════════════════════════════════════════════════════════

class Scanner:
    def __init__(self, options: ScanOptions, logger: ValidationLogger) -> None:
        self._options   = options
        self._logger    = logger

    def discover_files(self) -> List[Path]:
        """Walk target_dir and collect all files matching configured extensions."""
        target  = self._options.target_dir
        exts    = set(self._options.extensions)
        exclude = self._options.exclude_patterns
        files:  List[Path] = []

        for path in sorted(target.rglob("*")):
            if not path.is_file():
                continue
            # Exclude dirs
            if any(pat in path.parts for pat in exclude):
                continue
            if path.suffix.lower() not in exts:
                continue
            # Skip very large files
            size_kb = path.stat().st_size / 1024
            if size_kb > self._options.max_file_size_kb:
                self._logger.warn(f"Skipping {path} — {size_kb:.0f}KB exceeds limit.")
                continue
            files.append(path)

        return files

    def scan_file(self, file_path: Path) -> FileReport:
        """Run all appropriate validators against a single file."""
        report      = FileReport(file_path=file_path)
        ext         = file_path.suffix.lower()
        language    = _EXT_MAP.get(ext)

        if not language:
            return report

        validators = _load_validators(language)

        for validator in validators:
            self._logger.scan_start(file_path, validator.name)
            result: ValidatorResult = validator.validate(file_path)

            if not self._options.include_quality_warnings:
                result.issues = [
                    issue
                    for issue in result.issues
                    if issue.severity != Severity.WARNING
                ]

            report.results.append(result)

            if result.skipped:
                self._logger.warn(f"[{validator.name}] Skipped: {result.skip_reason}")
                continue

            if result.passed and result.warning_count == 0:
                self._logger.scan_pass(file_path, validator.name, result.duration_ms)
            else:
                self._logger.scan_fail(
                    file_path, validator.name,
                    result.error_count, result.warning_count, result.duration_ms,
                )

            # Log each issue
            for issue in result.issues:
                self._logger.issue(
                    severity        = issue.severity.value,
                    line            = issue.line,
                    col             = issue.col,
                    rule            = issue.rule,
                    message         = issue.message,
                    suggested_fix   = issue.suggested_fix,
                    context_lines   = issue.context_lines,
                    context_start   = issue.context_start,
                )

        return report

    def run(
        self,
        progress_cb:    Optional[ProgressCallback] = None,
        files:          Optional[List[Path]]       = None,
    ) -> ScanReport:
        """Run a full scan and return a ScanReport."""
        scan_report             = ScanReport(target_dir=self._options.target_dir)
        scan_report.started_at  = time.time()

        target_files = files if files is not None else self.discover_files()
        total        = len(target_files)

        self._logger.section(f"SCANNING {total} FILE(S) IN {self._options.target_dir}")

        for idx, file_path in enumerate(target_files, start=1):
            if progress_cb:
                progress_cb(idx, total, file_path)

            file_report = self.scan_file(file_path)
            scan_report.file_reports.append(file_report)

            # File-level header in log
            self._logger.file_header(
                file_path,
                file_report.error_count,
                file_report.warning_count,
            )

        scan_report.finished_at = time.time()

        self._logger.summary(
            total       = scan_report.total_files,
            errors      = scan_report.total_errors,
            warnings    = scan_report.total_warnings,
            clean       = len(scan_report.clean_files),
            integrity   = scan_report.integrity_pct,
            duration_s  = scan_report.duration_s,
        )

        return scan_report
