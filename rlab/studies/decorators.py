from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TypeVar

from rlab.constants import EntryKind
from rlab.registry.context import current_registry
from rlab.registry.decorators import register
from rlab.studies.model import Study
from rlab.typing import JsonValue

Declaration = TypeVar("Declaration", bound=Callable[..., object])


def study(  # noqa: PLR0913
    name: str,
    *,
    question: str,
    hypotheses: tuple[str, ...] = (),
    domain: str = "general",
    variables: Mapping[str, tuple[JsonValue, ...]] | None = None,
    outcomes: tuple[str, ...] = (),
    decision_rule: str = "",
    experiments: tuple[str, ...] = (),
    references: tuple[str, ...] = (),
    requires: tuple[str, ...] = (),
    version: str = "1.0.0",
) -> Callable[[Declaration], Declaration]:
    """Attach a study plan to an experiment or other declaration function."""

    def decorate(declaration: Declaration) -> Declaration:
        register(
            current_registry(),
            EntryKind.STUDY,
            name,
            Study(
                question=question,
                hypotheses=hypotheses,
                domain=domain,
                variables=variables or {},
                outcomes=outcomes,
                decision_rule=decision_rule,
                experiments=experiments,
                references=references,
                requires=requires,
            ),
            version=version,
            declared_by=declaration,
        )
        return declaration

    return decorate
