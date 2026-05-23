#!/usr/bin/env python3
"""Run validation using a module-local virtual environment.

Usage:
    python validation/run_validation.py [TARGET] [OPTIONS]

This script ensures `validation/.venv` exists with required dependencies,
then re-executes `python -m validation ...` using that interpreter.

For TUI - python3 run_validation.py --textual
For plain stdout - python3 run_validation.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent
VENV_DIR = MODULE_DIR / ".venv"
REQ_FILE = MODULE_DIR / "requirements.txt"


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _venv_is_healthy(venv_python: Path) -> bool:
    if not venv_python.exists():
        return False
    check = subprocess.run(
        [str(venv_python), "-c", "import rich, textual"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return check.returncode == 0


def _create_local_venv(venv_python: Path) -> None:
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR, ignore_errors=True)
    subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
    subprocess.check_call([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([str(venv_python), "-m", "pip", "install", "-r", str(REQ_FILE)])


def _ensure_local_venv() -> Path:
    venv_python = _venv_python()
    if not _venv_is_healthy(venv_python):
        _create_local_venv(venv_python)
    return venv_python


def main() -> int:
    venv_python = _ensure_local_venv()
    argv = [str(venv_python), "-m", "validation", *sys.argv[1:]]
    os.execv(str(venv_python), argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
