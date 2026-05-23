from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class Severity(Enum):
    ERROR   = "ERROR"
    WARNING = "WARNING"
    INFO    = "INFO"


@dataclass
class ValidationIssue:
    file_path:      Path
    line:           int
    col:            int
    severity:       Severity
    rule:           str
    message:        str
    suggested_fix:  Optional[str]       = None
    context_lines:  List[str]           = field(default_factory=list)
    context_start:  int                 = 0  # line number of first context line

    def severity_label(self) -> str:
        labels = {
            Severity.ERROR:   "[bold red]ERROR[/bold red]",
            Severity.WARNING: "[bold yellow]WARNING[/bold yellow]",
            Severity.INFO:    "[bold cyan]INFO[/bold cyan]",
        }
        return labels[self.severity]

    def severity_plain(self) -> str:
        return self.severity.value


@dataclass
class ValidatorResult:
    validator_name: str
    file_path:      Path
    issues:         List[ValidationIssue]   = field(default_factory=list)
    duration_ms:    float                   = 0.0
    skipped:        bool                    = False
    skip_reason:    Optional[str]           = None

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)

    @property
    def passed(self) -> bool:
        return self.error_count == 0


@dataclass
class FileReport:
    """Aggregated results for a single file across all validators."""
    file_path:  Path
    results:    List[ValidatorResult] = field(default_factory=list)

    @property
    def all_issues(self) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        for r in self.results:
            issues.extend(r.issues)
        return sorted(issues, key=lambda i: (i.line, i.col))

    @property
    def error_count(self) -> int:
        return sum(r.error_count for r in self.results)

    @property
    def warning_count(self) -> int:
        return sum(r.warning_count for r in self.results)

    @property
    def status(self) -> str:
        if self.error_count > 0:
            return "FAIL"
        if self.warning_count > 0:
            return "WARN"
        return "PASS"


@dataclass
class ScanReport:
    """Top-level report covering all scanned files."""
    target_dir:     Path
    started_at:     float                   = field(default_factory=time.time)
    finished_at:    float                   = 0.0
    file_reports:   List[FileReport]        = field(default_factory=list)

    # ── computed properties ────────────────────────────────────────────────

    @property
    def total_files(self) -> int:
        return len(self.file_reports)

    @property
    def total_errors(self) -> int:
        return sum(fr.error_count for fr in self.file_reports)

    @property
    def total_warnings(self) -> int:
        return sum(fr.warning_count for fr in self.file_reports)

    @property
    def failed_files(self) -> List[FileReport]:
        return [fr for fr in self.file_reports if fr.status == "FAIL"]

    @property
    def warned_files(self) -> List[FileReport]:
        return [fr for fr in self.file_reports if fr.status == "WARN"]

    @property
    def clean_files(self) -> List[FileReport]:
        return [fr for fr in self.file_reports if fr.status == "PASS"]

    @property
    def integrity_pct(self) -> float:
        if self.total_files == 0:
            return 100.0
        return (len(self.clean_files) / self.total_files) * 100.0

    @property
    def failure_pct(self) -> float:
        if self.total_files == 0:
            return 0.0
        return (len(self.failed_files) / self.total_files) * 100.0

    @property
    def warning_pct(self) -> float:
        if self.total_files == 0:
            return 0.0
        return (len(self.warned_files) / self.total_files) * 100.0

    @property
    def duration_s(self) -> float:
        return self.finished_at - self.started_at

    def issues_by_rule(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for fr in self.file_reports:
            for issue in fr.all_issues:
                counts[issue.rule] = counts.get(issue.rule, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: -kv[1]))
