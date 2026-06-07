from rlab.manifests.base import Manifest


class BenchmarkManifest(Manifest):
    source: str | None = None
    git_commit: str | None = None
    external_repo: str | None = None
    external_commit: str | None = None
