from pathlib import Path

__PROJECT_ROOT = Path(__file__).resolve().parent[4]

def get_project_root() -> Path:
    return __PROJECT_ROOT

def get_textures_dir() -> Path:
    return __PROJECT_ROOT / "Assets" / "Textures"

def get_models_dir() -> Path:
    return __PROJECT_ROOT / "Assets" / "Models"

def get_shaders_dir() -> Path:
    return __PROJECT_ROOT / "Assets" / "Shaders"

def get_logs_dir() -> Path:
    return __PROJECT_ROOT / "Logs"

def get_saves_dir() -> Path:
    return __PROJECT_ROOT / "Saves"

def get_configs_dir() -> Path:
    return __PROJECT_ROOT / "Configs"

def resolve_path(*path_parts: str) -> Path:
    return __PROJECT_ROOT.joinpath(*path_parts)

def ensure_directory(path: str | Path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)