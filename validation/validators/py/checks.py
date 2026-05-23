from __future__ import annotations

import ast
import builtins
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Set

from ...core.base_validator import BaseValidator
from ...core.models import Severity, ValidationIssue


# ── helpers ────────────────────────────────────────────────────────────────────

def _issue(
    file_path:      Path,
    line:           int,
    col:            int,
    severity:       Severity,
    rule:           str,
    message:        str,
    fix:            str | None,
    lines:          List[str],
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


def _ctx(lines: List[str], target: int, radius: int = 2):
    zero    = target - 1
    lo      = max(0, zero - radius)
    hi      = min(len(lines), zero + radius + 1)
    return lines[lo:hi], lo + 1


# ══════════════════════════════════════════════════════════════════════════════
# Validator 1 — Syntax (ast.parse)
# ══════════════════════════════════════════════════════════════════════════════

class PySyntaxValidator(BaseValidator):
    name        = "py.syntax"
    language    = "python"

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src = file_path.read_text(encoding="utf-8", errors="replace")
        try:
            ast.parse(src, filename=str(file_path))
        except SyntaxError as exc:
            lines   = src.splitlines()
            ln      = exc.lineno or 1
            col     = exc.offset or 0
            ctx, ctx_start = _ctx(lines, ln)
            return [
                ValidationIssue(
                    file_path=file_path,
                    line=ln, col=col,
                    severity=Severity.ERROR,
                    rule="py.syntax.parse_error",
                    message=f"SyntaxError: {exc.msg}",
                    suggested_fix="Fix the syntax error at the indicated line before running other checks.",
                    context_lines=ctx,
                    context_start=ctx_start,
                )
            ]
        return []


# ══════════════════════════════════════════════════════════════════════════════
# Validator 2 — Unused imports (AST walk)
# ══════════════════════════════════════════════════════════════════════════════

class PyUnusedImportValidator(BaseValidator):
    name        = "py.unused_imports"
    language    = "python"

    # Names that are considered "used" even if not referenced in code
    _ALWAYS_KEEP: Set[str] = {
        "__future__", "annotations", "TYPE_CHECKING",
        "__all__", "typing",
    }

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src = file_path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src, filename=str(file_path))
        except SyntaxError:
            return []   # syntax validator handles this

        lines = src.splitlines()

        # Collect all imported names → {alias_used_in_code: (import_line, original)}
        imported: dict[str, tuple[int, str]] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local_name  = alias.asname or alias.name.split(".")[0]
                    original    = alias.name
                    imported[local_name] = (node.lineno, original)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module in self._ALWAYS_KEEP:
                    continue
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    local_name  = alias.asname or alias.name
                    imported[local_name] = (node.lineno, f"{module}.{alias.name}")

        # Collect all name references in code (excluding import statements)
        used_names: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # collect root of attribute access  e.g. os.path → os
                root = node
                while isinstance(root, ast.Attribute):
                    root = root.value
                if isinstance(root, ast.Name):
                    used_names.add(root.id)

        # Also scan raw string for __all__ list references
        all_match = re.search(r"__all__\s*=\s*\[([^\]]+)\]", src)
        if all_match:
            for name in re.findall(r"['\"](\w+)['\"]", all_match.group(1)):
                used_names.add(name)

        issues: List[ValidationIssue] = []
        for local_name, (ln, original) in imported.items():
            if local_name in self._ALWAYS_KEEP:
                continue
            if local_name not in used_names:
                issues.append(
                    _issue(
                        file_path, ln, 0,
                        Severity.WARNING,
                        "py.unused_imports.unused",
                        f"Imported name '{local_name}' (from '{original}') is never used.",
                        f"Remove 'import {original}' or use the imported name.",
                        lines,
                    )
                )
        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Validator 3 — Compile check (py_compile)
# ══════════════════════════════════════════════════════════════════════════════

class PyCompileValidator(BaseValidator):
    name        = "py.compile"
    language    = "python"

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(file_path)],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            return []

        lines       = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        stderr_txt  = result.stderr.strip()

        # Parse "File ..., line N" from py_compile output
        ln_match = re.search(r"line (\d+)", stderr_txt)
        ln = int(ln_match.group(1)) if ln_match else 1
        ctx, ctx_start = _ctx(lines, ln)

        return [
            ValidationIssue(
                file_path=file_path,
                line=ln, col=0,
                severity=Severity.ERROR,
                rule="py.compile.compile_error",
                message=f"Compile failed: {stderr_txt}",
                suggested_fix="Fix all syntax or encoding errors before compiling.",
                context_lines=ctx,
                context_start=ctx_start,
            )
        ]


# ══════════════════════════════════════════════════════════════════════════════
# Validator 4 — Style / code-quality (AST heuristics)
# ══════════════════════════════════════════════════════════════════════════════

class PyStyleValidator(BaseValidator):
    name        = "py.style"
    language    = "python"

    _MAX_LINE_LEN   = 120
    _MAX_FUNC_LINES = 60
    _MAX_ARGS       = 7

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src     = file_path.read_text(encoding="utf-8", errors="replace")
        lines   = src.splitlines()
        issues: List[ValidationIssue] = []

        try:
            tree = ast.parse(src, filename=str(file_path))
        except SyntaxError:
            return []

        # Line length
        for idx, raw_line in enumerate(lines, start=1):
            if len(raw_line) > self._MAX_LINE_LEN:
                ctx, ctx_start = _ctx(lines, idx)
                issues.append(
                    ValidationIssue(
                        file_path=file_path,
                        line=idx, col=self._MAX_LINE_LEN + 1,
                        severity=Severity.WARNING,
                        rule="py.style.line_too_long",
                        message=f"Line {idx} is {len(raw_line)} chars (max {self._MAX_LINE_LEN}).",
                        suggested_fix=f"Break the line or extract a variable to stay under {self._MAX_LINE_LEN} chars.",
                        context_lines=ctx,
                        context_start=ctx_start,
                    )
                )

        # Function length & arg count
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_line    = getattr(node, "end_lineno", node.lineno)
                func_len    = end_line - node.lineno + 1
                n_args      = len(node.args.args)

                if func_len > self._MAX_FUNC_LINES:
                    ctx, ctx_start = _ctx(lines, node.lineno)
                    issues.append(
                        ValidationIssue(
                            file_path=file_path,
                            line=node.lineno, col=0,
                            severity=Severity.WARNING,
                            rule="py.style.function_too_long",
                            message=f"Function '{node.name}' is {func_len} lines (max {self._MAX_FUNC_LINES}).",
                            suggested_fix="Consider splitting the function into smaller, focused helpers.",
                            context_lines=ctx,
                            context_start=ctx_start,
                        )
                    )

                if n_args > self._MAX_ARGS:
                    ctx, ctx_start = _ctx(lines, node.lineno)
                    issues.append(
                        ValidationIssue(
                            file_path=file_path,
                            line=node.lineno, col=0,
                            severity=Severity.WARNING,
                            rule="py.style.too_many_arguments",
                            message=f"Function '{node.name}' has {n_args} arguments (max {self._MAX_ARGS}).",
                            suggested_fix="Group related arguments into a dataclass or config dict.",
                            context_lines=ctx,
                            context_start=ctx_start,
                        )
                    )

        # Bare except
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                ctx, ctx_start = _ctx(lines, node.lineno)
                issues.append(
                    ValidationIssue(
                        file_path=file_path,
                        line=node.lineno, col=0,
                        severity=Severity.WARNING,
                        rule="py.style.bare_except",
                        message="Bare 'except:' catches all exceptions including KeyboardInterrupt.",
                        suggested_fix="Use 'except Exception:' or catch specific exception types.",
                        context_lines=ctx,
                        context_start=ctx_start,
                    )
                )

        # Mutable default arguments  def f(x=[]) / def f(x={})
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        ctx, ctx_start = _ctx(lines, node.lineno)
                        issues.append(
                            ValidationIssue(
                                file_path=file_path,
                                line=node.lineno, col=0,
                                severity=Severity.WARNING,
                                rule="py.style.mutable_default_arg",
                                message=f"Function '{node.name}' uses a mutable default argument (list/dict/set).",
                                suggested_fix="Replace mutable default with None and initialize inside the function body.",
                                context_lines=ctx,
                                context_start=ctx_start,
                            )
                        )

        # Undefined names (basic, ignores builtins + globals defined in file)
        defined_names: Set[str] = set(dir(builtins))
        for node in ast.walk(tree):
            if isinstance(node, (
                ast.FunctionDef, ast.AsyncFunctionDef,
                ast.ClassDef, ast.Global, ast.Nonlocal,
            )):
                defined_names.add(getattr(node, "name", ""))
            if isinstance(node, (ast.Import,)):
                for alias in node.names:
                    defined_names.add(alias.asname or alias.name.split(".")[0])
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    defined_names.add(alias.asname or alias.name)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_names.add(target.id)
            if isinstance(node, (ast.For, ast.comprehension)):
                target = getattr(node, "target", None)
                if target and isinstance(target, ast.Name):
                    defined_names.add(target.id)
            if isinstance(node, ast.arg):
                defined_names.add(node.arg)

        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Validator 5 — Complexity (cyclomatic, nesting depth)
# ══════════════════════════════════════════════════════════════════════════════

class PyComplexityValidator(BaseValidator):
    name        = "py.complexity"
    language    = "python"

    _MAX_CYCLO      = 10
    _MAX_NESTING    = 5

    # AST nodes that add a branch
    _BRANCH_NODES = (
        ast.If, ast.While, ast.For, ast.ExceptHandler,
        ast.With, ast.Assert, ast.comprehension,
    )

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src = file_path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src, filename=str(file_path))
        except SyntaxError:
            return []

        lines   = src.splitlines()
        issues: List[ValidationIssue] = []

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            # Cyclomatic complexity (count branches + 1)
            complexity = 1 + sum(
                1 for child in ast.walk(node)
                if isinstance(child, self._BRANCH_NODES)
            )

            if complexity > self._MAX_CYCLO:
                ctx, ctx_start = _ctx(lines, node.lineno)
                issues.append(
                    ValidationIssue(
                        file_path=file_path,
                        line=node.lineno, col=0,
                        severity=Severity.WARNING,
                        rule="py.complexity.cyclomatic",
                        message=f"Function '{node.name}' has cyclomatic complexity {complexity} (max {self._MAX_CYCLO}).",
                        suggested_fix="Break the function into smaller functions or simplify conditional logic.",
                        context_lines=ctx,
                        context_start=ctx_start,
                    )
                )

            # Max nesting depth
            max_depth = self._nesting_depth(node)
            if max_depth > self._MAX_NESTING:
                ctx, ctx_start = _ctx(lines, node.lineno)
                issues.append(
                    ValidationIssue(
                        file_path=file_path,
                        line=node.lineno, col=0,
                        severity=Severity.WARNING,
                        rule="py.complexity.nesting_depth",
                        message=f"Function '{node.name}' has nesting depth {max_depth} (max {self._MAX_NESTING}).",
                        suggested_fix="Use early returns, extract helpers, or flatten nested logic.",
                        context_lines=ctx,
                        context_start=ctx_start,
                    )
                )

        return issues

    def _nesting_depth(self, node: ast.AST, current: int = 0) -> int:
        _SCOPE = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)
        max_d = current
        for child in ast.iter_child_nodes(node):
            add = 1 if isinstance(child, _SCOPE) else 0
            max_d = max(max_d, self._nesting_depth(child, current + add))
        return max_d


# ══════════════════════════════════════════════════════════════════════════════
# Registry — all Python validators in execution order
# ══════════════════════════════════════════════════════════════════════════════

ALL_VALIDATORS: List[BaseValidator] = [
    PySyntaxValidator(),
    PyCompileValidator(),
    PyUnusedImportValidator(),
    PyStyleValidator(),
    PyComplexityValidator(),
]
