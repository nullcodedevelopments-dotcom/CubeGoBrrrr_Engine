"""
.validation — multi-language codebase integrity scanner.

Public API (no TUI required):
    from validation import run, run_all_python, run_all_javascript, run_all_css, run_all_html

Launch Textual TUI:
    from validation import launch_tui  # requires: pip install textual
    launch_tui(target_dir=Path("."))
"""
from typing import Any


def run(*args: Any, **kwargs: Any):
    from .__main__ import run as _run
    return _run(*args, **kwargs)


def run_all_python(*args: Any, **kwargs: Any):
    from .__main__ import run_all_python as _run_all_python
    return _run_all_python(*args, **kwargs)


def run_all_javascript(*args: Any, **kwargs: Any):
    from .__main__ import run_all_javascript as _run_all_javascript
    return _run_all_javascript(*args, **kwargs)


def run_all_css(*args: Any, **kwargs: Any):
    from .__main__ import run_all_css as _run_all_css
    return _run_all_css(*args, **kwargs)


def run_all_html(*args: Any, **kwargs: Any):
    from .__main__ import run_all_html as _run_all_html
    return _run_all_html(*args, **kwargs)

try:
    from .tui.app import launch_tui  # noqa: F401
except ImportError:
    launch_tui = None  # type: ignore[assignment]

__version__ = "2.0.0"
__all__ = ["run", "run_all_python", "run_all_javascript", "run_all_css", "run_all_html", "launch_tui"]
