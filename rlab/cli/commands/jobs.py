import shlex

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState
from rlab.constants import JOBS_DB_NAME
from rlab.jobs.manager import JobManager
from rlab.jobs.store import JobStore

app = typer.Typer(help="Manage persistent local jobs.")


def _manager(state: CliState) -> JobManager:
    cache = state.runtime().paths.cache
    return JobManager(JobStore(cache / JOBS_DB_NAME), cache / "jobs" / "logs")


@app.command("start")
def start(ctx: typer.Context, command: str) -> None:
    state: CliState = ctx.obj
    state.console.print(_manager(state).start(tuple(shlex.split(command)), state.root).id)


@app.command("list")
def list_jobs(ctx: typer.Context) -> None:
    state: CliState = ctx.obj
    manager = _manager(state)
    jobs = [manager.refresh(job).model_dump(mode="json") for job in manager.store.list()]
    state.console.print(table("Jobs", jobs))


@app.command("cancel")
def cancel(ctx: typer.Context, job_id: str) -> None:
    state: CliState = ctx.obj
    state.console.print(_manager(state).cancel(job_id).status)


@app.command("logs")
def logs(ctx: typer.Context, job_id: str) -> None:
    state: CliState = ctx.obj
    job = _manager(state).store.get(job_id)
    state.console.print(job.log.read_text() if job.log.exists() else "")
