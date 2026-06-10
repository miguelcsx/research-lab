from pathlib import Path

from rlab.data.audit import AuditPaths
from rlab.manifests.checksum import sha256
from rlab.manifests.dataset import DatasetAudit, DatasetManifest, DatasetOutput
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
    declaration: str,
    pipeline: str,
    components: tuple[str, ...],
    configuration: dict[str, dict[str, JsonValue]],
    audit: AuditPaths,
) -> DatasetManifest:
    return DatasetManifest(
        kind="dataset",
        name=name,
        version=version,
        declaration=declaration,
        pipeline=pipeline,
        components=components,
        configuration=configuration,
        inputs=inputs,
        stages=stages,
        outputs={
            key: DatasetOutput(
                kind="dataset_output",
                name=key,
                version=version,
                path=path,
                sha256=sha256(path),
                size_bytes=_path_size(path),
                is_directory=path.is_dir(),
            )
            for key, path in outputs.items()
        },
        stats=stats,
        checks=checks,
        audit=DatasetAudit(
            kind="dataset_audit",
            name="audit",
            version=version,
            summary=audit.summary,
            drop_reasons=audit.drop_reasons,
            stage_summary=audit.stage_summary,
            source_summary=audit.source_summary,
            decisions=audit.decisions,
            samples=dict(audit.samples),
        ),
    )


def _path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())
