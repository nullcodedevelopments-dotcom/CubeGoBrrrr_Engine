from __future__ import annotations

import importlib.util
import time
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .models import Severity, ValidationIssue, ValidatorResult
from .base_validator import BaseValidator
from .logger import ValidationLogger

RunFn = Callable[[Path, "ValidationLogger"], object]


@dataclass
class ScriptMeta:
    name:       str
    path:       Path
    description: str
    is_global:  bool
    source_dir: Path


@dataclass
class ScriptValidatorResult(ValidatorResult):
    script_meta: Optional[ScriptMeta] = field(default=None)


def _filename_to_title(stem: str) -> str:
    return stem.replace("_", " ").replace("-", " ").title()


def _extract_description(module: types.ModuleType) -> str:
    doc = getattr(module, "__doc__", None) or ""
    for line in doc.splitlines():
        s = line.strip()
        if s:
            return s
    return "(no description)"


class ScriptLoader:
    _SKIP_STEMS = {"__init__", "example_audit", "conftest"}

    def __init__(self, global_dir: Path, project_dir: Optional[Path] = None) -> None:
        self._global_dir  = global_dir
        self._project_dir = project_dir
        self._cache: Dict[Path, types.ModuleType] = {}

    def discover(self) -> List[ScriptMeta]:
        found: List[ScriptMeta] = []
        dirs = [(self._global_dir, True)]
        if self._project_dir and self._project_dir.is_dir():
            dirs.append((self._project_dir, False))
        for script_dir, is_global in dirs:
            if not script_dir.is_dir():
                continue
            for script_path in sorted(script_dir.glob("*.py")):
                if script_path.stem in self._SKIP_STEMS or script_path.stem.startswith("_"):
                    continue
                module = self._try_load(script_path)
                if module is None or not self._is_valid(module):
                    continue
                found.append(ScriptMeta(
                    name=_filename_to_title(script_path.stem),
                    path=script_path,
                    description=_extract_description(module),
                    is_global=is_global,
                    source_dir=script_dir,
                ))
        return found

    def load_script(self, meta: ScriptMeta) -> Optional[types.ModuleType]:
        return self._try_load(meta.path)

    def _try_load(self, path: Path) -> Optional[types.ModuleType]:
        if path in self._cache:
            return self._cache[path]
        try:
            spec = importlib.util.spec_from_file_location(f"_vs_{path.stem}", path)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            self._cache[path] = module
            return module
        except Exception:
            return None

    def _is_valid(self, module: types.ModuleType) -> bool:
        return callable(getattr(module, "run", None)) or isinstance(getattr(module, "ALL_VALIDATORS", None), list)

    def run_script(self, meta: ScriptMeta, target_dir: Path, logger: ValidationLogger) -> ScriptValidatorResult:
        result  = ScriptValidatorResult(validator_name=f"script.{meta.path.stem}", file_path=target_dir, script_meta=meta)
        t_start = time.perf_counter()
        module  = self.load_script(meta)
        if module is None:
            result.issues = [ValidationIssue(
                file_path=target_dir, line=0, col=0, severity=Severity.ERROR,
                rule=f"script.{meta.path.stem}.load_failed",
                message=f"Failed to load custom script: {meta.path}",
                suggested_fix="Ensure the script is valid Python and exposes a run() function.",
            )]
        else:
            try:
                raw = module.run(target_dir, logger)  # type: ignore[attr-defined]
                if isinstance(raw, ValidatorResult):
                    result.issues = raw.issues
                elif isinstance(raw, list):
                    result.issues = [i for i in raw if isinstance(i, ValidationIssue)]
                else:
                    result.issues = []
            except Exception as exc:
                result.issues = [ValidationIssue(
                    file_path=target_dir, line=0, col=0, severity=Severity.ERROR,
                    rule=f"script.{meta.path.stem}.runtime_error",
                    message=f"Script raised an exception: {exc}",
                    suggested_fix="Check the script for bugs.",
                )]
        result.duration_ms = (time.perf_counter() - t_start) * 1000
        return result

    def build_validators(self, meta: ScriptMeta) -> List[BaseValidator]:
        module = self.load_script(meta)
        if module is None:
            return []
        validators = getattr(module, "ALL_VALIDATORS", None)
        if isinstance(validators, list):
            return [v for v in validators if isinstance(v, BaseValidator)]
        return []
