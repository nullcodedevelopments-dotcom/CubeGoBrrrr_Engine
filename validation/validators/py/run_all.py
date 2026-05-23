#!/usr/bin/env python3
"""
Run all Python (.py) validators against the directory provided as the first
argument (default: current directory).

Usage:
    python run_all.py [DIRECTORY] [--no-tui] [--log-dir PATH]
"""
from __future__ import annotations

import sys
from pathlib import Path


def _add_parent_to_path() -> None:
    """Make sure the .validation package is importable."""
    here = Path(__file__).resolve().parent
    root = here.parent.parent          # .validation/../..
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_add_parent_to_path()

from validation.__main__ import main   # noqa: E402

if __name__ == "__main__":
    # Inject --ext py if the caller hasn't specified --ext
    argv = list(sys.argv[1:])
    if "--ext" not in argv and "-e" not in argv:
        argv = ["--ext", "py"] + argv
    sys.exit(main(argv))
