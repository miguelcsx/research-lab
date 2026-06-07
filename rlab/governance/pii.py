import re
from pydantic import BaseModel, ConfigDict


class PiiHit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    value: str
    line: int


_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PHONE = re.compile(r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_IP = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")


def scan_for_pii(text: str) -> tuple[PiiHit, ...]:
    hits: list[PiiHit] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _EMAIL.finditer(line):
            hits.append(PiiHit(kind="email", value=match.group(), line=lineno))
        for match in _PHONE.finditer(line):
            hits.append(PiiHit(kind="phone", value=match.group(), line=lineno))
        for match in _SSN.finditer(line):
            hits.append(PiiHit(kind="ssn", value="[REDACTED]", line=lineno))
        for match in _IP.finditer(line):
            hits.append(PiiHit(kind="ip_address", value=match.group(), line=lineno))
    return tuple(hits)
