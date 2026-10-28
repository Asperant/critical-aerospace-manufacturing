"""The published JSON Schemas and the typed decoder describe the same messages.

TEST-SIM-DECISIONIF (contract acceptance): every fixture validates, every typed
document validates, every document the decoder refuses is also refused by the schema,
and the reason-code enum equals the code set. Nothing here proves behaviour.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from dispatch_fixtures import intake_document
from jsonschema import Draft202012Validator
from manufacturing_simulator import (
    DecisionContractError,
    DispatchOutcome,
    IntakeSource,
    OutcomeStatus,
    RejectReason,
    decode_intake,
    decode_request,
)
from test_decision_messages import INTAKE_BAD, REQUEST, REQUEST_BAD, mutated

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts" / "v1"


def schema(name: str) -> Draft202012Validator:
    document = json.loads((CONTRACTS / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(document)
    return Draft202012Validator(document)


def fixture(name: str) -> Any:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


REQUEST_SCHEMA = schema("decision-request.v1.schema.json")
INTAKE_SCHEMA = schema("dispatch-intake.v1.schema.json")
OUTCOME_SCHEMA = schema("dispatch-outcome.v1.schema.json")


def test_every_fixture_validates_and_decodes() -> None:
    assert REQUEST_SCHEMA.is_valid(fixture("decision-request.v1.json"))
    assert INTAKE_SCHEMA.is_valid(fixture("dispatch-intake.v1.json"))
    assert OUTCOME_SCHEMA.is_valid(fixture("dispatch-outcome.v1.json"))
    assert OUTCOME_SCHEMA.is_valid(fixture("dispatch-outcome.rejected.json"))
    assert decode_request(fixture("decision-request.v1.json")).to_document() == fixture(
        "decision-request.v1.json"
    )
    assert decode_intake(fixture("dispatch-intake.v1.json")).to_document() == fixture(
        "dispatch-intake.v1.json"
    )


def test_typed_documents_validate_for_every_source_and_outcome() -> None:
    for source in IntakeSource:
        assert INTAKE_SCHEMA.is_valid(intake_document(source=source.value))
    assert INTAKE_SCHEMA.is_valid(
        intake_document(request_id=None, schedule_version="s1")
    )
    for reason in RejectReason:
        rejected = DispatchOutcome(None, "w", OutcomeStatus.REJECTED, reason, 0, "r")
        assert OUTCOME_SCHEMA.is_valid(rejected.to_document()), reason
    accepted = DispatchOutcome("d", "w", OutcomeStatus.ACCEPTED, None, 0, "r")
    assert OUTCOME_SCHEMA.is_valid(accepted.to_document())


def test_the_outcome_schema_ties_status_to_reason_code() -> None:
    document = DispatchOutcome(
        "d", "w", OutcomeStatus.ACCEPTED, None, 0, "r"
    ).to_document()
    assert not OUTCOME_SCHEMA.is_valid({**document, "reason_code": "LOT_HELD"})
    assert not OUTCOME_SCHEMA.is_valid({**document, "dispatch_id": None})
    rejected = {**document, "status": "REJECTED"}
    assert not OUTCOME_SCHEMA.is_valid(rejected)  # a rejection needs a reason code
    assert OUTCOME_SCHEMA.is_valid({**rejected, "reason_code": "LOT_HELD"})
    assert not OUTCOME_SCHEMA.is_valid({**rejected, "reason_code": "NOT_A_CODE"})


def test_the_schema_reason_codes_equal_the_code_set() -> None:
    codes = json.loads((CONTRACTS / "dispatch-outcome.v1.schema.json").read_text())
    listed = codes["properties"]["reason_code"]["anyOf"][0]["enum"]
    assert listed == [reason.value for reason in RejectReason]


@pytest.mark.parametrize(("path", "value", "code"), INTAKE_BAD)
def test_what_the_intake_decoder_refuses_the_schema_refuses(
    path: list[str | int], value: Any, code: RejectReason
) -> None:
    document = mutated(intake_document(), path, value)
    with pytest.raises(DecisionContractError):
        decode_intake(document)
    assert not INTAKE_SCHEMA.is_valid(document)


@pytest.mark.parametrize(("path", "value", "code"), REQUEST_BAD)
def test_what_the_request_decoder_refuses_the_schema_refuses(
    path: list[str | int], value: Any, code: RejectReason
) -> None:
    document = mutated(REQUEST, path, value)
    with pytest.raises(DecisionContractError):
        decode_request(document)
    assert not REQUEST_SCHEMA.is_valid(document)
