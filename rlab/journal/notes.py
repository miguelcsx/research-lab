from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Note(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    timestamp: str = ""
    run_id: str | None = None
    author: str | None = None


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def add_note(path: Path, text: str, *, run_id: str | None = None, author: str | None = None) -> Note:
    note = Note(text=text, timestamp=_now(), run_id=run_id, author=author)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(note.model_dump_json() + "\n")
    return note


def list_notes(path: Path) -> tuple[Note, ...]:
    if not path.exists():
        return ()
    return tuple(
        Note.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    )
