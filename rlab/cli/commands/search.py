import json
from typing import Annotated

import typer

from rlab.cli.render.tables import table
from rlab.cli.state import CliState

_DEFAULT_SEARCH_LIMIT = 50


def command(
    ctx: typer.Context,
    text: str,
    kinds: Annotated[list[str] | None, typer.Option("--kind")] = None,
    limit: int = typer.Option(_DEFAULT_SEARCH_LIMIT),
) -> None:
    """Full-text search across runs, notes, artifacts, and decisions."""
    state: CliState = ctx.obj
    from rlab.search.index import SearchIndex
    from rlab.search.indexer import rebuild_index

    index_path = state.root / ".rlab" / "search.db"
    search = SearchIndex(index_path)
    # Rebuild on first use / if empty
    rebuild_index(state.root, search)
    results = search.search(text, kinds=tuple(kinds or ()), limit=limit)
    if not results:
        state.console.print("[dim]No results found.[/dim]")
        return
    if state.json_output:
        state.console.print(json.dumps(list(results), indent=2, default=str))
    else:
        state.console.print(table(f'Search: "{text}"', results))
