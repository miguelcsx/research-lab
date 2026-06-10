from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from rlab.evaluations.task import EvaluationTask


class EvaluationSuite(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tasks: tuple[EvaluationTask, ...]
    baselines: tuple[str, ...] = ()

    def add(self, task: EvaluationTask, *, baselines: tuple[str, ...] = ()) -> "EvaluationSuite":
        """Return a new suite with `task` appended and baselines merged (deduped, order-preserving)."""
        if any(existing.name == task.name for existing in self.tasks):
            raise ValueError(f"duplicate task {task.name!r} in suite")
        merged_baselines = tuple(dict.fromkeys((*self.baselines, *baselines)))
        return self.model_copy(
            update={
                "tasks": (*self.tasks, task),
                "baselines": merged_baselines,
            }
        )
