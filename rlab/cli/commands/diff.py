from __future__ import annotations

import json
from pathlib import Path

import typer

from rlab.cli.state import CliState


def command(ctx: typer.Context, run_a: Path, run_b: Path) -> None:
    """Show what changed between two runs."""
    state: CliState = ctx.obj
    from rlab.runs.reader import RunReader

    reader_a = RunReader(run_a)
    reader_b = RunReader(run_b)

    params_a = reader_a.params()
    params_b = reader_b.params()
    metrics_a = reader_a.metrics_summary()
    metrics_b = reader_b.metrics_summary()

    all_param_keys = sorted(set(params_a) | set(params_b))
    all_metric_keys = sorted(set(metrics_a) | set(metrics_b))

    state.console.print(f"\n[bold]Comparing:[/bold]")
    state.console.print(f"  A: {run_a.name}")
    state.console.print(f"  B: {run_b.name}")

    changed_params: list[str] = []
    if all_param_keys:
        state.console.print("\n[bold]Parameters:[/bold]")
        for key in all_param_keys:
            va = params_a.get(key, "[missing]")
            vb = params_b.get(key, "[missing]")
            if va != vb:
                state.console.print(f"  [yellow]{key}[/yellow]: {va!r} → {vb!r}")
                changed_params.append(key)
            else:
                state.console.print(f"  {key}: {va!r} (unchanged)")

    if all_metric_keys:
        state.console.print("\n[bold]Metrics:[/bold]")
        for key in all_metric_keys:
            va = metrics_a.get(key)
            vb = metrics_b.get(key)
            if va is None:
                state.console.print(f"  {key}: [missing] → {vb:.6g}")
            elif vb is None:
                state.console.print(f"  {key}: {va:.6g} → [missing]")
            elif abs(va - vb) > 1e-9:
                delta = vb - va
                state.console.print(f"  [cyan]{key}[/cyan]: {va:.6g} → {vb:.6g} ({delta:+.6g})")
            else:
                state.console.print(f"  {key}: {va:.6g} (unchanged)")

    # Git diff of reproducibility
    git_a = run_a / "reproducibility" / "git.json"
    git_b = run_b / "reproducibility" / "git.json"
    if git_a.exists() and git_b.exists():
        data_a = json.loads(git_a.read_text())
        data_b = json.loads(git_b.read_text())
        commit_a = data_a.get("commit", "")
        commit_b = data_b.get("commit", "")
        if commit_a != commit_b:
            state.console.print(f"\n[bold]Code:[/bold] commit changed {commit_a[:8]} → {commit_b[:8]}")
        else:
            state.console.print(f"\n[bold]Code:[/bold] same commit ({commit_a[:8]})")

    if not changed_params and not all_metric_keys:
        state.console.print("\n[dim]No differences found.[/dim]")
