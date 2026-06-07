from typing import Annotated

import typer

RootOption = Annotated[str | None, typer.Option("--root", help="Project root")]
JsonOption = Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON")]
