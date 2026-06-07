from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class NegativeResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    hypothesis: str
    tried: str
    reason: str
    evidence: str = ""
    recommendation: str = ""
    run_ids: tuple[str, ...] = ()
    created_at: str = ""
    tags: tuple[str, ...] = ()


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def add_negative(
    path: Path,
    hypothesis: str,
    tried: str,
    reason: str,
    *,
    evidence: str = "",
    recommendation: str = "",
    run_ids: tuple[str, ...] = (),
    tags: tuple[str, ...] = (),
) -> NegativeResult:
    entry = NegativeResult(
        hypothesis=hypothesis,
        tried=tried,
        reason=reason,
        evidence=evidence,
        recommendation=recommendation,
        run_ids=run_ids,
        created_at=_now(),
        tags=tags,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(entry.model_dump_json() + "\n")
    return entry


def list_negatives(path: Path) -> tuple[NegativeResult, ...]:
    if not path.exists():
        return ()
    return tuple(
        NegativeResult.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    )


def search_negatives(path: Path, text: str) -> tuple[NegativeResult, ...]:
    text_lower = text.lower()
    return tuple(
        e for e in list_negatives(path)
        if text_lower in e.hypothesis.lower()
        or text_lower in e.tried.lower()
        or text_lower in e.reason.lower()
        or text_lower in e.evidence.lower()
    )
