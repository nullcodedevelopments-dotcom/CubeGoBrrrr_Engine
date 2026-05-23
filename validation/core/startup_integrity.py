from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class StartupIntegrityReport:
    target_dir: Path
    log_dir: Path
    project_scripts_dir: Path
    created_dirs: List[Path] = field(default_factory=list)
    failed_dirs: List[Tuple[Path, str]] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.created_dirs)

    @property
    def has_failures(self) -> bool:
        return bool(self.failed_dirs)


def ensure_startup_integrity(
    target_dir: Path,
    log_dir: Optional[Path] = None,
    project_scripts_dir: Optional[Path] = None,
) -> StartupIntegrityReport:
    """Ensure required runtime directories exist before scanning or launching TUI."""
    resolved_target = target_dir.resolve()
    resolved_log_dir = log_dir.resolve() if log_dir else (resolved_target / ".validation_logs")
    resolved_scripts_dir = (
        project_scripts_dir.resolve()
        if project_scripts_dir
        else (resolved_target / ".validation_scripts")
    )

    report = StartupIntegrityReport(
        target_dir=resolved_target,
        log_dir=resolved_log_dir,
        project_scripts_dir=resolved_scripts_dir,
    )

    required_dirs = [resolved_log_dir, resolved_scripts_dir]
    seen: set[Path] = set()

    for directory in required_dirs:
        if directory in seen:
            continue
        seen.add(directory)

        if directory.exists():
            if not directory.is_dir():
                report.failed_dirs.append((directory, "path exists but is not a directory"))
            continue

        try:
            directory.mkdir(parents=True, exist_ok=True)
            report.created_dirs.append(directory)
        except OSError as exc:
            report.failed_dirs.append((directory, str(exc)))

    return report
