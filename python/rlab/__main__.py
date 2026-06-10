"""Command entrypoint for ``python -m rlab``."""

from __future__ import annotations


def main() -> int:
    """Run the Rust-owned rlab CLI."""
    from ._rlab import cli_main

    return int(cli_main())


if __name__ == "__main__":
    raise SystemExit(main())
