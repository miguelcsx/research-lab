import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path


def clean_cache(root: Path, older_than: timedelta | None = None) -> tuple[Path, ...]:
    removed: list[Path] = []
    cutoff = datetime.now(UTC).timestamp() - older_than.total_seconds() if older_than else None
    if not root.exists():
        return ()
    for path in sorted(root.iterdir()):
        if cutoff is not None and path.stat().st_mtime >= cutoff:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(path)
    return tuple(removed)
