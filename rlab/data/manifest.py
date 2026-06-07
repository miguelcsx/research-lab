from pathlib import Path

from rlab.manifests.checksum import sha256
from rlab.manifests.dataset import DatasetManifest, DatasetOutput
from rlab.typing import JsonValue


def dataset_manifest(  # noqa: PLR0913
    name: str,
    version: str,
    outputs: dict[str, Path],
    *,
    inputs: tuple[str, ...],
    stages: tuple[str, ...],
    stats: dict[str, JsonValue],
    checks: dict[str, str],
) -> DatasetManifest:
    return DatasetManifest(
        kind="dataset",
        name=name,
        version=version,
        inputs=inputs,
        stages=stages,
        outputs={
            key: DatasetOutput(
                kind="dataset_output",
                name=key,
                version=version,
                path=path,
                sha256=sha256(path),
                size_bytes=path.stat().st_size,
            )
            for key, path in outputs.items()
        },
        stats=stats,
        checks=checks,
    )
