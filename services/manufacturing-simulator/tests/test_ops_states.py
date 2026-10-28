"""Legality tables and their parity with Core (TEST-SIM-KERNEL).

The Simulator never invents legality. The tables below are checked edge by edge, and
the execution and lifecycle edges are compared with Core's own transition tables by
reading Core's source as text (no import), so a drift on either side fails here.
"""

from __future__ import annotations

import ast
import itertools
import json
from pathlib import Path

import pytest
from manufacturing_simulator.operations import (
    EQUIPMENT_EDGES,
    EXECUTION_EDGES,
    LOT_EDGES,
    EquipmentState,
    ExecutionState,
    IllegalTransition,
    LotLifecycle,
)
from manufacturing_simulator.operations.states import check

ROOT = Path(__file__).resolve().parents[3]
CORE_SOURCE = ROOT / "services/manufacturing-core/src/manufacturing_core/transitions.py"
CORE_SCHEMA = (
    ROOT
    / "services/manufacturing-core/contracts/v1/lot-operational-semantics.v1.schema.json"
)


def core_table(name: str) -> dict[str, set[str]]:
    """Read ``NAME = _matrix({State.A: (State.B, ...), ...})`` from Core's source."""
    tree = ast.parse(CORE_SOURCE.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            call = node.value
            assert isinstance(call, ast.Call) and isinstance(call.args[0], ast.Dict)
            table: dict[str, set[str]] = {}
            for key, value in zip(call.args[0].keys, call.args[0].values, strict=True):
                assert isinstance(key, ast.Attribute) and isinstance(value, ast.Tuple)
                table[key.attr] = {
                    item.attr for item in value.elts if isinstance(item, ast.Attribute)
                }
            return table
    raise AssertionError(f"{name} not found in Core")


@pytest.mark.parametrize(
    ("edges", "states", "kind"),
    [
        (EXECUTION_EDGES, list(ExecutionState), "EXECUTION"),
        (LOT_EDGES, list(LotLifecycle), "LOT"),
        (EQUIPMENT_EDGES, list(EquipmentState), "EQUIPMENT"),
    ],
)
def test_an_edge_is_legal_exactly_when_it_is_listed(
    edges: dict[str, frozenset[str]], states: list[object], kind: str
) -> None:
    for current, target in itertools.product(states, states):
        assert isinstance(current, ExecutionState | LotLifecycle | EquipmentState)
        assert isinstance(target, ExecutionState | LotLifecycle | EquipmentState)
        listed = target.value in edges.get(current.value, frozenset())
        if listed:
            check(edges, kind, current, target)
        else:
            with pytest.raises(IllegalTransition) as caught:
                check(edges, kind, current, target)
            assert caught.value.kind == kind and caught.value.current == current.value


def test_execution_edges_equal_cores_table() -> None:
    ours = {k: set(v) for k, v in EXECUTION_EDGES.items()}
    assert ours == core_table("EXECUTION_TRANSITIONS")


def test_lot_lifecycle_edges_equal_cores_table() -> None:
    ours = {k: set(v) for k, v in LOT_EDGES.items()}
    assert ours == core_table("LOT_TRANSITIONS")


def test_state_vocabularies_are_cores_published_vocabulary() -> None:
    defs = json.loads(CORE_SCHEMA.read_text(encoding="utf-8"))["$defs"]
    assert {s.value for s in ExecutionState} == set(defs["ExecutionState"]["enum"])
    assert {s.value for s in LotLifecycle} == set(defs["LotLifecycle"]["enum"])


def test_equipment_follows_the_documented_repair_path() -> None:
    path = [
        EquipmentState.AVAILABLE,
        EquipmentState.DOWN,
        EquipmentState.MAINTENANCE,
        EquipmentState.QUALIFICATION,
        EquipmentState.AVAILABLE,
    ]
    for current, target in itertools.pairwise(path):
        check(EQUIPMENT_EDGES, "EQUIPMENT", current, target)
    for current, target in [
        (EquipmentState.DOWN, EquipmentState.AVAILABLE),  # no return without repair
        (EquipmentState.BUSY, EquipmentState.MAINTENANCE),  # window waits for idle
        (EquipmentState.MAINTENANCE, EquipmentState.BUSY),
    ]:
        with pytest.raises(IllegalTransition):
            check(EQUIPMENT_EDGES, "EQUIPMENT", current, target)
