"""Trace graph vocabulary (01 Item 83, 03 §4.2) and the edge identity."""

from __future__ import annotations

import re
from dataclasses import dataclass

SCHEMA_ID = "cap.trace-registry/v1"

# Controlled relation vocabulary, in the order of 03 §4.2. Nothing else is a
# relation: Item 83 #38 prohibits vague relations such as related_to.
RELATIONS: tuple[str, ...] = (
    "DERIVED_FROM",
    "ALLOCATED_TO",
    "DECIDED_BY",
    "EXPOSED_BY",
    "REALIZED_BY",
    "USES_DATA",
    "USES_MODEL",
    "GOVERNED_BY",
    "EXERCISED_IN",
    "VERIFIED_BY",
    "EXECUTED_AS",
    "EVIDENCED_BY",
    "SUPPORTS_CLAIM",
    "MITIGATES",
    "CARRIES_DEBT",
)
PROHIBITED = ("related_to", "maybe_supports", "sort_of_checks")

# PLANNED: the edge comes from the planning baseline (03 Draft).
# RECORDED: the target is something that actually exists or ran
# (a repository path, a run record, an evidence bundle).
APPLICABILITY: tuple[str, ...] = ("PLANNED", "RECORDED")

# Relations whose targets are actual executions or evidence (03 §4.2: populated
# only by real runs and immutable EvidenceBundles).
RECORDED_RELATIONS = frozenset({"EXECUTED_AS", "EVIDENCED_BY", "SUPPORTS_CLAIM"})

REQUIREMENT_ID = re.compile(r"^(?:FR|NFR)-[A-Z]+-[0-9]{3}$")
TBD = "TBD_BY_IMPLEMENTATION"
REPO_PREFIX = "repo:"


@dataclass(frozen=True, order=True)
class Edge:
    """One TraceEdge; its logical identity is from + relation + to (Item 83)."""

    source: str
    relation: str
    target: str
    applicability: str = "PLANNED"

    @property
    def identity(self) -> tuple[str, str, str]:
        return (self.source, self.relation, self.target)

    def to_dict(self) -> dict[str, str]:
        return {
            "from": self.source,
            "relation": self.relation,
            "to": self.target,
            "applicability": self.applicability,
        }

    def label(self) -> str:
        return f"{self.source} {self.relation} {self.target}"
