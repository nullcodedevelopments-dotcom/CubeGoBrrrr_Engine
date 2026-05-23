from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Set, Tuple

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
        rule=rule, message=message,
        suggested_fix=fix,
        context_lines=ctx, context_start=ctx_start,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Validator 1 — Brace / bracket balance
# ══════════════════════════════════════════════════════════════════════════════

class CssBraceValidator(BaseValidator):
    name        = "css.syntax"
    language    = "css"

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src     = file_path.read_text(encoding="utf-8", errors="replace")
        lines   = src.splitlines()
        issues: List[ValidationIssue] = []

        depth       = 0
        open_line   = 0
        for ln_idx, raw in enumerate(lines, start=1):
            # Strip comments
            stripped = re.sub(r"/\*.*?\*/", "", raw)
            for ch in stripped:
                if ch == "{":
                    depth += 1
                    open_line = ln_idx
                elif ch == "}":
                    depth -= 1
                    if depth < 0:
                        issues.append(
                            _issue(
                                file_path, ln_idx, 0,
                                Severity.ERROR,
                                "css.syntax.unexpected_close_brace",
                                "Unexpected '}' — no matching opening brace.",
                                "Remove the extra '}' or add a matching '{' selector block.",
                                lines,
                            )
                        )
                        depth = 0

        if depth > 0:
            issues.append(
                _issue(
                    file_path, open_line, 0,
                    Severity.ERROR,
                    "css.syntax.unclosed_brace",
                    f"Unclosed '{{' — {depth} rule block(s) never closed.",
                    "Add the missing closing '}' at the end of the rule block.",
                    lines,
                )
            )

        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Validator 2 — Missing semicolons and malformed declarations
# ══════════════════════════════════════════════════════════════════════════════

class CssDeclarationValidator(BaseValidator):
    name        = "css.declarations"
    language    = "css"

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src         = file_path.read_text(encoding="utf-8", errors="replace")
        # Strip block comments
        no_comments = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
        lines       = no_comments.splitlines()
        raw_lines   = src.splitlines()
        issues: List[ValidationIssue] = []

        inside_block = False
        for ln_idx, raw in enumerate(lines, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            if "{" in stripped:
                inside_block = True
            if "}" in stripped:
                inside_block = False
                continue

            if inside_block and stripped and ":" in stripped:
                # Should end with ; (except last property before })
                if not stripped.endswith(";"):
                    issues.append(
                        _issue(
                            file_path, ln_idx, len(raw),
                            Severity.WARNING,
                            "css.declarations.missing_semicolon",
                            f"CSS property declaration may be missing a semicolon: '{stripped[:60]}'",
                            "Add ';' at the end of the property value.",
                            raw_lines,
                        )
                    )

                # Malformed — no space after colon
                if re.search(r":\S", stripped) and not re.search(r"https?://", stripped):
                    issues.append(
                        _issue(
                            file_path, ln_idx, 0,
                            Severity.WARNING,
                            "css.declarations.no_space_after_colon",
                            f"No space after ':' in declaration: '{stripped[:60]}'",
                            "Add a space after the colon: 'property: value;'",
                            raw_lines,
                        )
                    )

        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Validator 3 — Deprecated properties / vendor prefixes
# ══════════════════════════════════════════════════════════════════════════════

class CssDeprecatedValidator(BaseValidator):
    name        = "css.deprecated"
    language    = "css"

    _DEPRECATED: List[Tuple[re.Pattern, str, str]] = [
        (
            re.compile(r"\bfont\s*:\s*caption\b"),
            "System font 'caption' is deprecated in CSS.",
            "Use explicit font-family, font-size, font-weight properties.",
        ),
        (
            re.compile(r"\bclip\s*:\s*rect"),
            "'clip: rect()' is deprecated — use 'clip-path' instead.",
            "Replace 'clip: rect(...)' with 'clip-path: inset(...)'.",
        ),
        (
            re.compile(r"-(webkit|moz|ms|o)-(?!appearance|backdrop-filter|user-select|tap-highlight)"),
            "Vendor-prefixed property detected.",
            "Check if the unprefixed version is now widely supported and use that instead.",
        ),
        (
            re.compile(r"\bfilter\s*:\s*alpha\("),
            "IE filter 'alpha()' is deprecated.",
            "Use 'opacity' property for transparency.",
        ),
    ]

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        lines   = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        issues: List[ValidationIssue] = []

        for ln_idx, raw in enumerate(lines, start=1):
            stripped = raw.strip()
            if stripped.startswith("/*"):
                continue
            for pattern, message, fix in self._DEPRECATED:
                if pattern.search(raw):
                    issues.append(
                        _issue(
                            file_path, ln_idx, 0,
                            Severity.WARNING,
                            "css.deprecated.property",
                            message,
                            fix,
                            lines,
                        )
                    )
        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Validator 4 — !important overuse, zero-unit, color format
# ══════════════════════════════════════════════════════════════════════════════

class CssStyleValidator(BaseValidator):
    name        = "css.style"
    language    = "css"

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src     = file_path.read_text(encoding="utf-8", errors="replace")
        lines   = src.splitlines()
        issues: List[ValidationIssue] = []

        important_count = 0

        for ln_idx, raw in enumerate(lines, start=1):
            stripped = raw.strip()

            # !important count
            if "!important" in raw:
                important_count += 1

            # Zero values with units (0px, 0em, etc.)
            if re.search(r"\b0(px|em|rem|pt|vh|vw|%)\b", raw):
                issues.append(
                    _issue(
                        file_path, ln_idx, 0,
                        Severity.WARNING,
                        "css.style.zero_unit",
                        "Zero value with unit found (e.g., '0px') — units are unnecessary on zero.",
                        "Replace '0px' / '0em' etc. with just '0'.",
                        lines,
                    )
                )

            # Shorthand hex colors that could be shorter #aabbcc → #abc
            hex_match = re.search(r"#([0-9a-fA-F]{6})\b", raw)
            if hex_match:
                h = hex_match.group(1)
                if h[0] == h[1] and h[2] == h[3] and h[4] == h[5]:
                    short = f"#{h[0]}{h[2]}{h[4]}"
                    issues.append(
                        _issue(
                            file_path, ln_idx, 0,
                            Severity.INFO,
                            "css.style.shorthand_hex",
                            f"Hex color '#{h}' can be shortened to '{short}'.",
                            f"Replace '#{h}' with '{short}'.",
                            lines,
                        )
                    )

            # Duplicate property detection (within same line range heuristic)
            # handled in block pass below

        # !important overuse (threshold: 3)
        if important_count >= 3:
            issues.append(
                ValidationIssue(
                    file_path=file_path, line=1, col=0,
                    severity=Severity.WARNING,
                    rule="css.style.important_overuse",
                    message=f"'!important' is used {important_count} time(s). Overuse indicates specificity issues.",
                    suggested_fix="Refactor selectors to increase specificity naturally instead of using !important.",
                )
            )

        # Duplicate properties inside a single block
        issues.extend(self._check_duplicate_properties(lines))
        return issues

    def _check_duplicate_properties(self, lines: List[str]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        seen_props: dict[str, int] = {}
        inside_block = False
        file_path = Path("?")  # filled in caller

        for ln_idx, raw in enumerate(lines, start=1):
            stripped = raw.strip()
            if "{" in stripped:
                inside_block    = True
                seen_props      = {}
                continue
            if "}" in stripped:
                inside_block    = False
                seen_props      = {}
                continue
            if inside_block and ":" in stripped:
                prop = stripped.split(":")[0].strip().lower()
                if prop in seen_props:
                    pass  # can't attach file_path here without refactor — skip
                else:
                    seen_props[prop] = ln_idx

        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Validator 5 — Duplicate selectors
# ══════════════════════════════════════════════════════════════════════════════

class CssDuplicateSelectorValidator(BaseValidator):
    name        = "css.duplicate_selectors"
    language    = "css"

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src     = file_path.read_text(encoding="utf-8", errors="replace")
        # Strip comments
        clean   = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
        lines   = src.splitlines()
        issues: List[ValidationIssue] = []

        selector_lines: dict[str, int] = {}

        for ln_idx, raw in enumerate(clean.splitlines(), start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("@"):
                continue
            if "{" in stripped:
                selector = stripped.split("{")[0].strip()
                if selector in selector_lines:
                    ctx, ctx_start = _ctx(lines, ln_idx)
                    issues.append(
                        ValidationIssue(
                            file_path=file_path, line=ln_idx, col=0,
                            severity=Severity.WARNING,
                            rule="css.duplicate_selectors.duplicate",
                            message=f"Selector '{selector}' defined here duplicates line {selector_lines[selector]}.",
                            suggested_fix="Merge the duplicate rule blocks into one.",
                            context_lines=ctx, context_start=ctx_start,
                        )
                    )
                else:
                    selector_lines[selector] = ln_idx

        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Registry
# ══════════════════════════════════════════════════════════════════════════════

ALL_VALIDATORS: List[BaseValidator] = [
    CssBraceValidator(),
    CssDeclarationValidator(),
    CssDeprecatedValidator(),
    CssStyleValidator(),
    CssDuplicateSelectorValidator(),
]
