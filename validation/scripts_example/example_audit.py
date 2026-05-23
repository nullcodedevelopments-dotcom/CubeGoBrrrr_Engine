"""
Example custom audit script for .validation.

Copy this file into your project's .validation_scripts/ directory,
rename it (e.g. check_api_contracts.py), and implement the run() function.

CONTRACT
--------
Expose ONE of:
  def run(target_dir: Path, logger: ValidationLogger) -> List[ValidationIssue]
  def run(target_dir: Path, logger: ValidationLogger) -> ValidatorResult
  ALL_VALIDATORS: List[BaseValidator] = [...]

AVAILABLE IMPORTS
-----------------
  from validation.core.models    import ValidationIssue, Severity, ValidatorResult
  from validation.core.logger    import ValidationLogger
  from validation.core.formatter import format_output, OutputFormat
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List

from validation.core.models    import Severity, ValidationIssue
from validation.core.logger    import ValidationLogger
from validation.core.formatter import format_output, OutputFormat

_RULE_PREFIX = "example"
_EXTENSIONS  = {".py"}
_MARKERS     = {"TODO", "FIXME", "HACK", "XXX"}
_EXCLUDED    = {"__pycache__", ".git", "node_modules", "venv", ".venv"}


def run(target_dir: Path, logger: ValidationLogger) -> List[ValidationIssue]:
    """Scan for TODO/FIXME/HACK markers and optionally wrap flake8 output."""
    all_issues: List[ValidationIssue] = []
    logger.info(f"[example_audit] Scanning {target_dir}")

    for file_path in sorted(target_dir.rglob("*")):
        if not file_path.is_file() or file_path.suffix not in _EXTENSIONS:
            continue
        if any(p in _EXCLUDED for p in file_path.parts):
            continue
        all_issues.extend(_check_markers(file_path))

    try:
        proc = subprocess.run(
            ["flake8", "--max-line-length=120", str(target_dir)],
            capture_output=True, text=True, timeout=30,
        )
        if proc.stdout:
            for fp in target_dir.rglob("*.py"):
                chunk = "\n".join(l for l in proc.stdout.splitlines() if str(fp) in l)
                if chunk:
                    all_issues.extend(format_output(chunk, fp, f"{_RULE_PREFIX}.flake8", OutputFormat.FLAKE8))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.warn("[example_audit] flake8 not found — skipping external check.")

    logger.info(f"[example_audit] Found {len(all_issues)} issue(s).")
    return all_issues


def _check_markers(file_path: Path) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return issues
    for ln_idx, raw in enumerate(lines, start=1):
        for marker in _MARKERS:
            if marker in raw:
                lo, hi = max(0, ln_idx - 3), min(len(lines), ln_idx + 2)
                issues.append(ValidationIssue(
                    file_path=file_path, line=ln_idx, col=raw.find(marker),
                    severity=Severity.INFO,
                    rule=f"{_RULE_PREFIX}.todo_marker",
                    message=f"Found '{marker}' comment — resolve or track in your issue tracker.",
                    suggested_fix="Address the comment or create a ticket and reference it here.",
                    context_lines=lines[lo:hi], context_start=lo + 1,
                ))
                break
    return issues
