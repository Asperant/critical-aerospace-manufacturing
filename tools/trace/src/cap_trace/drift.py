"""Drift between the committed registry and the current 03 §17 records.

03 §17 is the source (decision of 25 October 2026, option A): owners keep editing
03 §17 in their own PRs and refresh the registry and its views with
`mfgctl trace seed`. CI runs `drift --strict`, so a PR that changes 03 §17
without refreshing the registry fails with the exact command to run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast


@dataclass
class Drift:
    added_edges: list[str] = field(default_factory=list[str])
    removed_edges: list[str] = field(default_factory=list[str])
    added_requirements: list[str] = field(default_factory=list[str])
    removed_requirements: list[str] = field(default_factory=list[str])
    changed_requirements: list[str] = field(default_factory=list[str])

    @property
    def empty(self) -> bool:
        return not (
            self.added_edges
            or self.removed_edges
            or self.added_requirements
            or self.removed_requirements
            or self.changed_requirements
        )

    def lines(self) -> list[str]:
        out: list[str] = []
        for title, items in (
            ("edge in 03 §17, missing from the registry", self.added_edges),
            ("edge in the registry, no longer in 03 §17", self.removed_edges),
            (
                "requirement in 03 §17, missing from the registry",
                self.added_requirements,
            ),
            (
                "requirement in the registry, no longer in 03 §17",
                self.removed_requirements,
            ),
            ("requirement attributes differ", self.changed_requirements),
        ):
            out.extend(f"DRIFT {title}: {item}" for item in items)
        return out


def _labels(registry: dict[str, Any]) -> set[str]:
    edges = cast(list[dict[str, str]], registry.get("edges", []))
    return {
        f"{e['from']} {e['relation']} {e['to']} [{e['applicability']}]" for e in edges
    }


def compare(committed: dict[str, Any], current: dict[str, Any]) -> Drift:
    """`current` is the registry seeded from 03 now; `committed` is the file."""
    old_nodes = cast(dict[str, Any], committed.get("requirements", {}))
    new_nodes = cast(dict[str, Any], current.get("requirements", {}))
    old_edges, new_edges = _labels(committed), _labels(current)
    return Drift(
        added_edges=sorted(new_edges - old_edges),
        removed_edges=sorted(old_edges - new_edges),
        added_requirements=sorted(set(new_nodes) - set(old_nodes)),
        removed_requirements=sorted(set(old_nodes) - set(new_nodes)),
        changed_requirements=sorted(
            r for r in set(old_nodes) & set(new_nodes) if old_nodes[r] != new_nodes[r]
        ),
    )
