"""Compatibility exports for the Python runner host process."""

from __future__ import annotations

from .runner import RuntimeContext, main

if __name__ == "__main__":
    raise SystemExit(main())
