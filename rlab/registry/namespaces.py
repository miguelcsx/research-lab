import re

from rlab.errors import RegistryError

NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]*$")


def validate_name(name: str) -> str:
    if not NAME_PATTERN.fullmatch(name):
        raise RegistryError(
            f"Invalid registry name {name!r}; use letters, numbers, '.', ':', '_' or '-'"
        )
    return name


def qualified_name(namespace: str | None, name: str) -> str:
    return validate_name(f"{namespace}.{name}" if namespace else name)
