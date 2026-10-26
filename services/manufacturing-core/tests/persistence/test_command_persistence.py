from typing import cast

import psycopg
import pytest
from conftest import Database
from manufacturing_core.command_persistence import PostgresCommandLedger
from manufacturing_core.commands import OutcomeStatus, PlaceLotOnHold, UnresolvedEffect
from manufacturing_core.database import connect_runtime
from psycopg.rows import DictRow

pytestmark = pytest.mark.integration


def make_command(key: str = "key-1", reason: str = "inspection") -> PlaceLotOnHold:
    return PlaceLotOnHold.model_validate(
        {
            "idempotency_key": key,
            "world_id": "primary",
            "correlation_id": "corr-1",
            "target": {"entity_type": "Lot", "entity_id": "LOT-1"},
            "expected": {"expected_revision": "r1"},
            "hold_reason": reason,
            "material_hold_id": "hold-1",
        }
    )


def test_command_acceptance_is_durable_idempotent_and_queryable(
    database: Database,
) -> None:
    with connect_runtime(database.runtime_dsn) as connection:
        ledger = PostgresCommandLedger(cast(psycopg.Connection[DictRow], connection))
        effects: list[str] = []

        def effect() -> None:
            effects.append("once")
            connection.execute(
                "INSERT INTO core.equipment(id, revision) VALUES ('E-CMD-1', 'r1')"
            )

        original = make_command()
        first = ledger.accept(original, current_revision="r1", mutate=effect)
        retry = ledger.accept(
            original, current_revision="r1", mutate=lambda: effects.append("bad")
        )
        conflict = ledger.accept(make_command(reason="different"), current_revision="r1")

        assert first.status == OutcomeStatus.ACCEPTED
        assert first.effect_verification.value == "NOT_VERIFIED"
        assert retry == first
        assert conflict.status == OutcomeStatus.CONFLICT
        assert effects == ["once"]
        assert ledger.get_outcome(first.outcome_id) == first
        assert ledger.get_by_idempotency("key-1") == first

    with connect_runtime(database.runtime_dsn) as connection:
        restarted = PostgresCommandLedger(cast(psycopg.Connection[DictRow], connection))
        assert restarted.get_by_idempotency("key-1") == first
        assert restarted.get_outcome(first.outcome_id) == first

    with psycopg.connect(database.admin_dsn) as admin:
        row = admin.execute(
            "SELECT status, effect_verification FROM core.command_outcome WHERE outcome_id = %s",
            (str(first.outcome_id),),
        ).fetchone()
        assert row == ("ACCEPTED", "NOT_VERIFIED")


def test_stale_and_unresolved_outcomes_survive_in_postgres(
    connection: psycopg.Connection,
) -> None:
    ledger = PostgresCommandLedger(cast(psycopg.Connection[DictRow], connection))
    stale = ledger.accept(make_command("stale"), current_revision="r2")
    unresolved = ledger.accept(
        make_command("unknown"),
        current_revision="r1",
        mutate=lambda: (_ for _ in ()).throw(UnresolvedEffect("effect could not be classified")),
    )
    assert stale.status == OutcomeStatus.REJECTED
    assert stale.error_code == "STALE"
    assert unresolved.status == OutcomeStatus.UNRESOLVED
    assert ledger.get_by_idempotency("unknown") == unresolved
