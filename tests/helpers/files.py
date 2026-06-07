from __future__ import annotations

from pathlib import Path


def write_module(root: Path, module_name: str, source: str) -> Path:
    path = root / f"{module_name.replace('.', '/')}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def append_to_lab_toml(project: Path, text: str) -> Path:
    path = project / "lab.toml"
    path.write_text(f"{path.read_text(encoding='utf-8')}\n{text}\n", encoding="utf-8")
    return path


def inject_module_load(project: Path, module: str) -> Path:
    path = project / "lab.toml"
    content = path.read_text(encoding="utf-8")
    if "load = [" in content:
        content = content.replace("load = [", f"load = [\n  \"{module}\",")
    else:
        content = f"{content}\n[modules]\nload = [\"{module}\"]\n"
    path.write_text(content, encoding="utf-8")
    return path
