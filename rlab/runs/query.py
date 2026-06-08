from __future__ import annotations

import ast
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from rlab.runs.reader import RunReader


def collect_run_rows(runs_dir: Path) -> tuple[dict[str, Any], ...]:
    """Materialize every run directory into a flat row of params + metrics."""
    if not runs_dir.exists():
        return ()
    rows: list[dict[str, Any]] = []
    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        rows.append(_row_for(run_dir))
    return tuple(rows)


def _row_for(run_dir: Path) -> dict[str, Any]:
    reader = RunReader(run_dir)
    row: dict[str, Any] = {"run": run_dir.name, "path": str(run_dir)}
    try:
        manifest = reader.manifest()
        row["operation"] = manifest.operation
        row["status"] = manifest.status.value
        row["tags"] = list(manifest.tags)
    except Exception:
        row["operation"] = ""
        row["status"] = ""
        row["tags"] = []
    for key, value in reader.params().items():
        row[str(key)] = value
    for name, value in reader.metrics_summary().items():
        row[str(name)] = value
    return row


def filter_rows(rows: Iterable[Mapping[str, Any]], where: str | None) -> tuple[dict[str, Any], ...]:
    """Evaluate a safe predicate expression against each row's columns as locals.

    Supports comparisons, ``in``, ``and`` / ``or``, ``not``, and parentheses.
    Unknown names are treated as *missing* and fail the predicate for that row.
    """
    if not where:
        return tuple(dict(row) for row in rows)
    tree = ast.parse(where, "<rlab-query>", mode="eval")
    _validate_predicate(tree)
    matched: list[dict[str, Any]] = []
    for row in rows:
        try:
            if _eval_node(tree.body, dict(row)):
                matched.append(dict(row))
        except Exception:
            continue
    return tuple(matched)


_ALLOWED_NODES: set[type[ast.AST]] = {
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Compare,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.Is,
    ast.IsNot,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Tuple,
    ast.List,
}


def _validate_predicate(tree: ast.Expression) -> None:
    for node in ast.walk(tree):
        if type(node) not in _ALLOWED_NODES:
            raise ValueError(f"Disallowed syntax in query: {type(node).__name__}")


def _eval_node(node: ast.AST, row: dict[str, Any]) -> Any:  # noqa: PLR0911, PLR0912
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return row[node.id]
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, row) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
        raise ValueError(f"Unsupported boolean operator: {type(node.op).__name__}")
    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, row)
        if isinstance(node.op, ast.Not):
            return not operand
        raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, row)
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise ValueError("Chained comparisons are not supported")
        right = _eval_node(node.comparators[0], row)
        op = node.ops[0]
        if isinstance(op, ast.Eq):
            return left == right
        if isinstance(op, ast.NotEq):
            return left != right
        if isinstance(op, ast.Lt):
            return left < right
        if isinstance(op, ast.LtE):
            return left <= right
        if isinstance(op, ast.Gt):
            return left > right
        if isinstance(op, ast.GtE):
            return left >= right
        if isinstance(op, ast.In):
            return left in right
        if isinstance(op, ast.Is):
            return left is right
        if isinstance(op, ast.IsNot):
            return left is not right
        raise ValueError(f"Unsupported comparison operator: {type(op).__name__}")
    if isinstance(node, (ast.Tuple, ast.List)):
        return [_eval_node(elt, row) for elt in node.elts]
    raise ValueError(f"Unsupported expression: {type(node).__name__}")


def sort_rows(
    rows: Iterable[Mapping[str, Any]], order_by: str | None
) -> tuple[dict[str, Any], ...]:
    """Sort rows by ``column`` or ``column desc`` / ``column asc``."""
    rows_list = [dict(row) for row in rows]
    if not order_by:
        return tuple(rows_list)
    parts = order_by.strip().split()
    key = parts[0]
    descending = len(parts) > 1 and parts[1].lower() == "desc"
    rows_list.sort(key=lambda row: _comparable(row.get(key)), reverse=descending)
    return tuple(rows_list)


def group_best(
    rows: Iterable[Mapping[str, Any]], *, metric: str, group_by: str | None, maximize: bool
) -> tuple[dict[str, Any], ...]:
    """Return the best row per ``group_by`` value (or overall if None)."""
    rows_list = [dict(row) for row in rows if metric in row]
    if not rows_list:
        return ()
    if group_by is None:
        return (
            max(rows_list, key=lambda row: row[metric])
            if maximize
            else min(rows_list, key=lambda row: row[metric]),
        )
    bucketed: dict[Any, dict[str, Any]] = {}
    for row in rows_list:
        key = row.get(group_by)
        current = bucketed.get(key)
        if current is None:
            bucketed[key] = row
            continue
        is_better = (maximize and row[metric] > current[metric]) or (
            not maximize and row[metric] < current[metric]
        )
        if is_better:
            bucketed[key] = row
    return tuple(bucketed.values())


def _comparable(value: Any) -> tuple[int, Any]:
    if value is None:
        return (1, 0)
    if isinstance(value, (int, float, str, bool)):
        return (0, value)
    return (0, json.dumps(value, default=str))
