from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from rlab.constants import EntryKind
from rlab.data.context import DataContext
from rlab.data.manifest import dataset_manifest
from rlab.data.recipe import DatasetRecipe
from rlab.manifests.dataset import DatasetManifest
from rlab.registry.resolve import resolve_definition
from rlab.registry.store import Registry
from rlab.typing import JsonValue


def build_dataset(
    registry: Registry,
    name: str,
    ctx: DataContext,
    output_root: Path,
    *,
    version: str = "1",
) -> DatasetManifest:
    recipe: DatasetRecipe[Any] = resolve_definition(
        registry.get(EntryKind.DATASET, name).value,
        DatasetRecipe,
    )
    if recipe.params:
        ctx = ctx.model_copy(update={"params": {**recipe.params, **ctx.params}})
    records: Iterable[Any] = (
        record for source in recipe.flow.sources for record in source.read(ctx)
    )
    for stage in recipe.flow.stages:
        records = stage.apply(records, ctx)
    data = tuple(records)

    outputs: dict[str, Path] = {}
    stats: dict[str, JsonValue] = {}
    checks: dict[str, str] = {}
    licenses: list[str] = []
    for sink in recipe.sinks:
        sink_result = sink.write(data, ctx)
        for output_id, path in sink_result.outputs.items():
            key = str(output_id)
            if key in outputs:
                raise ValueError(f"duplicate dataset output: {key}")
            outputs[key] = _validated_output(output_root, path)
        stats.update(sink_result.stats)
        checks.update(sink_result.checks)
        licenses.extend(sink_result.licenses)
    for check in recipe.checks:
        check_result = check.evaluate(data, ctx)
        checks[str(check.id)] = check_result.manifest_status
        for key, value in check_result.metrics.items():
            stats[f"{check.id}.{key}"] = value
    for metric in recipe.metrics:
        stats[str(metric.id)] = metric.measure(data, ctx)
    if not outputs:
        raise ValueError("dataset recipe must produce at least one output")

    manifest = dataset_manifest(
        name,
        version or recipe.version,
        outputs,
        inputs=tuple(str(source.id) for source in recipe.flow.sources),
        stages=tuple(str(stage.id) for stage in recipe.flow.stages),
        stats=stats,
        checks=checks,
    )
    return manifest.model_copy(update={"licenses": tuple(dict.fromkeys(licenses))})


def _validated_output(output_root: Path, path: Path) -> Path:
    root = output_root.resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"dataset output must be inside {output_root}: {path}")
    if not resolved.exists():
        raise FileNotFoundError(f"dataset output does not exist: {path}")
    return resolved
