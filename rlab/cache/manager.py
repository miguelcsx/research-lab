from pathlib import Path

from rlab.cache.paths import CachePaths


class CacheManager:
    def __init__(self, root: Path) -> None:
        self.paths = CachePaths(root=root)
        root.mkdir(parents=True, exist_ok=True)

    def entries(self) -> tuple[Path, ...]:
        return tuple(sorted(path for path in self.paths.root.rglob("*") if path.is_file()))

    def size(self) -> int:
        return sum(path.stat().st_size for path in self.entries())
