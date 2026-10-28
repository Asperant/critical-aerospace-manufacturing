"""Simulated lot state conforms to Core's published lot-semantics contract (read only).

Only what the Simulator really produces is checked: the lot block (lifecycle and
execution vocabulary, opaque revision, order id). Holds, visits and executions are not
mapped to Core records here; that is DEP-039 integration work.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from ops_fixtures import config, run

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = json.loads(
    (
        ROOT
        / "services/manufacturing-core/contracts/v1/lot-operational-semantics.v1.schema.json"
    ).read_text(encoding="utf-8")
)
VALIDATOR = Draft202012Validator(SCHEMA)


def view(
    lot_id: str, order_id: str, revision: str, lifecycle: str, execution: str
) -> dict[str, object]:
    return {
        "contract_version": "core.lot-operational-semantics.v1",
        "lot": {
            "id": lot_id,
            "revision": revision,
            "order_id": order_id,
            "lifecycle_state": lifecycle,
            "execution_state": execution,
        },
        "holds": [],
        "component_histories": [],
    }


def test_the_lot_state_at_every_moment_validates_against_cores_schema() -> None:
    seen: set[tuple[str, str]] = set()
    for until in (0, 1, 5, 12, 30, 60, 90, 400):
        _, facility, _ = run(config(lots=3), until=until)
        for r in facility.lot_reports():
            document = view(
                r.lot_id, r.order_id, r.revision, r.lifecycle, r.execution_state
            )
            assert VALIDATOR.is_valid(document), (until, r)
            seen.add((r.lifecycle, r.execution_state))
    assert ("IN_PRODUCTION", "PROCESSING") in seen and (
        "COMPLETED",
        "STEP_COMPLETED",
    ) in seen
    assert ("IN_PRODUCTION", "QUEUED") in seen


def test_a_revision_changes_when_the_lot_changes_and_is_opaque_text() -> None:
    _, early, _ = run(config(lots=1), until=1)
    _, late, _ = run(config(lots=1), until=400)
    assert early.lot_reports()[0].revision != late.lot_reports()[0].revision
    assert isinstance(late.lot_reports()[0].revision, str)
