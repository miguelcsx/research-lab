from collections.abc import Sequence
from pathlib import Path

_DEFAULT_PLOT_WIDTH = 640
_DEFAULT_PLOT_HEIGHT = 320


def line_plot(
    values: Sequence[float],
    output: Path,
    width: int = _DEFAULT_PLOT_WIDTH,
    height: int = _DEFAULT_PLOT_HEIGHT,
) -> None:
    if not values:
        raise ValueError("Plot requires at least one value")
    minimum, maximum = min(values), max(values)
    span = maximum - minimum or 1.0
    points = " ".join(
        f"{index * width / max(1, len(values) - 1):.1f},"
        f"{height - ((value - minimum) / span * height):.1f}"
        for index, value in enumerate(values)
    )
    output.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<polyline fill="none" stroke="black" points="{points}"/></svg>\n'
    )
