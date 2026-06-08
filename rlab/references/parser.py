from rlab.errors import ReferenceError
from rlab.references.refs import Reference, ReferenceKind

_KNOWN_SCHEMES: frozenset[str] = frozenset(k.value for k in ReferenceKind)


def parse_reference(value: str) -> Reference:
    ref = try_parse_reference(value)
    if ref is not None:
        return ref
    scheme, separator, _ = value.partition(":")
    if not separator:
        raise ReferenceError(f"Invalid reference {value!r}; expected '<scheme>:<value>'")
    if scheme in _KNOWN_SCHEMES:
        raise ReferenceError(f"Invalid reference {value!r}")
    raise ReferenceError(f"Unsupported reference scheme {scheme!r}")


def try_parse_reference(value: str) -> Reference | None:
    scheme, separator, payload = value.partition(":")
    if not separator or not payload:
        return None
    if scheme in _KNOWN_SCHEMES:
        kind = ReferenceKind(scheme)
        component_kind = None
    elif scheme.replace("_", "").replace("-", "").isalnum():
        kind = ReferenceKind.COMPONENT
        component_kind = scheme
    else:
        return None
    alias = None
    if "@" in payload:
        payload, alias = payload.rsplit("@", maxsplit=1)
    artifact_kind = None
    if kind is ReferenceKind.ARTIFACT:
        artifact_kind, slash, payload = payload.partition("/")
        if not slash or not artifact_kind or not payload:
            return None
    return Reference(
        kind=kind,
        value=payload,
        alias=alias,
        artifact_kind=artifact_kind,
        component_kind=component_kind,
    )
