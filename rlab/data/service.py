import csv
import json
from collections.abc import Mapping
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
from rlab.typing import JsonValue, Record


def _dataset_name(reference: str) -> str:
    return reference.removeprefix("dataset:")


def build(
    runtime: RuntimeContext,
    reference: str,
    *,
    overrides: Mapping[str, JsonValue] | None = None,
) -> Path:
    name = _dataset_name(reference)
    active_overrides = dict(overrides or {})
    session = RunSession(runtime, "data.build", name, {"dataset": reference, **active_overrides})
    with session.running() as active:
        output = session.layout.artifacts / "dataset"
        context = DataContext(runtime=active, work_dir=output)
        manifest = build_dataset(
            active.registry,
            name,
            context,
            output,
            overrides=active_overrides,
        )
        write_manifest(output / "manifest.yaml", manifest)
        session.complete(manifest)
    return session.layout.root


def manifest_data_path(path: Path) -> Path:
    manifest = read_dataset_manifest(path)
    output = manifest.outputs.get("data") or next(iter(manifest.outputs.values()))
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


def audit_summary(path: Path) -> object:
    manifest = read_dataset_manifest(_manifest_path(path))
    return json.loads(_audit_path(path, manifest.audit.summary).read_text(encoding="utf-8"))


def audit_table(path: Path, table_name: str) -> tuple[dict[str, str], ...]:
    manifest_path = _manifest_path(path)
    manifest = read_dataset_manifest(manifest_path)
    audit_file = {
        "reasons": manifest.audit.drop_reasons,
        "stages": manifest.audit.stage_summary,
        "sources": manifest.audit.source_summary,
    }[table_name]
    with _audit_path(manifest_path, audit_file).open(encoding="utf-8", newline="") as stream:
        return tuple(csv.DictReader(stream))


def audit_samples(path: Path, reason: str) -> tuple[Record, ...]:
    manifest_path = _manifest_path(path)
    manifest = read_dataset_manifest(manifest_path)
    sample_path = manifest.audit.samples.get(reason)
    if sample_path is None:
        configured = ", ".join(sorted(manifest.audit.samples)) or "none"
        raise ValueError(
            f"No audit samples captured for reason {reason!r}; available reasons: {configured}"
        )
    return tuple(read_jsonl(_audit_path(manifest_path, sample_path)))


def _manifest_path(path: Path) -> Path:
    if path.is_file():
        return path
    candidate = path / "artifacts" / "dataset" / "manifest.yaml"
    if not candidate.exists():
        raise FileNotFoundError(f"dataset manifest not found under {path}")
    return candidate


def _audit_path(manifest_path: Path, path: Path) -> Path:
    return path if path.is_absolute() else manifest_path.parent / path
