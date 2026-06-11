"""Built-in model loaders.

These are registered automatically by the runner so that targets of the
form `model:<loader>:<path>` resolve without requiring the user to
register a per-path component. Each loader exposes a `.load(path)` method
that returns a model object consumable by the registered evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class HuggingFaceModel:
    """Minimal model object produced by the built-in `hf` loader.

    Exposes `name` so evaluators that read `getattr(model, "name", None)`
    can recover the underlying repo id. `ref()` is provided for evaluators
    that prefer the dict-style interface.
    """

    name_or_path: str
    backend: str = "causal"
    revision: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.name_or_path

    def ref(self) -> dict[str, Any]:
        return {
            "name_or_path": self.name_or_path,
            "backend": self.backend,
            "revision": self.revision,
            **self.extra,
        }


class HuggingFaceLoader:
    """Loader registered as `model:hf` — see :func:`register_builtin_loaders`."""

    def load(self, path: str) -> HuggingFaceModel:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("hf loader expects a non-empty <org>/<repo> path")
        return HuggingFaceModel(name_or_path=path.strip())


def register_builtin_loaders(project: Any) -> None:
    """Register built-in model loaders on `project`.

    Safe to call multiple times — registration fails only on conflict.
    """
    loaders: tuple[tuple[str, Callable[[str], Any]], ...] = (
        ("hf", HuggingFaceLoader().load),
    )
    for name, factory in loaders:
        if ("model", name) in project._callables:  # noqa: SLF001 — internal API
            continue
        project._callables[("model", name)] = HuggingFaceLoader()  # noqa: SLF001
        project._records.append(  # noqa: SLF001
            {
                "schema_version": 1,
                "kind": "component",
                "name": f"model:{name}",
                "version": "1",
                "module": "rlab._loaders",
                "qualname": "HuggingFaceLoader",
                "source": "python/rlab/_loaders.py",
                "tags": ["loader", "huggingface"],
                "description": f"Built-in model loader: builds a model object from `<{name}_path>`.",
                "metadata": {"component_kind": "model"},
            }
        )


__all__ = ["HuggingFaceLoader", "HuggingFaceModel", "register_builtin_loaders"]
