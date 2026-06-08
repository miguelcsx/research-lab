from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from rlab.constants import EntryKind
from rlab.context.runtime import RuntimeContext
from rlab.references.parser import parse_reference
from rlab.references.refs import ReferenceKind
from rlab.studies.model import Study


class StudyPlan(BaseModel):
    """A static analysis of a `Study`: planned runs and unmet requirements."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    study: Study
    planned_runs: int
    missing: tuple[str, ...] = Field(default_factory=tuple)


_KIND_TO_ENTRY: dict[ReferenceKind, EntryKind] = {
    ReferenceKind.SUITE: EntryKind.SUITE,
    ReferenceKind.BENCHMARK: EntryKind.BENCHMARK,
    ReferenceKind.DATASET: EntryKind.DATASET,
    ReferenceKind.COMPONENT: EntryKind.COMPONENT,
}


def plan_study(runtime: RuntimeContext, name: str, study: Study) -> StudyPlan:
    """Resolve every requirement reference and report what's missing."""
    return StudyPlan(
        name=name,
        study=study,
        planned_runs=study.planned_runs,
        missing=_missing_requirements(runtime, study),
    )


def _missing_requirements(runtime: RuntimeContext, study: Study) -> tuple[str, ...]:
    missing: list[str] = []
    for reference in study.requires:
        if not _is_resolvable(runtime, reference):
            missing.append(reference)
    return tuple(missing)


def _is_resolvable(runtime: RuntimeContext, reference: str) -> bool:
    try:
        parsed = parse_reference(reference)
    except Exception:
        return False
    kind = _KIND_TO_ENTRY.get(parsed.kind)
    if kind is None:
        return True  # opaque reference — assume the caller knows
    try:
        runtime.registry.get(kind, str(parsed))
    except Exception:
        return False
    return True
