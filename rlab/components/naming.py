from rlab.references.parser import try_parse_reference

_DEFAULT_ATTRIBUTES = ("name",)


def display_name(
    value: object,
    *,
    attributes: tuple[str, ...] = _DEFAULT_ATTRIBUTES,
    default: str = "",
) -> str:
    """Best-effort human-readable name for a reference string or component.

    Reference strings (``model:project.constant``, ``hf:org/model``) resolve to
    their payload; other strings pass through unchanged. Objects are probed for
    the given ``attributes`` in order — pass domain-specific attribute names
    (e.g. ``("name_or_path", "name")`` for HuggingFace models) when the default
    is not enough. Returns ``default`` when no name can be derived.
    """
    if isinstance(value, str):
        reference = try_parse_reference(value)
        return reference.value if reference is not None else value

    for attribute in attributes:
        found = getattr(value, attribute, None)
        if isinstance(found, str) and found:
            return found

    return default
