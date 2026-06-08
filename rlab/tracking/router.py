from pathlib import Path

from rlab.errors import ConfigError
from rlab.runs.index import RunIndex
from rlab.tracking.base import TrackingBackend
from rlab.tracking.local import LocalTracking
from rlab.tracking.null import NullTracking


def tracking_backend(name: str, cache: Path, runs: Path) -> TrackingBackend:
    if name == "local":
        return LocalTracking(RunIndex(cache / "runs.db"), runs)
    if name == "null":
        return NullTracking()
    raise ConfigError(f"Tracking backend {name!r} requires an installed adapter")
