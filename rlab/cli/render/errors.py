from rich.console import Console
from rich.panel import Panel


def render_error(console: Console, error: Exception) -> None:
    console.print(
        Panel(str(error), title=type(error).__name__, border_style="red"),
        style="red",
    )
