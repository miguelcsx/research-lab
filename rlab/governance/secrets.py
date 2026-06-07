import re

_SECRET_PATTERNS = re.compile(
    r"(token|secret|key|password|passwd|pwd|credential|api_key|access_key|private_key|auth)",
    re.IGNORECASE,
)

_DEFAULT_REDACTED = "[REDACTED]"


def redact_secrets(
    env: dict[str, str],
    allowlist: tuple[str, ...] = (),
) -> dict[str, str]:
    """Return env dict with secret-looking values replaced with [REDACTED]."""
    result: dict[str, str] = {}
    for key, value in env.items():
        if key in allowlist:
            result[key] = value
        elif _SECRET_PATTERNS.search(key):
            result[key] = _DEFAULT_REDACTED
        else:
            result[key] = value
    return result


def scan_for_secrets(text: str) -> list[str]:
    """Return a list of suspicious lines in text that look like secrets."""
    suspicious: list[str] = []
    for line in text.splitlines():
        if _SECRET_PATTERNS.search(line) and "=" in line:
            suspicious.append(line.strip())
    return suspicious
