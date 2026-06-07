from collections.abc import Sequence
from pathlib import Path


def line_plot(values: Sequence[float], output: Path, width: int = 640, height: int = 320) -> None:
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
