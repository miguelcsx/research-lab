import inspect
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from rlab.constants import EntryKind
from rlab.data.check import DataCheckResult
from rlab.data.context import DataContext
from rlab.data.io import read_jsonl, write_jsonl
from rlab.data.manifest import dataset_manifest
from rlab.data.pipeline import DataPipeline
from rlab.data.profile import profile_records
from rlab.data.report import data_report
from rlab.manifests.dataset import DatasetManifest
from rlab.registry.store import Registry
from rlab.typing import JsonValue, Record


def definition(registry: Registry, kind: EntryKind, name: str, expected: type[Any]) -> Any:
    value = registry.get(kind, name).value
    result = value() if callable(value) and not inspect.isclass(value) else value
    if not isinstance(result, expected):
        raise TypeError(f"{kind.value} {name!r} must return {expected.__name__}")
    return result


def build_dataset(
    registry: Registry,
    name: str,
    ctx: DataContext,
    output_root: Path,
    *,
    version: str = "1",
) -> DatasetManifest:
    pipeline = cast(DataPipeline, definition(registry, EntryKind.DATASET, name, DataPipeline))
    records: Iterable[Record] = (
        record
        for source_name in pipeline.sources
        for record in registry.get(EntryKind.DATA_SOURCE, source_name).value(ctx)
    )
    for transform_name in pipeline.transforms:
        records = registry.get(EntryKind.DATA_TRANSFORM, transform_name).value(records, ctx)
    materialized = output_root / "data.jsonl"
    write_jsonl(materialized, records)
    data = list(read_jsonl(materialized))
    checks: dict[str, str] = {}
    for check_name in pipeline.checks:
        result = registry.get(EntryKind.DATA_CHECK, check_name).value(data, ctx)
        if not isinstance(result, DataCheckResult):
            result = DataCheckResult.model_validate(result)
        checks[check_name] = "passed" if result.success else result.severity.value
    profile = cast(dict[str, JsonValue], profile_records(data))
    for metric_name in pipeline.metrics:
        value = registry.get(EntryKind.DATA_METRIC, metric_name).value(data, ctx)
        profile[metric_name] = value
    outputs = {"data": materialized}
    manifest = dataset_manifest(
        name,
        version,
        outputs,
        inputs=pipeline.sources,
        stages=pipeline.transforms,
        stats=profile,
        checks=checks,
    )
    (output_root / "data_report.md").write_text(data_report(name, profile, checks))
    return manifest
