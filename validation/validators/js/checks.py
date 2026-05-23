from __future__ import annotations

import re
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from ...core.base_validator import BaseValidator
from ...core.models import Severity, ValidationIssue


# ── helpers ────────────────────────────────────────────────────────────────────

def _ctx(lines: List[str], target: int, radius: int = 2) -> Tuple[List[str], int]:
    zero    = target - 1
    lo      = max(0, zero - radius)
    hi      = min(len(lines), zero + radius + 1)
    return lines[lo:hi], lo + 1


def _issue(
    file_path:  Path,
    line:       int,
    col:        int,
    severity:   Severity,
    rule:       str,
    message:    str,
    fix:        Optional[str],
    lines:      List[str],
) -> ValidationIssue:
    ctx, ctx_start = _ctx(lines, line)
    return ValidationIssue(
        file_path=file_path,
        line=line, col=col,
        severity=severity,
        rule=rule,
        message=message,
        suggested_fix=fix,
        context_lines=ctx,
        context_start=ctx_start,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Validator 1 — Node.js syntax check  (node --check)
# ══════════════════════════════════════════════════════════════════════════════

class JsSyntaxValidator(BaseValidator):
    name        = "js.syntax"
    language    = "javascript"

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        node_bin = shutil.which("node")
        if not node_bin:
            return [
                ValidationIssue(
                    file_path=file_path, line=0, col=0,
                    severity=Severity.WARNING,
                    rule="js.syntax.node_missing",
                    message="'node' not found on PATH — JS syntax check skipped.",
                    suggested_fix="Install Node.js: https://nodejs.org",
                )
            ]

        result = subprocess.run(
            [node_bin, "--check", str(file_path)],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return []

        lines       = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        stderr_txt  = result.stderr.strip()
        ln_match    = re.search(r":(\d+)\n", stderr_txt + "\n")
        ln          = int(ln_match.group(1)) if ln_match else 1
        ctx, ctx_start = _ctx(lines, ln)

        return [
            ValidationIssue(
                file_path=file_path, line=ln, col=0,
                severity=Severity.ERROR,
                rule="js.syntax.parse_error",
                message=f"Node syntax error: {stderr_txt}",
                suggested_fix="Fix the syntax error at the indicated line.",
                context_lines=ctx,
                context_start=ctx_start,
            )
        ]


# ══════════════════════════════════════════════════════════════════════════════
# Validator 2 — Unused variables / imports (regex heuristic)
# ══════════════════════════════════════════════════════════════════════════════

class JsUnusedVarValidator(BaseValidator):
    name        = "js.unused_vars"
    language    = "javascript"

    # Match: const/let/var FOO = / import FOO from / import { FOO } from
    _DECL_RE    = re.compile(
        r"""
        (?:
            (?:const|let|var)\s+(\w+)\s*=   # variable declaration
            |
            import\s+(\w+)\s+from            # default import
            |
            import\s*\{([^}]+)\}\s*from      # named imports
        )
        """,
        re.VERBOSE,
    )

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src     = file_path.read_text(encoding="utf-8", errors="replace")
        lines   = src.splitlines()
        issues: List[ValidationIssue] = []

        # Strip string literals and comments for usage analysis
        stripped = re.sub(r"//[^\n]*", " ", src)
        stripped = re.sub(r"/\*.*?\*/", " ", stripped, flags=re.DOTALL)
        stripped = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '""', stripped)
        stripped = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", "''", stripped)
        stripped = re.sub(r"`[^`\\]*(?:\\.[^`\\]*)*`", "``", stripped)

        for ln_idx, raw in enumerate(lines, start=1):
            # Named imports: import { A, B as C } from ...
            named_match = re.match(r"\s*import\s*\{([^}]+)\}\s*from", raw)
            if named_match:
                for part in named_match.group(1).split(","):
                    part = part.strip()
                    local = (part.split(" as ")[-1]).strip()
                    if local and not self._is_used(local, stripped, ln_idx, lines):
                        issues.append(
                            _issue(
                                file_path, ln_idx, 0,
                                Severity.WARNING,
                                "js.unused_vars.unused_import",
                                f"Imported name '{local}' is never used.",
                                f"Remove '{local}' from the import list or use it.",
                                lines,
                            )
                        )
                continue

            # Default import
            def_match = re.match(r"\s*import\s+(\w+)\s+from", raw)
            if def_match:
                name = def_match.group(1)
                if not self._is_used(name, stripped, ln_idx, lines):
                    issues.append(
                        _issue(
                            file_path, ln_idx, 0,
                            Severity.WARNING,
                            "js.unused_vars.unused_import",
                            f"Default import '{name}' is never used.",
                            f"Remove the import or reference '{name}' in your code.",
                            lines,
                        )
                    )
                continue

            # const/let declarations (skip destructuring for simplicity)
            decl_match = re.match(r"\s*(?:const|let|var)\s+(\w+)\s*=", raw)
            if decl_match:
                name = decl_match.group(1)
                if not self._is_used(name, stripped, ln_idx, lines):
                    issues.append(
                        _issue(
                            file_path, ln_idx, 0,
                            Severity.WARNING,
                            "js.unused_vars.unused_variable",
                            f"Variable '{name}' is declared but never used.",
                            f"Remove the declaration or use '{name}' later in the code.",
                            lines,
                        )
                    )

        return issues

    def _is_used(self, name: str, stripped: str, decl_line: int, lines: List[str]) -> bool:
        # Count occurrences of 'name' as whole word across entire file
        occurrences = len(re.findall(rf"\b{re.escape(name)}\b", stripped))
        # The declaration itself counts as 1 — used if found > 1 times
        return occurrences > 1


# ══════════════════════════════════════════════════════════════════════════════
# Validator 3 — console.log / debugger leftovers
# ══════════════════════════════════════════════════════════════════════════════

class JsDebugLeftoverValidator(BaseValidator):
    name        = "js.debug_leftovers"
    language    = "javascript"

    _PATTERNS = [
        (re.compile(r"\bconsole\.(log|warn|error|debug|info|trace)\b"), "console.{method}() call"),
        (re.compile(r"\bdebugger\b"),                                   "debugger statement"),
        (re.compile(r"\balert\s*\("),                                   "alert() call"),
    ]

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        lines   = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        issues: List[ValidationIssue] = []

        for ln_idx, raw in enumerate(lines, start=1):
            stripped = raw.strip()
            if stripped.startswith("//"):
                continue
            for pattern, label in self._PATTERNS:
                if pattern.search(raw):
                    issues.append(
                        _issue(
                            file_path, ln_idx, 0,
                            Severity.WARNING,
                            "js.debug_leftovers.found",
                            f"Debug leftover: {label} found.",
                            "Remove debug statements before committing to production.",
                            lines,
                        )
                    )
        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Validator 4 — Style checks (var usage, == vs ===, long lines, semicolons)
# ══════════════════════════════════════════════════════════════════════════════

class JsStyleValidator(BaseValidator):
    name        = "js.style"
    language    = "javascript"

    _MAX_LINE = 120

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        lines   = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        issues: List[ValidationIssue] = []

        for ln_idx, raw in enumerate(lines, start=1):
            stripped = raw.strip()

            # Skip comments
            if stripped.startswith("//") or stripped.startswith("*"):
                continue

            # var usage (prefer const/let)
            if re.search(r"\bvar\s+\w", raw):
                issues.append(
                    _issue(
                        file_path, ln_idx, 0,
                        Severity.WARNING,
                        "js.style.var_usage",
                        "Use of 'var' detected — prefer 'const' or 'let'.",
                        "Replace 'var' with 'const' (immutable) or 'let' (mutable).",
                        lines,
                    )
                )

            # == vs ===  (loose equality)
            if re.search(r"(?<!=)={2}(?!=)", raw) and "=>" not in raw:
                issues.append(
                    _issue(
                        file_path, ln_idx, 0,
                        Severity.WARNING,
                        "js.style.loose_equality",
                        "Loose equality '==' used — prefer strict '==='.",
                        "Replace '==' with '===' (and '!=' with '!==').",
                        lines,
                    )
                )

            # Line length
            if len(raw) > self._MAX_LINE:
                issues.append(
                    _issue(
                        file_path, ln_idx, self._MAX_LINE + 1,
                        Severity.WARNING,
                        "js.style.line_too_long",
                        f"Line is {len(raw)} chars (max {self._MAX_LINE}).",
                        "Break the line or extract a helper.",
                        lines,
                    )
                )

            # Missing semicolons on statement lines
            if (
                stripped
                and not stripped.endswith(("{", "}", "(", ",", ":", "\\", "=>", ";"))
                and not stripped.startswith(("//", "/*", "*", "import ", "export ", "if", "else", "for", "while", "function", "class", "try", "catch"))
                and re.match(r"^(const|let|var|return|throw)\s", stripped)
            ):
                issues.append(
                    _issue(
                        file_path, ln_idx, len(raw),
                        Severity.WARNING,
                        "js.style.missing_semicolon",
                        "Statement appears to be missing a trailing semicolon.",
                        "Add ';' at the end of the statement.",
                        lines,
                    )
                )

        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Validator 5 — Security patterns (eval, innerHTML, dangerous APIs)
# ══════════════════════════════════════════════════════════════════════════════

class JsSecurityValidator(BaseValidator):
    name        = "js.security"
    language    = "javascript"

    _PATTERNS = [
        (re.compile(r"\beval\s*\("),                "eval() usage — arbitrary code execution risk"),
        (re.compile(r"\.innerHTML\s*="),             "innerHTML assignment — XSS risk"),
        (re.compile(r"\.outerHTML\s*="),             "outerHTML assignment — XSS risk"),
        (re.compile(r"document\.write\s*\("),        "document.write() — XSS and performance risk"),
        (re.compile(r"\bnew\s+Function\s*\("),       "new Function() — arbitrary code execution risk"),
        (re.compile(r"setTimeout\s*\(\s*['\"]"),     "setTimeout with string argument — eval equivalent"),
        (re.compile(r"setInterval\s*\(\s*['\"]"),    "setInterval with string argument — eval equivalent"),
    ]

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        lines   = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        issues: List[ValidationIssue] = []

        for ln_idx, raw in enumerate(lines, start=1):
            if raw.strip().startswith("//"):
                continue
            for pattern, label in self._PATTERNS:
                if pattern.search(raw):
                    issues.append(
                        _issue(
                            file_path, ln_idx, 0,
                            Severity.ERROR,
                            "js.security.dangerous_api",
                            f"Security risk: {label}.",
                            "Avoid this pattern. Use safer alternatives or sanitize all inputs.",
                            lines,
                        )
                    )
        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Registry
# ══════════════════════════════════════════════════════════════════════════════

ALL_VALIDATORS: List[BaseValidator] = [
    JsSyntaxValidator(),
    JsUnusedVarValidator(),
    JsDebugLeftoverValidator(),
    JsStyleValidator(),
    JsSecurityValidator(),
]
