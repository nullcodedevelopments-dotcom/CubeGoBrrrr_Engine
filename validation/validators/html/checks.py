from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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
        file_path=file_path, line=line, col=col,
        severity=severity, rule=rule, message=message,
        suggested_fix=fix, context_lines=ctx, context_start=ctx_start,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Tracking HTML parser
# ══════════════════════════════════════════════════════════════════════════════

class _TrackingParser(HTMLParser):
    """HTMLParser subclass that tracks (line, col) for each tag."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.events: List[Tuple[str, str, dict, int, int]] = []
        # (type, tag, attrs_dict, line, col)
        self.errors: List[Tuple[str, int, int]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        ln, col = self.getpos()
        self.events.append(("open", tag, dict(attrs), ln, col))

    def handle_endtag(self, tag: str) -> None:
        ln, col = self.getpos()
        self.events.append(("close", tag, {}, ln, col))

    def handle_error(self, message: str) -> None:
        ln, col = self.getpos()
        self.errors.append((message, ln, col))


# ══════════════════════════════════════════════════════════════════════════════
# Validator 1 — Tag structure & nesting
# ══════════════════════════════════════════════════════════════════════════════

# Tags that must never be nested inside themselves
_NO_SELF_NEST: Set[str] = {"a", "button", "label", "form", "p"}

# Void / self-closing tags that must NOT have closing tags
_VOID_TAGS: Set[str] = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class HtmlStructureValidator(BaseValidator):
    name        = "html.structure"
    language    = "html"

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src     = file_path.read_text(encoding="utf-8", errors="replace")
        lines   = src.splitlines()
        issues: List[ValidationIssue] = []
        parser  = _TrackingParser()

        try:
            parser.feed(src)
        except Exception:
            pass

        # Stack-based tag matching
        stack: List[Tuple[str, int, int]] = []  # (tag, line, col)

        for ev_type, tag, attrs, ln, col in parser.events:
            if ev_type == "open":
                if tag not in _VOID_TAGS:
                    stack.append((tag, ln, col))
            elif ev_type == "close":
                if tag in _VOID_TAGS:
                    issues.append(
                        _issue(
                            file_path, ln, col,
                            Severity.WARNING,
                            "html.structure.void_closing_tag",
                            f"Void element <{tag}> should not have a closing tag </{tag}>.",
                            f"Remove the closing '</{tag}>' — void elements are self-closing.",
                            lines,
                        )
                    )
                    continue

                if stack and stack[-1][0] == tag:
                    stack.pop()
                else:
                    # Find most recent matching open tag
                    idx = next(
                        (i for i in range(len(stack) - 1, -1, -1) if stack[i][0] == tag),
                        None,
                    )
                    if idx is not None:
                        unclosed = stack[idx + 1:]
                        for unc_tag, unc_ln, _ in unclosed:
                            issues.append(
                                _issue(
                                    file_path, unc_ln, 0,
                                    Severity.ERROR,
                                    "html.structure.unclosed_tag",
                                    f"<{unc_tag}> opened here was never properly closed.",
                                    f"Add '</{unc_tag}>' at the correct closing position.",
                                    lines,
                                )
                            )
                        stack = stack[:idx]
                    else:
                        issues.append(
                            _issue(
                                file_path, ln, col,
                                Severity.ERROR,
                                "html.structure.unexpected_close_tag",
                                f"Closing tag '</{tag}>' has no matching opening tag.",
                                f"Remove '</{tag}>' or add the opening '<{tag}>' tag.",
                                lines,
                            )
                        )

        # Remaining unclosed tags
        for unc_tag, unc_ln, _ in stack:
            issues.append(
                _issue(
                    file_path, unc_ln, 0,
                    Severity.ERROR,
                    "html.structure.unclosed_tag",
                    f"<{unc_tag}> is never closed.",
                    f"Add '</{unc_tag}>' at the appropriate location.",
                    lines,
                )
            )

        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Validator 2 — Accessibility (alt, aria, lang, etc.)
# ══════════════════════════════════════════════════════════════════════════════

class HtmlA11yValidator(BaseValidator):
    name        = "html.accessibility"
    language    = "html"

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src     = file_path.read_text(encoding="utf-8", errors="replace")
        lines   = src.splitlines()
        parser  = _TrackingParser()
        try:
            parser.feed(src)
        except Exception:
            pass

        issues: List[ValidationIssue] = []

        # Track <html lang="...">
        has_lang = False

        for ev_type, tag, attrs, ln, col in parser.events:
            if ev_type != "open":
                continue

            # <html> must have lang attribute
            if tag == "html":
                if "lang" not in attrs:
                    issues.append(
                        _issue(
                            file_path, ln, col,
                            Severity.WARNING,
                            "html.a11y.missing_lang",
                            "<html> element is missing the 'lang' attribute.",
                            "Add lang='en' (or appropriate language code) to <html>.",
                            lines,
                        )
                    )
                has_lang = True

            # <img> must have alt attribute
            if tag == "img":
                if "alt" not in attrs:
                    issues.append(
                        _issue(
                            file_path, ln, col,
                            Severity.WARNING,
                            "html.a11y.img_missing_alt",
                            "<img> element is missing the 'alt' attribute.",
                            "Add alt='' for decorative images or alt='description' for informative images.",
                            lines,
                        )
                    )

            # <a> should have meaningful text (skip checking — complex, needs content)
            if tag == "a":
                href = attrs.get("href", "")
                if href == "#":
                    issues.append(
                        _issue(
                            file_path, ln, col,
                            Severity.WARNING,
                            "html.a11y.empty_href",
                            "<a href='#'> found — placeholder anchor may cause accessibility issues.",
                            "Use a real href, or use a <button> if this triggers an action.",
                            lines,
                        )
                    )

            # <input> should have associated label or aria-label
            if tag == "input":
                itype = attrs.get("type", "text").lower()
                if itype not in {"hidden", "submit", "button", "reset", "image"}:
                    has_label = (
                        "aria-label" in attrs
                        or "aria-labelledby" in attrs
                        or "id" in attrs      # assume a <label for="id"> exists somewhere
                        or "title" in attrs
                    )
                    if not has_label:
                        issues.append(
                            _issue(
                                file_path, ln, col,
                                Severity.WARNING,
                                "html.a11y.input_missing_label",
                                f"<input type='{itype}'> has no accessible label (aria-label / id for label).",
                                "Add aria-label='...' or pair with a <label for='...'> element.",
                                lines,
                            )
                        )

            # <button> with no visible text / aria
            if tag == "button":
                if "aria-label" not in attrs and "aria-labelledby" not in attrs and "title" not in attrs:
                    # heuristic only — content check requires parsing
                    pass

        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Validator 3 — Document structure (doctype, head, title, charset)
# ══════════════════════════════════════════════════════════════════════════════

class HtmlDocStructureValidator(BaseValidator):
    name        = "html.doc_structure"
    language    = "html"

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src     = file_path.read_text(encoding="utf-8", errors="replace")
        lines   = src.splitlines()
        issues: List[ValidationIssue] = []

        lower = src.lower()

        # <!DOCTYPE html>
        if not re.search(r"<!doctype\s+html", lower):
            issues.append(
                _issue(
                    file_path, 1, 0,
                    Severity.WARNING,
                    "html.doc_structure.missing_doctype",
                    "Document is missing '<!DOCTYPE html>' declaration.",
                    "Add '<!DOCTYPE html>' as the very first line of the file.",
                    lines,
                )
            )

        # <title>
        if "<title>" not in lower or "</title>" not in lower:
            issues.append(
                _issue(
                    file_path, 1, 0,
                    Severity.WARNING,
                    "html.doc_structure.missing_title",
                    "Document is missing a <title> element.",
                    "Add <title>Your Page Title</title> inside the <head> section.",
                    lines,
                )
            )

        # charset meta
        if not re.search(r'<meta[^>]+charset', lower):
            issues.append(
                _issue(
                    file_path, 1, 0,
                    Severity.WARNING,
                    "html.doc_structure.missing_charset",
                    "Document is missing a charset meta tag.",
                    "Add <meta charset='UTF-8'> inside <head>.",
                    lines,
                )
            )

        # viewport meta
        if not re.search(r'<meta[^>]+viewport', lower):
            issues.append(
                _issue(
                    file_path, 1, 0,
                    Severity.INFO,
                    "html.doc_structure.missing_viewport",
                    "Document is missing a viewport meta tag (needed for responsive design).",
                    "Add <meta name='viewport' content='width=device-width, initial-scale=1.0'>.",
                    lines,
                )
            )

        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Validator 4 — Inline styles & deprecated attributes
# ══════════════════════════════════════════════════════════════════════════════

class HtmlStyleValidator(BaseValidator):
    name        = "html.style"
    language    = "html"

    _DEPRECATED_ATTRS: Set[str] = {
        "align", "bgcolor", "border", "cellpadding", "cellspacing",
        "color", "face", "height", "hspace", "marginheight", "marginwidth",
        "noshade", "nowrap", "size", "valign", "vspace", "width",
    }

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src     = file_path.read_text(encoding="utf-8", errors="replace")
        lines   = src.splitlines()
        parser  = _TrackingParser()
        try:
            parser.feed(src)
        except Exception:
            pass

        issues: List[ValidationIssue] = []

        for ev_type, tag, attrs, ln, col in parser.events:
            if ev_type != "open":
                continue

            # Inline style
            if "style" in attrs:
                issues.append(
                    _issue(
                        file_path, ln, col,
                        Severity.WARNING,
                        "html.style.inline_style",
                        f"<{tag}> uses an inline 'style' attribute.",
                        "Move inline styles to an external or embedded stylesheet.",
                        lines,
                    )
                )

            # Deprecated presentational attributes
            for attr in attrs:
                if attr in self._DEPRECATED_ATTRS:
                    issues.append(
                        _issue(
                            file_path, ln, col,
                            Severity.WARNING,
                            "html.style.deprecated_attribute",
                            f"<{tag}> uses deprecated presentational attribute '{attr}'.",
                            f"Remove '{attr}' and use CSS instead.",
                            lines,
                        )
                    )

        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Validator 5 — Security (target=_blank without rel, inline event handlers)
# ══════════════════════════════════════════════════════════════════════════════

class HtmlSecurityValidator(BaseValidator):
    name        = "html.security"
    language    = "html"

    _INLINE_EVENTS = re.compile(
        r'\bon\w+\s*=',
        re.IGNORECASE,
    )

    def _run(self, file_path: Path) -> List[ValidationIssue]:
        src     = file_path.read_text(encoding="utf-8", errors="replace")
        lines   = src.splitlines()
        parser  = _TrackingParser()
        try:
            parser.feed(src)
        except Exception:
            pass

        issues: List[ValidationIssue] = []

        for ev_type, tag, attrs, ln, col in parser.events:
            if ev_type != "open":
                continue

            # target=_blank without rel=noopener
            if attrs.get("target") == "_blank":
                rel = attrs.get("rel", "")
                if "noopener" not in rel and "noreferrer" not in rel:
                    issues.append(
                        _issue(
                            file_path, ln, col,
                            Severity.WARNING,
                            "html.security.blank_no_rel",
                            f"<{tag} target='_blank'> is missing rel='noopener noreferrer'.",
                            "Add rel='noopener noreferrer' to prevent tab-napping attacks.",
                            lines,
                        )
                    )

        # Inline event handlers (onerror=, onclick=, onload=, etc.)
        for ln_idx, raw in enumerate(lines, start=1):
            if self._INLINE_EVENTS.search(raw):
                ctx, ctx_start = _ctx(lines, ln_idx)
                issues.append(
                    ValidationIssue(
                        file_path=file_path, line=ln_idx, col=0,
                        severity=Severity.WARNING,
                        rule="html.security.inline_event_handler",
                        message="Inline event handler detected (on* attribute).",
                        suggested_fix="Move event handling to JavaScript using addEventListener().",
                        context_lines=ctx, context_start=ctx_start,
                    )
                )

        return issues


# ══════════════════════════════════════════════════════════════════════════════
# Registry
# ══════════════════════════════════════════════════════════════════════════════

ALL_VALIDATORS: List[BaseValidator] = [
    HtmlDocStructureValidator(),
    HtmlStructureValidator(),
    HtmlA11yValidator(),
    HtmlStyleValidator(),
    HtmlSecurityValidator(),
]
