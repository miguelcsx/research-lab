from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from rlab.constants import EntryKind
from rlab.registry.decorators import register
from rlab.registry.store import Registry
from rlab.studies.model import Study

Declaration = TypeVar("Declaration", bound=Callable[..., object])


class _StudyDecorator:
    """Two clean entry points: plain kwargs (common) or a pre-built spec (advanced).

    ``registry`` is required — pass the ``Project.registry`` to register into.
    """

    def __call__(
        self,
        name: str,
        question: str,
        *,
        registry: Registry,
        **fields: object,
    ) -> Callable[[Declaration], Declaration]:
        spec = Study(question=question, **fields)

        def decorate(declaration: Declaration) -> Declaration:
            self._register(registry, name, declaration, spec)
            return declaration

        return decorate

    @classmethod
    def from_spec(
        cls,
        name: str,
        spec: Study,
        *,
        registry: Registry,
    ) -> Callable[[Declaration], Declaration]:
        def decorate(declaration: Declaration) -> Declaration:
            cls()._register(registry, name, declaration, spec)
            return declaration

        return decorate

    def _register(
        self,
        registry: Registry,
        name: str,
        declaration: Declaration,
        spec: Study,
    ) -> None:
        register(registry, EntryKind.STUDY, name, spec, declared_by=declaration)


study: _StudyDecorator = _StudyDecorator()
