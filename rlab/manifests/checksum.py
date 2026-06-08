import hashlib
from pathlib import Path
from typing import Protocol


class _Digest(Protocol):
    def update(self, data: bytes) -> None: ...


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_dir():
        for child in sorted(item for item in path.rglob("*") if item.is_file()):
            digest.update(child.relative_to(path).as_posix().encode())
            digest.update(b"\0")
            _update_digest(digest, child)
        return digest.hexdigest()
    _update_digest(digest, path)
    return digest.hexdigest()


def _update_digest(digest: _Digest, path: Path) -> None:
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)


def verify_sha256(path: Path, expected: str) -> bool:
    return sha256(path) == expected.removeprefix("sha256:")
