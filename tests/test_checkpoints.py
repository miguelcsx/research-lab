from __future__ import annotations

from pathlib import Path

from rlab import CheckpointManager, JsonObject, RetentionPolicy


class TextSerializer:
    def write(self, path: Path, state: str) -> JsonObject:
        (path / "state.txt").write_text(state, encoding="utf-8")
        return {"state": "state.txt"}

    def read(self, path: Path) -> str:
        return (path / "state.txt").read_text(encoding="utf-8")

    def validate(self, path: Path) -> None:
        if not (path / "state.txt").is_file():
            raise ValueError("checkpoint state is missing")


def test_checkpoint_manager_tracks_aliases_and_retention(tmp_path: Path) -> None:
    manager = CheckpointManager(
        tmp_path,
        TextSerializer(),
        retention=RetentionPolicy(keep_last=1, keep_milestones=True),
    )
    first = manager.save("step-1", "one", step=1, metric=2.0, milestone=True)
    second = manager.save("step-2", "two", step=2, metric=1.0)

    assert manager.load() == "two"
    assert manager.load("best") == "two"
    assert first.path.exists()
    assert second.path.exists()
