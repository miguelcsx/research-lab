from __future__ import annotations

import sqlite3
import time
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import yaml

from rlab.constants import RUNS_DB_NAME, RunStatus
from rlab.manifests.run import RunManifest
from rlab.reports.markdown import render_run_report
from rlab.reproducibility.capture import capture_reproducibility
from rlab.runs.index import RunIndex
from rlab.runs.layout import RunLayout
from rlab.runs.lifecycle import fail_run, finish_run, start_run
from rlab.runs.writer import writer_for

if TYPE_CHECKING:
    from rlab.context.runtime import RuntimeContext


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _slug(value: str) -> str:
    return "".join(c if c.isalnum() or c in ("-", "_", ".") else "_" for c in value)


class RunSession:
    def __init__(  # noqa: PLR0913
        self,
        runtime: RuntimeContext,
        operation: str,
        name: str,
        params: dict[str, Any],
        *,
        tags: tuple[str, ...] = (),
        notes: str | None = None,
        parent_run: str | None = None,
    ) -> None:
        self.runtime = runtime
        self.operation = operation
        self.params = dict(params)
        self.tags = tuple(tags)
        self._notes = notes
        self._parent_run = parent_run
        created = _now()
        run_id = f"{_slug(operation)}_{_slug(name)}_{int(time.time() * 1000)}"
        runtime.paths.runs.mkdir(parents=True, exist_ok=True)
        self.layout = RunLayout(root=runtime.paths.runs / run_id)
        self.layout.create()
        self.manifest = RunManifest(
            kind="run",
            name=run_id,
            version="1",
            operation=operation,
            status=RunStatus.CREATED,
            created_at=created,
            updated_at=created,
            parameters={k: v for k, v in self.params.items() if _jsonable(v)},
            tags=self.tags,
            notes=notes,
            parent_run=parent_run,
        )
        self._write_manifest()
        self._writer = writer_for(self.layout.root)
        self._writer.params(self.manifest.parameters)
        if notes:
            self._writer.note(notes)
        self._index = RunIndex(runtime.paths.cache / RUNS_DB_NAME)

    def _write_manifest(self) -> None:
        self.layout.manifest_file.write_text(
            yaml.safe_dump(self.manifest.model_dump(mode="json"), sort_keys=False),
            encoding="utf-8",
        )

    def _refresh(self, **fields: Any) -> None:
        fields.setdefault("updated_at", _now())
        self.manifest = self.manifest.model_copy(update=fields)
        self._write_manifest()

    def _upsert_index(self) -> None:
        try:
            self._index.upsert(
                run_id=self.manifest.name,
                name=self.manifest.name,
                operation=self.operation,
                status=self.manifest.status,
                path=self.layout.root,
                created_at=self.manifest.created_at.isoformat(),
                parent_id=self._parent_run,
                tags=self.tags,
                params=dict(self.manifest.parameters),
            )
        except (OSError, sqlite3.Error, ValueError, TypeError) as exc:
            warnings.warn(f"Run index upsert failed: {exc}", stacklevel=2)

    def start(self) -> RuntimeContext:
        start_run(self.layout.root)
        self._refresh(status=RunStatus.RUNNING)
        self._capture_reproducibility()
        self._upsert_index()
        return self.runtime.model_copy(
            update={
                "run_id": self.manifest.name,
                "run_dir": self.layout.root,
                "params": {**self.runtime.params, **self.manifest.parameters},
            }
        )

    @contextmanager
    def running(self) -> Iterator[RuntimeContext]:
        active = self.start()
        try:
            yield active
        except Exception as error:
            self.fail(error)
            raise

    def _capture_reproducibility(self) -> None:
        try:
            capture_reproducibility(
                self.runtime.paths.root,
                self.layout.root,
                self.runtime.config.reproducibility,
                ("rlab", self.operation, self.manifest.name),
            )
        except (OSError, ImportError, ValueError, TypeError) as exc:
            warnings.warn(f"Reproducibility capture failed: {exc}", stacklevel=2)

    def metric(self, name: str, value: float, **attrs: Any) -> None:
        self._writer.metric(name, float(value), **{k: v for k, v in attrs.items() if _jsonable(v)})

    def complete(self, results: Any, notes: str | None = None) -> None:
        self._writer.results(results)
        if notes:
            self._writer.note(notes)
        finish_run(self.layout.root)
        self._refresh(status=RunStatus.COMPLETED)
        self._write_report()
        self._upsert_index()

    def _write_report(self) -> None:
        text = f"# Run {self.manifest.name}\n"
        try:
            text = render_run_report(self.layout.root)
        except (OSError, ImportError, ValueError) as exc:
            warnings.warn(f"Report generation failed: {exc}", stacklevel=2)
        (self.layout.root / "report.md").write_text(text, encoding="utf-8")

    def fail(self, error: BaseException | str) -> None:
        message = str(error)
        fail_run(self.layout.root, message)
        self._refresh(status=RunStatus.FAILED, error=message)
        self._upsert_index()


def _jsonable(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, (list, tuple)):
        return all(_jsonable(v) for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _jsonable(v) for k, v in value.items())
    return False
