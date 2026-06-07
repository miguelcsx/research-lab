# rlab test suite

This test suite is organized by behavior and domain, not by historical coverage patches.
The intent is to make each test file small, focused, and easy to extend.

## Layout

- `helpers/`: reusable test utilities only. No assertions about product behavior live here unless they are generic test assertions.
- `cli/`: end-to-end command tests through the Typer application.
- `integration/`: workflows that cross multiple bounded contexts.
- `external/`: external process, repository, parser, and sandbox behavior.
- `unit/`: domain-oriented unit tests grouped by production module area.

## Conventions

- Use `invoke_cli()` for every CLI test.
- Use `run_smoke_experiment()` and other factories instead of rebuilding runtime setup in each file.
- Use `assert_success()` and `assert_failure()` so failures include command output and exceptions.
- Prefer one behavioral concept per test function.
- Do not create empty compatibility tests for removed modules.
- Do not add `coverage_fill*` files. Add tests to the relevant domain folder.
