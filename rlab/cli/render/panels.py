from rich.panel import Panel


def result_panel(title: str, body: str, *, success: bool = True) -> Panel:
    return Panel(body, title=title, border_style="green" if success else "red")
