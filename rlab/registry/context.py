from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from rlab.registry.global_store import registry as default_registry
from rlab.registry.store import Registry

_ACTIVE: ContextVar[Registry] = ContextVar("rlab_registry", default=default_registry)


def current_registry() -> Registry:
    return _ACTIVE.get()


@contextmanager
def using_registry(registry: Registry) -> Iterator[None]:
    token = _ACTIVE.set(registry)
    try:
        yield
    finally:
        _ACTIVE.reset(token)
