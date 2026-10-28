"""Evaluator-only (Oracle) field detection shared by the decision and exposure code.

The Simulator owns hidden ground truth. Nothing it accepts or exposes operationally
may carry a field that names it. Detection is on field names, iterative so a deeply
nested payload cannot exhaust the interpreter stack, and never reads values.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_MARKERS = ("oracle", "ground_truth", "groundtruth", "true_root_cause")


def is_evaluator_field(name: object) -> bool:
    """True if a field name mentions evaluator-only truth."""
    if not isinstance(name, str):
        return False
    folded = name.casefold().replace("-", "_").replace(" ", "_")
    return any(marker in folded for marker in _MARKERS)


def find_evaluator_field(value: Any) -> str | None:
    """Path of the first mapping key that names evaluator-only truth, else ``None``."""
    stack: list[tuple[str, Any]] = [("", value)]
    while stack:
        here, node = stack.pop()
        if isinstance(node, Mapping):
            fields: Mapping[Any, Any] = node
            for key, child in fields.items():
                if is_evaluator_field(key):
                    return f"{here}/{key}"
                stack.append((f"{here}/{key}", child))
        elif isinstance(node, list | tuple):
            items: list[Any] | tuple[Any, ...] = node
            stack.extend(
                (f"{here}/{index}", child) for index, child in enumerate(items)
            )
    return None
