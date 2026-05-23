from __future__ import annotations

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from .models import ValidationIssue, ValidatorResult


class BaseValidator(ABC):
    """
    Abstract base all language validators inherit from.

    Subclasses implement `_run(file_path)` and return a list of
    ValidationIssue objects. Timing and error-isolation are handled here.
    """

    name:       str = "base"
    language:   str = "unknown"

    def validate(self, file_path: Path) -> ValidatorResult:
        result = ValidatorResult(
            validator_name=self.name,
            file_path=file_path,
        )
        t_start = time.perf_counter()

        try:
            result.issues = self._run(file_path)
        except Exception as exc:            # noqa: BLE001
            # Never let a validator crash the entire scan —
            # log it as an error issue instead.
            from .models import ValidationIssue, Severity
            result.issues = [
                ValidationIssue(
                    file_path=file_path,
                    line=0,
                    col=0,
                    severity=Severity.ERROR,
                    rule=f"{self.name}.internal_error",
                    message=f"Validator raised an exception: {exc}",
                    suggested_fix="Check that all required tools are installed and the file is readable.",
                )
            ]

        result.duration_ms = (time.perf_counter() - t_start) * 1000
        return result

    @abstractmethod
    def _run(self, file_path: Path) -> List[ValidationIssue]:
        ...

    # ── shared helpers ─────────────────────────────────────────────────────────

    def _read_lines(self, file_path: Path) -> List[str]:
        return file_path.read_text(encoding="utf-8", errors="replace").splitlines()

    def _context(self, lines: List[str], target_line: int, radius: int = 2):
        """
        Return (slice_of_lines, start_line_number) centered around
        target_line (1-indexed).
        """
        zero    = target_line - 1
        lo      = max(0, zero - radius)
        hi      = min(len(lines), zero + radius + 1)
        return lines[lo:hi], lo + 1
