from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
import rlab
from rlab.data import classify, materialize, substitute, threshold
from rlab.data.sinks.jsonl import JsonlSink


def test_data_document_extends_and_applies_explicit_overrides(tmp_path: Path) -> None:
    (tmp_path / "base.yaml").write_text(
        "dataset:\n  name: base\nsource:\n  max_rows: 10\n",
        encoding="utf-8",
    )
    (tmp_path / "child.yaml").write_text(
        "extends: base\ndataset:\n  name: child\n",
        encoding="utf-8",
    )

    document = rlab.resolve_dataset(
        tmp_path,
        "child",
        overrides={"source.max_rows": 20},
    )

    assert document == {
        "dataset": {"name": "child"},
        "source": {"max_rows": 20},
    }
    assert rlab.list_datasets(tmp_path) == ("base", "child")
    assert rlab.validate_datasets(tmp_path) == {}
    with pytest.raises(ValueError, match="explicit dotted path"):
        rlab.resolve_dataset(tmp_path, "child", overrides={"max_rows": 20})


def test_data_document_rejects_cycles(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text("extends: b\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("extends: a\n", encoding="utf-8")

    with pytest.raises(ValueError, match="cyclic config inheritance"):
        rlab.resolve_dataset(tmp_path, "a")


@dataclass(frozen=True)
class NestedRecord:
    text: str
    metadata: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {"text": self.text, "metadata": self.metadata}


def test_jsonl_sink_accepts_nested_json_records(tmp_path: Path) -> None:
    path = tmp_path / "records.jsonl"

    JsonlSink(path).write(
        [
            NestedRecord(
                text="hello",
                metadata={"source": "unit", "scores": [1, 2, 3]},
            )
        ]
    )

    assert path.read_text(encoding="utf-8").strip() == (
        '{"metadata":{"scores":[1,2,3],"source":"unit"},"text":"hello"}'
    )


def test_materialize_records_runs_through_native_data_engine() -> None:
    records: list[rlab.JsonObject] = [
        {"text": "hello world", "score": 0.9},
        {"text": "skip me", "score": 0.1},
    ]

    assert materialize(
        records,
        [
            threshold("score", minimum=0.5),
            substitute("text", "world", "rlab"),
            classify("text", {"greeting": "hello"}),
        ],
    ) == [{"text": "hello rlab", "score": 0.9, "label": "greeting"}]
