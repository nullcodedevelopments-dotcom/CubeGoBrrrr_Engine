from pathlib import Path

def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")

def write_text(path: str | Path, content: str) -> None:
    Path(path).write_text(content, encoding="utf-8")

def append_text(path: str | Path, content: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)

def read_bytes(path: str | Path) -> bytes:
    return Path(path).read_bytes()

def write_bytes(path: str | Path, data: bytes) -> None:
    Path(path).write_bytes(data)