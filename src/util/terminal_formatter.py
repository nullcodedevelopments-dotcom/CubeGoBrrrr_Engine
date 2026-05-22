"""
Workspace-wide terminal output formatting.

Zero external dependencies — uses ANSI escape codes only.
Automatically disables colour when stdout is not a TTY (pipes, logs, CI).

USAGE:
    from src.util.terminal_formatter import (
        cprint, status_badge, draw_table, progress_bar, section_header
    )

    cprint("Deadline loaded", style="green")
    print(status_badge("OVERDUE"))
    draw_table(["Task", "Due", "Status"], rows)
    print(progress_bar(0.72, label="Progress"))

Public API:
    cprint(text, style, end, file)                  → None   (styled print)
    colorize(text, style)                           → str    (styled string)
    status_badge(label)                             → str    (coloured [LABEL])
    section_header(title, width, char)              → str
    draw_table(headers, rows, col_sep, align)       → None
    progress_bar(fraction, width, label, show_pct)  → str
    truncate(text, max_len, ellipsis)               → str
    indent(text, level, char)                       → str
    hr(width, char, style)                          → str

Styles (usable in colorize / cprint):
    Colours:    black red green yellow blue magenta cyan white
    Bright:     bright_red bright_green bright_yellow bright_blue
                bright_magenta bright_cyan bright_white
    Attributes: bold dim italic underline blink reverse reset
    Combos:     header subheader success warning error info muted
"""

import os
import sys

# ---------------------------------------------------------------------------
# TTY detection — no colour when piped / redirected
# ---------------------------------------------------------------------------

def _supports_colour(stream: object = sys.stdout) -> bool:
    """Return True if *stream* is a real TTY that should receive ANSI codes."""
    if os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(stream, "isatty") and bool(getattr(stream, "isatty")())


# Evaluated once at import; override by setting FORCE_COLOR=1 or NO_COLOR=1
_COLOUR_ENABLED: bool = _supports_colour()


# ---------------------------------------------------------------------------
# ANSI escape codes
# ---------------------------------------------------------------------------

_RESET = "\033[0m"

_CODES: dict[str, str] = {
    # --- attributes ---
    "reset":          "\033[0m",
    "bold":           "\033[1m",
    "dim":            "\033[2m",
    "italic":         "\033[3m",
    "underline":      "\033[4m",
    "blink":          "\033[5m",
    "reverse":        "\033[7m",
    # --- standard foreground colours ---
    "black":          "\033[30m",
    "red":            "\033[31m",
    "green":          "\033[32m",
    "yellow":         "\033[33m",
    "blue":           "\033[34m",
    "magenta":        "\033[35m",
    "cyan":           "\033[36m",
    "white":          "\033[37m",
    # --- bright foreground colours ---
    "bright_black":   "\033[90m",
    "bright_red":     "\033[91m",
    "bright_green":   "\033[92m",
    "bright_yellow":  "\033[93m",
    "bright_blue":    "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan":    "\033[96m",
    "bright_white":   "\033[97m",
}

# Semantic combo styles — map to one or more _CODES keys.
# These are expanded in colorize() before lookup.
_COMBOS: dict[str, list[str]] = {
    "header":    ["bold", "bright_cyan"],
    "subheader": ["bold", "cyan"],
    "success":   ["bold", "bright_green"],
    "warning":   ["bold", "bright_yellow"],
    "error":     ["bold", "bright_red"],
    "info":      ["bright_blue"],
    "muted":     ["dim", "white"],
    "label":     ["bold", "white"],
}

# Urgency → style mapping (matches urgency_label() returns in date_parser)
_URGENCY_STYLES: dict[str, str] = {
    "OVERDUE": "error",
    "URGENT":  "warning",
    "SOON":    "info",
    "OK":      "success",
}


def _build_code(style: str) -> str:
    """
    Resolve a style name (or space-separated list) to ANSI escape prefix.
    Returns empty string if colour is disabled or style is unknown.
    """
    if not _COLOUR_ENABLED:
        return ""
    parts: list[str] = []
    for token in style.strip().split():
        if token in _COMBOS:
            for sub in _COMBOS[token]:
                code = _CODES.get(sub, "")
                if code:
                    parts.append(code)
        else:
            code = _CODES.get(token, "")
            if code:
                parts.append(code)
    return "".join(parts)


# ---------------------------------------------------------------------------
# Core colourising
# ---------------------------------------------------------------------------

def colorize(text: str, style: str) -> str:
    """Wrap *text* in ANSI escape codes for the given *style*."""
    code = _build_code(style)
    if not code:
        return text
    return f"{code}{text}{_RESET}"


def cprint(
    text: str,
    style: str = "reset",
    *,
    end: str = "\n",
    file: object = sys.stdout,
) -> None:
    """Styled print(). Convenience wrapper around colorize()."""
    print(colorize(text, style), end=end, file=file)


# ---------------------------------------------------------------------------
# Status badge
# ---------------------------------------------------------------------------

def status_badge(label: str, *, width: int = 0) -> str:
    """Return a coloured badge string like  [OVERDUE]  or  [ OK ]."""
    upper = label.upper()
    style = _URGENCY_STYLES.get(upper, "label")
    inner = upper.center(max(width, len(upper)))
    return colorize(f"[{inner}]", style)


# ---------------------------------------------------------------------------
# Section headers & horizontal rules
# ---------------------------------------------------------------------------

def hr(width: int = 72, char: str = "─", style: str = "muted") -> str:
    """Return a horizontal rule string."""
    return colorize(char * width, style)


def section_header(
    title: str,
    width: int = 72,
    char: str = "─",
    style: str = "header",
) -> str:
    """Return a centred section header surrounded by rule characters."""
    pad = max(0, width - len(title) - 2)
    left = char * (pad // 2)
    right = char * (pad - pad // 2)
    rule_style = "muted"
    return (
        colorize(left, rule_style)
        + " "
        + colorize(title, style)
        + " "
        + colorize(right, rule_style)
    )


# ---------------------------------------------------------------------------
# Table renderer
# ---------------------------------------------------------------------------

def draw_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    col_sep: str = "  │  ",
    align: list[str] | None = None,
    border: bool = True,
) -> None:
    """Print a plain-text table to stdout."""
    if not headers:
        return

    n_cols = len(headers)
    align = align or ["left"] * n_cols

    str_rows: list[list[str]] = [[str(cell) for cell in row] for row in rows]

    def _visible(s: str) -> str:
        import re
        return re.sub(r"\033\[[0-9;]*m", "", s)

    col_widths: list[int] = [
        max(
            len(_visible(headers[i])),
            *(len(_visible(row[i])) for row in str_rows) if str_rows else [0],
        )
        for i in range(n_cols)
    ]

    def _pad(cell: str, width: int, a: str) -> str:
        vis_len = len(_visible(cell))
        extra = width - vis_len
        if extra <= 0:
            return cell
        if a == "right":
            return " " * extra + cell
        if a == "center":
            left_pad = extra // 2
            return " " * left_pad + cell + " " * (extra - left_pad)
        return cell + " " * extra

    sep = colorize(col_sep, "muted")
    total_width = sum(col_widths) + len(_visible(col_sep)) * (n_cols - 1)

    if border:
        print(hr(total_width))

    header_cells = [
        colorize(_pad(headers[i], col_widths[i], align[i]), "subheader")
        for i in range(n_cols)
    ]
    print(sep.join(header_cells))
    print(hr(total_width, char="─", style="muted"))

    for row in str_rows:
        padded = row + [""] * max(0, n_cols - len(row))
        cells = [_pad(padded[i], col_widths[i], align[i]) for i in range(n_cols)]
        print(sep.join(cells))

    if border:
        print(hr(total_width))


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------

def progress_bar(
    fraction: float,
    *,
    width: int = 30,
    label: str = "",
    show_pct: bool = True,
    fill_char: str = "█",
    empty_char: str = "░",
) -> str:
    """Build a single-line progress bar string."""
    fraction = max(0.0, min(1.0, fraction))
    filled = round(width * fraction)
    empty = width - filled

    if fraction >= 0.66:
        bar_style = "bright_green"
    elif fraction >= 0.33:
        bar_style = "bright_yellow"
    else:
        bar_style = "bright_red"

    bar = colorize(fill_char * filled, bar_style)
    bar += colorize(empty_char * empty, "muted")
    bar = f"[{bar}]"

    prefix = f"{label} " if label else ""
    suffix = f"  {int(fraction * 100)}%" if show_pct else ""
    return f"{prefix}{bar}{suffix}"


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def truncate(text: str, max_len: int, ellipsis: str = "…") -> str:
    """Truncate *text* to *max_len* visible characters, appending *ellipsis*."""
    if len(text) <= max_len:
        return text
    return text[: max_len - len(ellipsis)] + ellipsis


def indent(text: str, level: int = 1, char: str = "  ") -> str:
    """Indent every line of *text* by *level* repetitions of *char*."""
    pad = char * level
    return "\n".join(pad + line for line in text.splitlines())
