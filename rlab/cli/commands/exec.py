from __future__ import annotations

import importlib
import json
import subprocess
import time
from pathlib import Path
from typing import Annotated

import typer

from rlab.cli.state import CliState


def command(
    ctx: typer.Context,
    name: Annotated[str, typer.Option("--name", "-n")],
    command_args: Annotated[list[str], typer.Argument()],
    cwd: Annotated[Path | None, typer.Option("--cwd")] = None,
    timeout: Annotated[int | None, typer.Option("--timeout")] = None,
    metric_parser: Annotated[str | None, typer.Option("--parser")] = None,
) -> None:
    """Execute an arbitrary command under rlab tracking."""
    state: CliState = ctx.obj

    start = time.monotonic()
    result = subprocess.run(
        command_args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    elapsed = time.monotonic() - start

    record: dict[str, object] = {
        "name": name,
        "command": command_args,
        "returncode": result.returncode,
        "runtime_seconds": round(elapsed, 3),
        "cwd": str(cwd) if cwd else None,
    }

    if metric_parser and result.returncode == 0:
        if ":" not in metric_parser:
            state.console.print(f"[yellow]Parser must be 'module:function', got {metric_parser!r}[/yellow]")
        else:
            module_path, func_name = metric_parser.rsplit(":", 1)
            try:
                func = getattr(importlib.import_module(module_path), func_name)
                record["metrics"] = func(result.stdout)
            except (ImportError, AttributeError) as exc:
                state.console.print(f"[yellow]Parser not found: {exc}[/yellow]")
            except Exception as exc:  # noqa: BLE001 — user-provided parser may raise anything
                state.console.print(f"[yellow]Parser failed: {exc}[/yellow]")

    # Append to exec log
    exec_log = state.root / ".rlab" / "exec_log.jsonl"
    exec_log.parent.mkdir(parents=True, exist_ok=True)
    with exec_log.open("a") as f:
        f.write(json.dumps(record, default=str) + "\n")

    # Show result
    if result.returncode == 0:
        state.console.print(f"[green]✓[/green] {name} completed in {elapsed:.1f}s")
    else:
        state.console.print(f"[red]✗[/red] {name} failed (exit {result.returncode})")
        if result.stderr:
            state.console.print(result.stderr[-1000:])
        raise typer.Exit(result.returncode)

    if result.stdout:
        state.console.print(result.stdout[-2000:])
