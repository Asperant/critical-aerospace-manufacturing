"""Strict decoding of decision requests and dispatch intakes (TEST-SIM-DECISIONIF)."""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest
from dispatch_fixtures import intake_document
from hypothesis import given
from hypothesis import strategies as st
from manufacturing_simulator import (
    DecisionContractError,
    DispatchIntake,
    RejectReason,
    decode_intake,
    decode_request,
)
from manufacturing_simulator.decision import loads_document

REQUEST: dict[str, Any] = {
    "contract_version": "simulator.decision-request.v1",
    "world_id": "world-1",
    "request_id": "REQ-1",
    "state_revision": "rev-1",
    "simulation_time": {"value": 10, "unit": "us"},
    "provenance": "SIMULATION",
    "decision_point": {"kind": "MACHINE_AVAILABLE", "machine_id": "M1"},
    "candidates": [
        {
            "lot_id": "L1",
            "lot_revision": "L1-r1",
            "route_step": "ROUGH-MILL",
            "priority": 2,
            "due_at": 90,
            "ready_at": 5,
            "eligible_machine_ids": ["M1", "M2"],
        }
    ],
}


def code_of(call: Any, *args: Any) -> RejectReason:
    with pytest.raises(DecisionContractError) as caught:
        call(*args)
    return caught.value.code


def test_documents_round_trip_exactly() -> None:
    intake = decode_intake(intake_document())
    assert intake.to_document() == intake_document()
    request = decode_request(REQUEST)
    assert request.to_document() == REQUEST
    assert decode_intake(json.dumps(intake_document())) == intake


def mutated(base: dict[str, Any], path: list[str | int], value: Any) -> dict[str, Any]:
    result = copy.deepcopy(base)
    node: Any = result
    for step in path[:-1]:
        node = node[step]
    if value is KeyError:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return result


INTAKE_BAD: list[tuple[list[str | int], Any, RejectReason]] = [
    (
        ["contract_version"],
        "simulator.dispatch-intake.v2",
        RejectReason.UNSUPPORTED_VERSION,
    ),
    (["contract_version"], KeyError, RejectReason.MALFORMED),
    (["extra"], 1, RejectReason.MALFORMED),
    (["dispatch_id"], "", RejectReason.MALFORMED),
    (["dispatch_id"], "has space", RejectReason.MALFORMED),
    (["dispatch_id"], " padded", RejectReason.MALFORMED),
    (["dispatch_id"], 5, RejectReason.MALFORMED),
    (["lot_id"], None, RejectReason.MALFORMED),
    (["request_id"], "", RejectReason.MALFORMED),
    (["decision_time"], 5, RejectReason.MALFORMED),
    (["decision_time", "value"], -1, RejectReason.MALFORMED),
    (["decision_time", "value"], True, RejectReason.MALFORMED),
    (["decision_time", "value"], 1.5, RejectReason.MALFORMED),
    (["decision_time", "value"], 2**53, RejectReason.MALFORMED),
    (["decision_time", "unit"], "ms", RejectReason.MALFORMED),
    (["rule"], {"id": "r"}, RejectReason.MALFORMED),
    (["rule", "version"], "", RejectReason.MALFORMED),
    (["schedule_version"], "", RejectReason.MALFORMED),
    (["source"], "SCHEDULER", RejectReason.MALFORMED),
    (["reason"], "", RejectReason.MALFORMED),
    (["reason"], " padded ", RejectReason.MALFORMED),
    (["oracle_label"], "x", RejectReason.ORACLE_FIELD_REJECTED),
    (["rule", "ground_truth"], 1, RejectReason.ORACLE_FIELD_REJECTED),
]


@pytest.mark.parametrize(("path", "value", "code"), INTAKE_BAD)
def test_intake_rejection_matrix(
    path: list[str | int], value: Any, code: RejectReason
) -> None:
    document = mutated(intake_document(), path, value)
    assert code_of(decode_intake, document) is code


def test_nullable_fields_accept_null_and_no_other_field_does() -> None:
    document = intake_document(request_id=None, schedule_version=None)
    intake = decode_intake(document)
    assert intake.request_id is None and intake.schedule_version is None
    for name in intake_document():
        if name in {"request_id", "schedule_version"}:
            continue
        assert code_of(decode_intake, mutated(intake_document(), [name], None)) in {
            RejectReason.MALFORMED,
            RejectReason.UNSUPPORTED_VERSION,
        }


REQUEST_BAD: list[tuple[list[str | int], Any, RejectReason]] = [
    (["provenance"], "REAL", RejectReason.UNSUPPORTED_VERSION),
    (["decision_point", "kind"], "LOT_ARRIVED", RejectReason.MALFORMED),
    (["candidates"], {}, RejectReason.MALFORMED),
    (["candidates", 0, "priority"], -1, RejectReason.MALFORMED),
    (["candidates", 0, "eligible_machine_ids"], ["M1", "M1"], RejectReason.MALFORMED),
    (["candidates", 0, "eligible_machine_ids"], "M1", RejectReason.MALFORMED),
    (["candidates", 0, "ground_truth"], 1, RejectReason.ORACLE_FIELD_REJECTED),
    (["candidates", 0, "lot_id"], KeyError, RejectReason.MALFORMED),
]


@pytest.mark.parametrize(("path", "value", "code"), REQUEST_BAD)
def test_request_rejection_matrix(
    path: list[str | int], value: Any, code: RejectReason
) -> None:
    assert code_of(decode_request, mutated(REQUEST, path, value)) is code


def test_duplicate_candidate_lots_are_rejected() -> None:
    document = copy.deepcopy(REQUEST)
    document["candidates"].append(copy.deepcopy(document["candidates"][0]))
    assert code_of(decode_request, document) is RejectReason.MALFORMED


@pytest.mark.parametrize(
    "text",
    ['{"a": 1, "a": 2}', '{"a": NaN}', '{"a": Infinity}', '{"a": 1e999}', "{", ""],
)
def test_json_text_is_decoded_strictly(text: str) -> None:
    assert code_of(loads_document, text) is RejectReason.MALFORMED


def test_errors_name_a_path_and_never_repeat_input() -> None:
    secret = "SECRET-VALUE-123"
    document = mutated(intake_document(), ["lot_id"], f"{secret} x")
    with pytest.raises(DecisionContractError) as caught:
        decode_intake(document)
    assert secret not in str(caught.value) and caught.value.path == "/lot_id"


ident = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs", "Zs", "Cc"), blacklist_characters=" "
    ),
    min_size=1,
    max_size=12,
)


@given(
    dispatch_id=ident,
    lot=ident,
    machine=ident,
    when=st.integers(0, 2**53 - 1),
    reason=ident,
)
def test_any_valid_intake_round_trips(
    dispatch_id: str, lot: str, machine: str, when: int, reason: str
) -> None:
    document = intake_document(
        dispatch_id=dispatch_id,
        lot_id=lot,
        machine_id=machine,
        decision_time={"value": when, "unit": "us"},
        reason=reason,
    )
    decoded = decode_intake(document)
    assert isinstance(decoded, DispatchIntake)
    assert decoded.to_document() == document
    assert decode_intake(json.dumps(document)) == decoded
