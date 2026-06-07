import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from rlab.plugins.errors import PluginLoadError


def load_file(path: Path) -> ModuleType:
    resolved = path.resolve()
    module_name = f"_rlab_{abs(hash(resolved))}_{len(sys.modules)}"
    spec = importlib.util.spec_from_file_location(module_name, resolved)
    if spec is None or spec.loader is None:
        raise PluginLoadError(f"Cannot import project module {resolved}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_project_module(root: Path, module_name: str) -> tuple[Path, ...]:
    module_path = root / module_name
    file_path = root / f"{module_name}.py"
    if file_path.exists():
        load_file(file_path)
        return (file_path,)
    if module_path.is_dir():
        paths = tuple(
            path for path in sorted(module_path.rglob("*.py")) if path.name != "__init__.py"
        )
        for path in paths:
            load_file(path)
        return paths
    return ()
