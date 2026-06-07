from typing import Protocol

from rlab.manifests.run import RunManifest


class TrackingBackend(Protocol):
    def start(self, manifest: RunManifest) -> None: ...

    def metric(self, run_id: str, name: str, value: float, step: int | None = None) -> None: ...

    def finish(self, manifest: RunManifest) -> None: ...
