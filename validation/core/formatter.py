from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import List, Optional

from .models import Severity, ValidationIssue


class OutputFormat(Enum):
    PLAIN_TEXT  = "plain_text"
    FLAKE8      = "flake8"
    MYPY        = "mypy"
    ESLINT_JSON = "eslint_json"
    GENERIC     = "generic"


def _read_context(file_path: Path, target_line: int, radius: int = 2):
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return [], 0
    zero = target_line - 1
    lo   = max(0, zero - radius)
    hi   = min(len(lines), zero + radius + 1)
    return lines[lo:hi], lo + 1


def _map_severity(raw: str) -> Severity:
    r = raw.lower()
    if r in {"error", "e", "err", "critical", "fatal"}:
        return Severity.ERROR
    if r in {"warning", "w", "warn", "note"}:
        return Severity.WARNING
    return Severity.INFO


class FormatterAdapter(ABC):
    format: OutputFormat = OutputFormat.GENERIC

    @abstractmethod
    def parse(self, raw: str, file_path: Path, rule_prefix: str = "custom") -> List[ValidationIssue]:
        ...


class Flake8Adapter(FormatterAdapter):
    format  = OutputFormat.FLAKE8
    _RE     = re.compile(r"^(?P<path>[^:]+):(?P<line>\d+):(?P<col>\d+):\s*(?P<code>[A-Z]\d+)\s+(?P<msg>.+)$")
    _ERROR_PREFIXES = {"E", "F", "C9"}

    def parse(self, raw: str, file_path: Path, rule_prefix: str = "flake8") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        for line_txt in raw.splitlines():
            m = self._RE.match(line_txt.strip())
            if not m:
                continue
            code = m.group("code")
            ln   = int(m.group("line"))
            col  = int(m.group("col"))
            sev  = Severity.ERROR if any(code.startswith(p) for p in self._ERROR_PREFIXES) else Severity.WARNING
            ctx, ctx_start = _read_context(file_path, ln)
            issues.append(ValidationIssue(
                file_path=file_path, line=ln, col=col, severity=sev,
                rule=f"{rule_prefix}.{code.lower()}",
                message=f"[{code}] {m.group('msg')}",
                suggested_fix=f"See https://www.flake8rules.com/rules/{code}.html",
                context_lines=ctx, context_start=ctx_start,
            ))
        return issues


class MypyAdapter(FormatterAdapter):
    format = OutputFormat.MYPY
    _RE    = re.compile(
        r"^(?P<path>[^:]+):(?P<line>\d+):\s*(?P<sev>error|warning|note):\s*(?P<msg>.+?)(?:\s+\[(?P<code>[^\]]+)\])?$"
    )

    def parse(self, raw: str, file_path: Path, rule_prefix: str = "mypy") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        for line_txt in raw.splitlines():
            m = self._RE.match(line_txt.strip())
            if not m:
                continue
            ln   = int(m.group("line"))
            sev  = _map_severity(m.group("sev"))
            code = m.group("code") or "general"
            ctx, ctx_start = _read_context(file_path, ln)
            issues.append(ValidationIssue(
                file_path=file_path, line=ln, col=0, severity=sev,
                rule=f"{rule_prefix}.{code.replace('-','_')}",
                message=m.group("msg").strip(),
                suggested_fix=f"See https://mypy.readthedocs.io/en/stable/error_codes.html#{code}",
                context_lines=ctx, context_start=ctx_start,
            ))
        return issues


class EslintJsonAdapter(FormatterAdapter):
    format = OutputFormat.ESLINT_JSON

    def parse(self, raw: str, file_path: Path, rule_prefix: str = "eslint") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return issues
        records = data if isinstance(data, list) else [data]
        for record in records:
            for msg in record.get("messages", []):
                ln      = msg.get("line", 1)
                col     = msg.get("column", 0)
                sev     = Severity.ERROR if msg.get("severity", 1) >= 2 else Severity.WARNING
                rule_id = msg.get("ruleId") or "unknown"
                ctx, ctx_start = _read_context(file_path, ln)
                issues.append(ValidationIssue(
                    file_path=file_path, line=ln, col=col, severity=sev,
                    rule=f"{rule_prefix}.{rule_id.replace('/','.')}",
                    message=msg.get("message", ""),
                    suggested_fix=f"See https://eslint.org/docs/rules/{rule_id}",
                    context_lines=ctx, context_start=ctx_start,
                ))
        return issues


class PlainTextAdapter(FormatterAdapter):
    format   = OutputFormat.PLAIN_TEXT
    _PATTERNS = [
        re.compile(r"^(?P<path>[^:]+):(?P<line>\d+):(?P<col>\d+):\s*(?P<sev>\w+):\s*(?P<msg>.+)$"),
        re.compile(r"^(?P<path>[^:]+):(?P<line>\d+):\s*(?P<sev>error|warning|info|note):\s*(?P<msg>.+)$", re.I),
        re.compile(r"^(?P<sev>ERROR|WARNING|INFO)\s*:\s*(?P<msg>.+?)\s+\(at [^:]+:(?P<line>\d+)\)$", re.I),
    ]

    def parse(self, raw: str, file_path: Path, rule_prefix: str = "custom") -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        for line_txt in raw.splitlines():
            stripped = line_txt.strip()
            if not stripped:
                continue
            for pattern in self._PATTERNS:
                m = pattern.match(stripped)
                if m:
                    gd  = m.groupdict()
                    ln  = int(gd["line"]) if gd.get("line") else 1
                    col = int(gd["col"])  if gd.get("col")  else 0
                    sev = _map_severity(gd.get("sev", "warning"))
                    ctx, ctx_start = _read_context(file_path, ln)
                    issues.append(ValidationIssue(
                        file_path=file_path, line=ln, col=col, severity=sev,
                        rule=f"{rule_prefix}.generic",
                        message=gd.get("msg", stripped).strip(),
                        context_lines=ctx, context_start=ctx_start,
                    ))
                    break
        return issues


_ADAPTERS: list[FormatterAdapter] = [
    Flake8Adapter(), MypyAdapter(), EslintJsonAdapter(), PlainTextAdapter(),
]


def auto_detect(raw: str) -> FormatterAdapter:
    stripped = raw.strip()
    if stripped.startswith(("[", "{")):
        try:
            json.loads(stripped)
            return EslintJsonAdapter()
        except json.JSONDecodeError:
            pass
    if re.search(r":\d+:\d+:\s+[A-Z]\d{3}", raw):
        return Flake8Adapter()
    if re.search(r":\d+:\s+(error|note|warning):", raw):
        return MypyAdapter()
    return PlainTextAdapter()


def format_output(
    raw:            str,
    file_path:      Path,
    rule_prefix:    str                    = "custom",
    force_format:   Optional[OutputFormat] = None,
) -> List[ValidationIssue]:
    """Convert any supported tool stdout into a list of ValidationIssue objects."""
    if force_format is not None:
        adapter = {a.format: a for a in _ADAPTERS}.get(force_format, PlainTextAdapter())
    else:
        adapter = auto_detect(raw)
    return adapter.parse(raw, file_path, rule_prefix)
