"""Command entrypoint for ``python -m rlab``."""

from __future__ import annotations

import sys


def main() -> int:
    """Run the Rust-owned rlab CLI."""
    from ._rlab import cli_main

    try:
        return int(cli_main())
    except Exception as exc:  # noqa: BLE001 - CLI boundary should not print tracebacks.
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
