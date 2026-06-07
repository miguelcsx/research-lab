from rlab.manifests.run import RunManifest


class NullTracking:
    def start(self, manifest: RunManifest) -> None:
        pass

    def metric(self, run_id: str, name: str, value: float, step: int | None = None) -> None:
        pass

    def finish(self, manifest: RunManifest) -> None:
        pass
