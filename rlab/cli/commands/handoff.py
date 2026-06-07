from __future__ import annotations

from pathlib import Path

import typer

from rlab.cli.state import CliState


def command(
    ctx: typer.Context,
    run_id: str,
    to: str = typer.Option(..., "--to"),
    output: Path | None = typer.Option(None, "--output"),
) -> None:
    """Generate a handoff document for another team."""
    state: CliState = ctx.obj
    runs_dir = state.root / "runs"
    run_dir = next(
        (d for d in runs_dir.iterdir() if d.is_dir() and (d.name == run_id or d.name.endswith(run_id))),
        None,
    ) if runs_dir.exists() else None

    if run_dir is None:
        raise typer.BadParameter(f"Run {run_id!r} not found")

    from rlab.runs.reader import RunReader
    from rlab.reports.markdown import render_run_report
    reader = RunReader(run_dir)

    lines: list[str] = [
        f"# Handoff: {run_dir.name} → {to}\n",
        "## Context\n",
        f"Generated from run: `{run_dir.name}`\n",
        "## How to Reproduce\n",
        "```bash",
        f"uv run rlab reproduce {run_dir}",
        "```\n",
        "## Results Summary\n",
    ]
    metrics = reader.metrics_summary()
    for k, v in sorted(metrics.items()):
        lines.append(f"- **{k}**: {v:.6g}")
    lines.append("")

    notes = reader.notes()
    if notes:
        lines.append("## Notes\n")
        for n in notes:
            lines.append(f"- {n.get('text', '')}")
        lines.append("")

    lines.extend([
        "## Known Issues\n",
        "- (fill in known issues)\n",
        "## Suggested Next Experiments\n",
        "- (fill in suggestions)\n",
    ])

    content = "\n".join(lines)
    dest = output or (run_dir / "handoff.md")
    dest.write_text(content)
    state.console.print(f"[green]Handoff document written:[/green] {dest}")
