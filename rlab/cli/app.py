from pathlib import Path

import typer

from rlab.cli.commands import (
    artifacts,
    baselines,
    bench,
    cache,
    ci,
    compare,
    config,
    data,
    diff,
    discover,
    doctor,
    eval,
    exec,
    freeze,
    graph,
    handoff,
    impact,
    init,
    invalidate,
    jobs,
    journal,
    lineage,
    lint,
    modules,
    notes,
    plan,
    report,
    reproduce,
    run,
    runs,
    search,
    status,
)
from rlab.cli.render import console, render_error
from rlab.cli.state import CliState
from rlab.errors import RlabError

app = typer.Typer(
    name="rlab",
    help="Declarative, local-first research runtime.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

# Sub-command groups
app.add_typer(init.app, name="init")
app.add_typer(modules.app, name="modules")
app.add_typer(runs.app, name="runs")
app.add_typer(data.app, name="data")
app.add_typer(artifacts.app, name="artifacts")
app.add_typer(cache.app, name="cache")
app.add_typer(config.app, name="config")
app.add_typer(report.app, name="report")
app.add_typer(jobs.app, name="jobs")
app.add_typer(notes.app, name="notes")
app.add_typer(journal.app, name="journal")
app.add_typer(ci.app, name="ci")
app.add_typer(freeze.app, name="freeze")
app.add_typer(baselines.app, name="baselines")
app.add_typer(plan.app, name="plan")
app.add_typer(graph.app, name="graph")

# Single commands
app.command("run")(run.command)
app.command("bench")(bench.command)
app.command("eval")(eval.command)
app.command("compare")(compare.command)
app.command("reproduce")(reproduce.command)
app.command("discover")(discover.command)
app.command("doctor")(doctor.command)
app.command("status")(status.command)
app.command("lineage")(lineage.command)
app.command("search")(search.command)
app.command("exec")(exec.command)
app.command("diff")(diff.command)
app.command("impact")(impact.command)
app.command("invalidate")(invalidate.command)
app.command("lint")(lint.command)
app.command("handoff")(handoff.command)


@app.callback()
def callback(
    ctx: typer.Context,
    root: Path = typer.Option(Path.cwd(), "--root", exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    ctx.obj = CliState(root=root.resolve(), console=console, json_output=json_output)


def main() -> None:
    try:
        app()
    except RlabError as error:
        render_error(console, error)
        raise SystemExit(2) from error
