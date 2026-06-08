from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

from rlab.runs.reader import RunReader


def render_run_report(run_dir: Path) -> str:
    """Render a markdown report for a completed run."""
    reader = RunReader(run_dir)
    lines: list[str] = [f"# Run Report: {run_dir.name}\n"]

    _header_section(lines, reader)
    _params_section(lines, reader)
    _metrics_section(lines, reader)
    _figures_section(lines, reader, run_dir)
    _tables_section(lines, reader, run_dir)
    _notes_section(lines, reader)
    return "\n".join(lines)


def render_experiment_report(run_dir: Path) -> str:
    """Render a full scientific narrative report for an experiment run.

    Loads the experiment definition (if available) and produces:
    Question, Hypothesis, Design, Variables, Results, Threats, Decision.
    """
    reader = RunReader(run_dir)
    lines: list[str] = [f"# Experiment Report: {run_dir.name}\n"]

    experiment = _load_experiment_definition(reader)
    _experiment_header(lines, reader, experiment)
    _design_section(lines, experiment)
    _params_section(lines, reader)
    _metrics_section(lines, reader)
    _results_section(lines, reader, experiment)
    _figures_section(lines, reader, run_dir)
    _tables_section(lines, reader, run_dir)
    _threats_section(lines, experiment)
    _notes_section(lines, reader)
    return "\n".join(lines)


def _header_section(lines: list[str], reader: Any) -> None:
    if reader.layout.manifest_file.exists():
        try:
            manifest = reader.manifest()
            lines.append(f"**Operation:** {manifest.operation}")
            lines.append(f"**Status:** {manifest.status.value}")
            lines.append(f"**Created:** {manifest.created_at.isoformat()}")
            if manifest.tags:
                lines.append(f"**Tags:** {', '.join(manifest.tags)}")
            lines.append("")
        except Exception:
            lines.append("*Manifest incomplete or unreadable.*")
            lines.append("")


def _experiment_header(lines: list[str], reader: Any, experiment: Any) -> None:
    if experiment is not None and experiment.get("question"):
        lines.append("## Question\n")
        lines.append(f"{experiment['question']}\n")
        if experiment.get("hypothesis"):
            lines.append("## Hypothesis\n")
            lines.append(f"{experiment['hypothesis']}\n")
    else:
        _header_section(lines, reader)


def _design_section(lines: list[str], experiment: Any) -> None:
    if experiment is None:
        return
    if experiment.get("decision_criteria"):
        lines.append("## Decision Criteria\n")
        lines.append(f"{experiment['decision_criteria']}\n")
    matrix = experiment.get("matrix")
    if matrix:
        lines.append("## Variables\n")
        lines.append("| Variable | Values |")
        lines.append("|---|---|")
        for k, v in sorted(matrix.items()):
            values = ", ".join(str(x) for x in v)
            lines.append(f"| {k} | {values} |")
        lines.append("")
    refs = experiment.get("references", ())
    if refs:
        lines.append("## References\n")
        for ref in refs:
            lines.append(f"- {ref}")
        lines.append("")


def _results_section(lines: list[str], reader: Any, experiment: Any) -> None:
    results = reader.results()
    if results and experiment is not None:
        lines.append("## Results Summary\n")
        steps = results.get("steps", ())
        total = len(steps)
        failed = sum(1 for s in steps if s.get("error"))
        lines.append(f"- Total jobs: {total}")
        lines.append(f"- Successful: {total - failed}")
        lines.append(f"- Failed: {failed}")
        lines.append("")
        if experiment.get("assumptions"):
            lines.append("## Assumptions\n")
            for a in experiment["assumptions"]:
                lines.append(f"- {a}")
            lines.append("")


def _threats_section(lines: list[str], experiment: Any) -> None:
    if experiment is None:
        return
    threats = experiment.get("threats", ())
    if threats:
        lines.append("## Threats to Validity\n")
        for t in threats:
            lines.append(f"- {t}")
        lines.append("")


def _params_section(lines: list[str], reader: Any) -> None:
    params = reader.params()
    if params:
        lines.append("## Parameters\n")
        lines.append("| Parameter | Value |")
        lines.append("|---|---|")
        for k, v in sorted(params.items()):
            lines.append(f"| {k} | {v} |")
        lines.append("")


def _metrics_section(lines: list[str], reader: Any) -> None:
    metrics = reader.metrics_summary()
    if metrics:
        lines.append("## Metrics\n")
        lines.append("| Metric | Value |")
        lines.append("|---|---|")
        for k, v in sorted(metrics.items()):
            lines.append(f"| {k} | {v:.6g} |")
        lines.append("")


def _figures_section(lines: list[str], reader: Any, run_dir: Path) -> None:
    figures = reader.figures()
    if figures:
        lines.append("## Figures\n")
        for fig in figures:
            rel = fig.relative_to(run_dir)
            lines.append(f"- [{fig.name}]({rel})")
        lines.append("")


def _tables_section(lines: list[str], reader: Any, run_dir: Path) -> None:
    tables = reader.tables()
    if tables:
        lines.append("## Tables\n")
        for tbl in tables:
            rel = tbl.relative_to(run_dir)
            lines.append(f"- [{tbl.name}]({rel})")
        lines.append("")


def _notes_section(lines: list[str], reader: Any) -> None:
    notes = reader.notes()
    if notes:
        lines.append("## Notes\n")
        for note in notes:
            ts = note.get("timestamp", "")
            text = note.get("text", "")
            lines.append(f"- *{ts}*: {text}")
        lines.append("")


def _load_experiment_definition(reader: Any) -> dict[str, Any] | None:
    """Try to recover the experiment definition from the run directory."""
    params = reader.params()
    exp_path_str = params.get("path")
    if not exp_path_str:
        return None
    exp_path = Path(exp_path_str)
    if not exp_path.exists():
        return None
    return _cached_experiment_dump(exp_path)


@functools.lru_cache(maxsize=128)
def _cached_experiment_dump(exp_path: Path) -> dict[str, Any] | None:
    try:
        from rlab.experiments.loader import load_experiment  # noqa: PLC0415
        from rlab.registry.context import current_registry  # noqa: PLC0415

        registry = current_registry()
        _name, experiment = load_experiment(registry, exp_path)
        return experiment.model_dump(mode="json")
    except Exception:
        return None
