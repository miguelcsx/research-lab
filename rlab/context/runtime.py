from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from rlab.config.models import LabConfig
from rlab.constants import Direction
from rlab.context.paths import ProjectPaths
from rlab.context.resources import Resources
from rlab.registry.store import Registry
from rlab.typing import JsonValue, MetricValue, UnitStr

if TYPE_CHECKING:
    from rlab.typing import Serializer

T = TypeVar("T")


class RuntimeContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: LabConfig
    paths: ProjectPaths
    registry: Registry
    run_id: str | None = None
    run_dir: Path | None = None
    seed: int = 0
    params: dict[str, JsonValue] = Field(default_factory=dict)
    resources: Resources = Field(default_factory=Resources)

    # ── path helpers ──────────────────────────────────────────────────────────

    def artifact_path(self, relative: str) -> Path:
        path = self._run_subdir("artifacts") / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def figure_path(self, relative: str) -> Path:
        path = self._run_subdir("figures") / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def table_path(self, relative: str) -> Path:
        path = self._run_subdir("tables") / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def log_path(self, relative: str) -> Path:
        path = self._run_subdir("logs") / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    # ── result recording ──────────────────────────────────────────────────────

    def log_metric(
        self,
        name: str,
        value: MetricValue,
        *,
        unit: UnitStr = "dimensionless",
        direction: Direction = Direction.MINIMIZE,
        step: int | None = None,
    ) -> RuntimeContext:
        from rlab.runs.layout import RunLayout  # noqa: PLC0415
        from rlab.runs.writer import RunWriter  # noqa: PLC0415

        if self.run_dir is not None:
            writer = RunWriter(RunLayout(root=self.run_dir))
            attrs: dict[str, Any] = {"unit": unit, "direction": direction.value}
            if step is not None:
                attrs["step"] = step
            writer.metric(name, value, **attrs)
        return self

    def save_figure(
        self,
        name: str,
        fig: Any,
        *,
        formats: tuple[str, ...] = ("png",),
    ) -> RuntimeContext:
        if self.run_dir is None:
            return self
        dest = self._run_subdir("figures") / name
        dest.mkdir(parents=True, exist_ok=True)
        _save_figure_obj(fig, dest, name, formats)
        return self

    def save_table(
        self,
        name: str,
        data: Any,
        *,
        formats: tuple[str, ...] = ("csv",),
    ) -> RuntimeContext:
        from rlab.runs.layout import RunLayout  # noqa: PLC0415
        from rlab.runs.writer import RunWriter  # noqa: PLC0415

        if self.run_dir is None:
            return self
        writer = RunWriter(RunLayout(root=self.run_dir))
        for fmt in formats:
            writer.table(name, data, fmt=fmt)
        return self

    def save_artifact(self, name: str, path: str | Path) -> RuntimeContext:
        if self.run_dir is None:
            return self
        src = Path(path)
        dest = self._run_subdir("artifacts") / name
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        elif src.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        return self

    def note(self, text: str, author: str | None = None) -> RuntimeContext:
        from rlab.runs.layout import RunLayout  # noqa: PLC0415
        from rlab.runs.writer import RunWriter  # noqa: PLC0415

        if self.run_dir is not None:
            RunWriter(RunLayout(root=self.run_dir)).note(text, author)
        return self

    def save_object(
        self,
        name: str,
        obj: T,
        serializer: Serializer[T],
    ) -> RuntimeContext:
        if self.run_dir is None:
            return self
        dest = self._run_subdir("artifacts") / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(serializer(obj))
        return self

    # ── private ───────────────────────────────────────────────────────────────

    def _run_subdir(self, name: str) -> Path:
        if self.run_dir is None:
            raise RuntimeError("RuntimeContext has no active run")
        path = self.run_dir / name
        path.mkdir(parents=True, exist_ok=True)
        return path


def _save_figure_obj(fig: Any, dest: Path, name: str, formats: tuple[str, ...]) -> None:
    """Save a figure object (matplotlib, PIL, or plain path) into dest/."""
    # matplotlib Figure
    if hasattr(fig, "savefig"):
        for fmt in formats:
            fig.savefig(dest / f"{name}.{fmt}", bbox_inches="tight")
        return
    # PIL / Pillow Image
    if hasattr(fig, "save") and hasattr(fig, "format"):
        for fmt in formats:
            fig.save(dest / f"{name}.{fmt}")
        return
    # Path-like: copy the file
    src = Path(str(fig))
    if src.exists():
        for fmt in formats:
            dest_file = dest / f"{name}.{fmt}"
            if src.suffix.lstrip(".") == fmt:
                shutil.copy2(src, dest_file)
