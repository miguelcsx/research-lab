from __future__ import annotations

import json
from pathlib import Path

from rlab.reports import write_card
from rlab.runs import RunQuery
from rlab.stats import paired_bootstrap


def test_run_query_filters_target_and_seed(tmp_path: Path) -> None:
    run = tmp_path / "run-1"
    run.mkdir()
    (run / "run.json").write_text(
        json.dumps(
            {
                "target": {"kind": "experiment", "name": "demo"},
                "seed": 7,
            }
        ),
        encoding="utf-8",
    )
    (run / "params.json").write_text('{"model": "small"}', encoding="utf-8")
    (run / "metrics_summary.json").write_text(
        '{"metrics": {"accuracy": 0.75}}',
        encoding="utf-8",
    )

    records = RunQuery(tmp_path).find(target="experiment:*", seed=7)

    assert len(records) == 1
    assert records[0].metrics == {"accuracy": 0.75}


def test_paired_bootstrap_is_deterministic() -> None:
    first = paired_bootstrap([1.0, 2.0, 4.0], [2.0, 2.5, 5.5], samples=200)
    second = paired_bootstrap([1.0, 2.0, 4.0], [2.0, 2.5, 5.5], samples=200)

    assert first == second
    assert first.confidence_interval is not None
    assert first.delta == 1.0


def test_write_card_renders_sections(tmp_path: Path) -> None:
    output = write_card(
        tmp_path / "card.md",
        title="Model Card",
        sections={"Training": {"seed": 7, "status": "complete"}},
    )

    text = output.read_text(encoding="utf-8")
    assert "# Model Card" in text
    assert "## Training" in text
