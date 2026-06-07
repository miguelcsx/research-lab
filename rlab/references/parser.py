from rlab.errors import ReferenceError
from rlab.references.refs import Reference, ReferenceKind


def parse_reference(value: str) -> Reference:
    scheme, separator, payload = value.partition(":")
    if not separator or not payload:
        raise ReferenceError(f"Invalid reference {value!r}; expected '<scheme>:<value>'")
    try:
        kind = ReferenceKind(scheme)
        component_kind = None
    except ValueError:
        if not scheme.replace("_", "").replace("-", "").isalnum():
            raise ReferenceError(f"Unsupported reference scheme {scheme!r}") from None
        kind = ReferenceKind.COMPONENT
        component_kind = scheme
    alias = None
    if "@" in payload:
        payload, alias = payload.rsplit("@", maxsplit=1)
    artifact_kind = None
    if kind is ReferenceKind.ARTIFACT:
        artifact_kind, slash, payload = payload.partition("/")
        if not slash or not artifact_kind or not payload:
            raise ReferenceError("Artifact references require artifact:<kind>/<name>")
    return Reference(
        kind=kind,
        value=payload,
        alias=alias,
        artifact_kind=artifact_kind,
        component_kind=component_kind,
    )
