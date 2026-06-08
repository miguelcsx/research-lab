from __future__ import annotations

from pathlib import Path

from rlab.runs.reader import RunReader
from rlab.studies.model import Study


def render_study_report(name: str, study: Study, runs: tuple[Path, ...]) -> str:
    """Generate a markdown report for a study and its linked runs."""
    lines: list[str] = [
        f"# Study: {name}",
        "",
        "## Question",
        "",
        study.question,
        "",
    ]
    if study.hypotheses:
        lines += ["## Hypotheses", ""]
        lines += [f"- {hypothesis}" for hypothesis in study.hypotheses]
        lines.append("")
    if study.variables:
        lines += ["## Variables", "", "| variable | choices |", "|---|---|"]
        for variable, choices in study.variables.items():
            lines.append(f"| {variable} | {', '.join(str(choice) for choice in choices)} |")
        lines.append("")
    if study.outcomes:
        lines += ["## Outcomes", ""]
        lines += [f"- `{outcome}`" for outcome in study.outcomes]
        lines.append("")
    if study.decision_rule:
        lines += ["## Decision rule", "", study.decision_rule, ""]
    if runs:
        lines += ["## Linked runs", ""]
        for run_dir in runs:
            metrics = RunReader(run_dir).metrics_summary()
            metric_text = ", ".join(
                f"`{outcome}`={metrics[outcome]:.6g}"
                for outcome in study.outcomes
                if outcome in metrics
            )
            lines.append(f"- `{run_dir.name}` — {metric_text or 'no recorded outcomes'}")
        lines.append("")
    if study.references:
        lines += ["## References", ""]
        lines += [f"- {reference}" for reference in study.references]
        lines.append("")
    return "\n".join(lines)
