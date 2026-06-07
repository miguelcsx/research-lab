from pathlib import Path

import typer

from rlab.cli.commands import (
    artifacts,
    bench,
    cache,
    compare,
    config,
    data,
    discover,
    doctor,
    eval,
    init,
    jobs,
    lineage,
    plugins,
    report,
    reproduce,
    run,
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

app.add_typer(init.app, name="init")
app.add_typer(plugins.app, name="plugins")
app.add_typer(data.app, name="data")
app.add_typer(artifacts.app, name="artifacts")
app.add_typer(cache.app, name="cache")
app.add_typer(config.app, name="config")
app.add_typer(report.app, name="report")
app.add_typer(jobs.app, name="jobs")

app.command("run")(run.command)
app.command("bench")(bench.command)
app.command("eval")(eval.command)
app.command("compare")(compare.command)
app.command("reproduce")(reproduce.command)
app.command("discover")(discover.command)
app.command("doctor")(doctor.command)
app.command("status")(status.command)
app.command("lineage")(lineage.command)


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
