import json
from pathlib import Path

from rlab.artifacts.service import promote_path
from rlab.context.runtime import RuntimeContext
from rlab.data.context import DataContext
from rlab.data.diff import diff_records
from rlab.data.io import read_jsonl
from rlab.data.profile import profile_records
from rlab.data.runner import build_dataset
from rlab.data.sample import sample_records
from rlab.manifests.io import read_dataset_manifest, write_manifest
from rlab.runs.session import RunSession
from rlab.typing import Record


def _dataset_name(reference: str) -> str:
    return reference.removeprefix("dataset:")


def build(runtime: RuntimeContext, reference: str, version: str = "1") -> Path:
    name = _dataset_name(reference)
    session = RunSession(runtime, "data.build", name, {"dataset": reference})
    with session.running() as active:
        output = session.layout.artifacts / "dataset"
        context = DataContext(runtime=active, work_dir=output)
        manifest = build_dataset(active.registry, name, context, output, version=version)
        write_manifest(output / "manifest.yaml", manifest)
        session.complete(manifest)
    return session.layout.root


def manifest_data_path(path: Path) -> Path:
    manifest = read_dataset_manifest(path)
    output = next(iter(manifest.outputs.values()))
    return output.path if output.path.is_absolute() else path.parent / output.path


def profile(path: Path) -> dict[str, object]:
    return profile_records(read_jsonl(manifest_data_path(path)))


def sample(path: Path, count: int) -> tuple[Record, ...]:
    return sample_records(read_jsonl(manifest_data_path(path)), count)


def diff(left: Path, right: Path) -> dict[str, tuple[Record, ...]]:
    return diff_records(
        read_jsonl(manifest_data_path(left)),
        read_jsonl(manifest_data_path(right)),
    )


def promote(
    runtime: RuntimeContext,
    manifest_path: Path,
    *,
    name: str,
    alias: str,
) -> Path:
    manifest = read_dataset_manifest(manifest_path)
    data_path = manifest_data_path(manifest_path)
    return promote_path(
        runtime,
        data_path,
        artifact_kind="dataset",
        name=name,
        version=manifest.version,
        alias=alias,
    )


def write_sample(path: Path, records: tuple[Record, ...]) -> None:
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n")
