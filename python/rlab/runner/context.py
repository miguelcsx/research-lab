"""Runtime context passed to user callables."""

from __future__ import annotations

import json
import platform
import shutil
import sys
from collections.abc import Mapping
from typing import cast
from pathlib import Path

from rlab._protocol import HostRequest, emit_event
from rlab._rlab import run_external_command
from rlab._typing import JsonObject, JsonValue
from rlab.external import (
    AdapterContext,
    ExternalCommand,
    ExternalCommandError,
    ExternalResult,
    ExternalWorkspace,
)
from rlab.graph import add_edge

from .constants import *
from .events import event, metric_event, metric_payload
from .external_workspace import materialize_external_workspace
from .paths import (
    artifact_stem,
    bounded_artifact_name,
    files_below,
    resolve_project_path,
    safe_external_name,
    safe_output_path,
)
from .serde import jsonable, mapping_value, pretty_json

MetricMap = dict[str, float]


class RuntimeContext:
    """Runtime context passed to Python user callables."""

    def __init__(self, request: HostRequest) -> None:
        if request.run_dir is None:
            raise ValueError(ERROR_RUN_DIR)
        if request.cache_dir is None:
            raise ValueError(ERROR_CACHE_DIR)

        self.run_id = request.run_id
        self.run_dir = Path(request.run_dir)
        self.cache_dir = Path(request.cache_dir)
        self.output_dir = self.run_dir / DIR_OUTPUTS
        self.params = dict(request.params)
        self.seed = request.seed
        self.project_root = Path(request.project_root)
        self.metadata = dict(request.environment)
        self._request = request
        self._metrics: MetricMap = {}
        self._input_artifacts: dict[str, Path] = {}
        self._output_artifacts: dict[str, Path] = {}

    def write_manifest(self, registry: list[JsonObject]) -> Path:
        target = self.run_dir / FILE_RUN_MANIFEST
        target.write_text(
            pretty_json(
                {
                    KEY_SCHEMA_VERSION: SCHEMA_VERSION,
                    KEY_RUN_ID: self.run_id,
                    KEY_SEED: self.seed,
                    KEY_PARAMS: self.params,
                    KEY_TARGET: _target_payload(self._request),
                    KEY_REGISTRY_SNAPSHOT: jsonable(registry),
                    KEY_ENVIRONMENT: self._environment_payload(),
                    KEY_METRICS: jsonable(self._metrics),
                    KEY_ARTIFACTS: self._artifacts_payload(),
                }
            ),
            encoding=ENCODING,
        )
        return target

    def output_path(self, value: str | Path) -> Path:
        output = self.output_dir / safe_output_path(value)
        output.parent.mkdir(parents=True, exist_ok=True)
        return output

    def str_param(self, name: str, default: str | None = None) -> str:
        value = self.params.get(name, default)
        if isinstance(value, str):
            return value
        raise TypeError(ERROR_PARAM_STRING.format(name=name))

    def int_param(self, name: str, default: int | None = None) -> int:
        value = self.params.get(name, default)
        if not isinstance(value, bool) and isinstance(value, int):
            return value
        raise TypeError(ERROR_PARAM_INT.format(name=name))

    def path_param(self, name: str, default: str | Path | None = None) -> Path:
        value = self.params.get(name, default)
        if isinstance(value, str | Path):
            return resolve_project_path(self.project_root, value)
        raise TypeError(ERROR_PARAM_PATH.format(name=name))

    def input_artifact(self, name: str, path: str | Path) -> Path:
        source = resolve_project_path(self.project_root, path)
        if not source.exists():
            raise FileNotFoundError(ERROR_INPUT_MISSING.format(path=source))

        resolved = source.resolve()
        self._input_artifacts[name] = resolved

        if self.run_id is not None:
            add_edge(
                self.project_root,
                f"artifact:{name}",
                f"run:{self.run_id}",
                REASON_INPUT,
            )

        return source

    def log_metric(
        self,
        name: str,
        value: float,
        *,
        unit: str | None = None,
        direction: str | None = None,
    ) -> None:
        metric_value = float(value)
        emit_event(
            event(
                self._request,
                EVENT_METRIC,
                metric=metric_payload(
                    name, metric_value, unit=unit, direction=direction
                ),
            )
        )
        self._metrics[str(name)] = metric_value

    def log_metrics(self, metrics: dict[str, float]) -> None:
        flat = {str(name): float(value) for name, value in metrics.items()}
        emit_event(
            event(
                self._request,
                EVENT_BATCH,
                events=[
                    metric_event(self._request, name, value)
                    for name, value in flat.items()
                ],
            )
        )
        self._metrics.update(flat)

    def note(self, text: str) -> None:
        emit_event(event(self._request, EVENT_LOG, message=str(text)))

    def save_artifact(
        self,
        name: str,
        path: str | Path,
        *,
        version: str = "1",
        kind: str = KIND_FILE,
        metadata: JsonObject | None = None,
        inputs: tuple[str, ...] = (),
    ) -> Path:
        source = resolve_project_path(self.project_root, path)
        if not source.exists():
            raise FileNotFoundError(ERROR_ARTIFACT_MISSING.format(path=source))

        resolved = source.resolve()
        existing = self._output_artifacts.get(name)
        if existing is not None:
            if existing == resolved:
                return source
            raise ValueError(ERROR_ARTIFACT_DUPLICATE.format(name=name))

        self._output_artifacts[name] = resolved
        emit_event(
            event(
                self._request,
                EVENT_ARTIFACT,
                artifact={
                    KEY_SCHEMA_VERSION: SCHEMA_VERSION,
                    KEY_KIND: kind,
                    KEY_NAME: str(name),
                    KEY_PATH: str(source),
                    KEY_VERSION: str(version),
                    KEY_METADATA: metadata or {},
                    KEY_INPUTS: list(inputs),
                },
            )
        )
        self._save_artifact_lineage(name, inputs)
        return source

    def save_table(self, name: str, rows: list[JsonObject]) -> Path:
        output = self.run_dir / DIR_GENERATED / DIR_TABLES / f"{name}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(pretty_json(rows), encoding=ENCODING)
        return self.save_artifact(name, output, kind=KIND_TABLE)

    def copy_artifact(
        self,
        name: str,
        source: str | Path,
        destination: str | Path,
        *,
        version: str = "1",
    ) -> Path:
        destination_path = resolve_project_path(self.project_root, destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(source), destination_path)
        return self.save_artifact(name, destination_path, version=version)

    def run_external(self, name: str, command: ExternalCommand) -> ExternalResult:
        command.validate()
        output_dir = self.run_dir / DIR_EXTERNAL / safe_external_name(name)
        output_dir.mkdir(parents=True, exist_ok=True)

        stdout_path = output_dir / FILE_STDOUT
        stderr_path = output_dir / FILE_STDERR
        payload = mapping_value(
            json.loads(
                run_external_command(
                    list(command.args),
                    command.cwd,
                    dict(command.env),
                    command.timeout_seconds,
                    stdout_path,
                    stderr_path,
                )
            ),
            "external command result",
        )

        result = ExternalResult(
            exit_code=cast(int | None, payload.get(KEY_EXIT_CODE)),
            stdout=stdout_path.read_text(encoding=ENCODING, errors=ERRORS_REPLACE),
            stderr=stderr_path.read_text(encoding=ENCODING, errors=ERRORS_REPLACE),
            timed_out=bool(payload.get(KEY_TIMED_OUT, False)),
        )

        self.save_artifact(f"{name}.stdout", stdout_path, kind=KIND_LOG)
        self.save_artifact(f"{name}.stderr", stderr_path, kind=KIND_LOG)

        if result.timed_out or result.exit_code != 0:
            raise ExternalCommandError(name, result)

        if command.output_root is not None:
            self._register_external_artifacts(
                name, command.output_root, command.artifacts
            )

        return result

    def external_workspace(
        self,
        name: str,
        spec: ExternalWorkspace,
        params: Mapping[str, JsonValue],
    ) -> AdapterContext:
        spec.validate()
        external_root = self.run_dir / DIR_EXTERNAL / safe_external_name(name)
        outputs = external_root / DIR_OUTPUTS
        workspace = materialize_external_workspace(
            project_root=self.project_root,
            cache_dir=self.cache_dir,
            run_outputs=outputs,
            name=name,
            source_param=spec.source_param,
            default_source=spec.default_source,
            ignored=spec.ignored,
            cached=spec.cached,
            outputs=spec.outputs,
            params=params,
        )
        return AdapterContext(
            project_root=self.project_root,
            workspace=workspace,
            outputs=outputs,
            params=dict(params),
        )

    def register_outputs(self) -> None:
        if not self.output_dir.exists():
            return

        registered = set(self._output_artifacts.values())
        for path in files_below(self.output_dir):
            if path.resolve() in registered:
                continue
            stem = artifact_stem(path, self.output_dir)
            self.save_artifact(bounded_artifact_name("output", stem), path)

    def _register_external_artifacts(
        self,
        command_name: str,
        output_root: Path,
        patterns: tuple[str, ...],
    ) -> None:
        paths = sorted(
            {
                path
                for pattern in patterns
                for path in output_root.glob(pattern)
                if path.is_file()
            }
        )
        for path in paths:
            self.save_artifact(
                bounded_artifact_name(command_name, artifact_stem(path, output_root)),
                path,
            )

    def _environment_payload(self) -> JsonObject:
        return {
            **self.metadata,
            KEY_PYTHON: sys.version,
            KEY_PLATFORM: platform.platform(),
            KEY_MACHINE: platform.machine(),
            KEY_PROCESSOR: platform.processor(),
        }

    def _artifacts_payload(self) -> JsonObject:
        return {
            KEY_INPUTS: {
                name: str(path) for name, path in self._input_artifacts.items()
            },
            KEY_OUTPUTS: {
                name: str(path) for name, path in self._output_artifacts.items()
            },
        }

    def _save_artifact_lineage(self, name: str, inputs: tuple[str, ...]) -> None:
        if self.run_id is None:
            return

        run_ref = f"run:{self.run_id}"
        artifact_ref = f"artifact:{name}"
        add_edge(self.project_root, run_ref, artifact_ref, REASON_OUTPUT)

        for input_name in inputs:
            add_edge(
                self.project_root,
                f"artifact:{input_name}",
                artifact_ref,
                REASON_DERIVED,
            )


def _target_payload(request: HostRequest) -> JsonObject | None:
    if request.target is None:
        return None
    return {KEY_KIND: request.target.kind, KEY_NAME: request.target.name}
