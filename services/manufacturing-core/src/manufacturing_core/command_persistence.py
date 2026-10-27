"""PostgreSQL command ledger and durable outcome persistence.

The caller supplies the Core runtime connection and transaction boundary.  The
tables are append-only: runtime privileges need only SELECT/INSERT.  A command
reservation and its outcome are created in one transaction with the domain
mutation callback, so a failed mutation cannot leave a reusable reservation.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import DictRow

from manufacturing_core.commands import (
    CommandOutcome,
    CommandRejected,
    EffectVerificationStatus,
    OutcomeStatus,
    TypedOperationalCommand,
    UnresolvedEffect,
    validate_command_context,
    validate_preconditions,
)
from manufacturing_core.observability import record


class PostgresCommandLedger:
    """Core command ledger; never uses the event-consumer processed-message table."""

    def __init__(self, connection: psycopg.Connection[DictRow]) -> None:
        self.connection = connection

    def accept(
        self,
        command: TypedOperationalCommand,
        *,
        current_revision: str | None,
        mutate: Callable[[], None] | None = None,
        now: datetime | None = None,
        expected_world_id: str | None = None,
    ) -> CommandOutcome:
        fingerprint = command.fingerprint()
        started = perf_counter()
        with self.connection.transaction():
            inserted = self.connection.execute(
                "INSERT INTO core.command_idempotency "
                "(idempotency_key, command_id, command_type, command_version, "
                "command_fingerprint, target_type, target_id, world_id, "
                "correlation_id, causation_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (idempotency_key) DO NOTHING RETURNING idempotency_key",
                (
                    command.idempotency_key,
                    str(command.command_id),
                    command.command_type.value,
                    command.command_version,
                    fingerprint,
                    command.target.entity_type,
                    command.target.entity_id,
                    command.world_id,
                    command.correlation_id,
                    command.causation_id,
                ),
            ).fetchone()
            if inserted is None:
                prior = self._by_key(command.idempotency_key)
                if prior is None:
                    raise RuntimeError("idempotency reservation has no durable outcome")
                if self._fingerprint(command.idempotency_key) != fingerprint:
                    return self._conflict(command)
                return prior

            try:
                validate_command_context(command, expected_world_id=expected_world_id)
                validate_preconditions(
                    command, current_revision=current_revision, now=now
                )
                if mutate is not None:
                    mutate()
                outcome = self._persist_outcome(command, OutcomeStatus.ACCEPTED)
            except CommandRejected as error:
                outcome = self._persist_outcome(
                    command, OutcomeStatus.REJECTED, error.code, error.detail
                )
            except UnresolvedEffect as error:
                outcome = self._persist_outcome(
                    command, OutcomeStatus.UNRESOLVED, "UNRESOLVED", error.detail
                )
            record(
                command.correlation_id,
                f"command.{command.command_type.value}",
                outcome.status.value,
                (perf_counter() - started) * 1000,
            )
            return outcome

    def get_outcome(self, outcome_id: UUID) -> CommandOutcome | None:
        row = self.connection.execute(
            "SELECT outcome_id, command_id, idempotency_key, command_type, "
            "command_version, world_id, correlation_id, status, "
            "effect_verification, error_code, detail "
            "FROM core.command_outcome WHERE outcome_id = %s",
            (str(outcome_id),),
        ).fetchone()
        return None if row is None else self._model(row)

    def get_by_idempotency(self, key: str) -> CommandOutcome | None:
        return self._by_key(key)

    def _by_key(self, key: str) -> CommandOutcome | None:
        row = self.connection.execute(
            "SELECT outcome_id, command_id, idempotency_key, command_type, "
            "command_version, world_id, correlation_id, status, "
            "effect_verification, error_code, detail "
            "FROM core.command_outcome WHERE idempotency_key = %s",
            (key,),
        ).fetchone()
        return None if row is None else self._model(row)

    def _fingerprint(self, key: str) -> str:
        row = self.connection.execute(
            "SELECT command_fingerprint FROM core.command_idempotency "
            "WHERE idempotency_key = %s",
            (key,),
        ).fetchone()
        if row is None:
            raise RuntimeError("idempotency reservation disappeared")
        return row["command_fingerprint"]

    def _persist_outcome(
        self,
        command: TypedOperationalCommand,
        status: OutcomeStatus,
        error_code: str | None = None,
        detail: str | None = None,
    ) -> CommandOutcome:
        outcome_id = uuid4()
        self.connection.execute(
            "INSERT INTO core.command_outcome "
            "(outcome_id, command_id, idempotency_key, command_type, command_version, "
            "world_id, correlation_id, status, effect_verification, error_code, detail) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                str(outcome_id),
                str(command.command_id),
                command.idempotency_key,
                command.command_type.value,
                command.command_version,
                command.world_id,
                command.correlation_id,
                status.value,
                EffectVerificationStatus.NOT_VERIFIED.value,
                error_code,
                detail,
            ),
        )
        return CommandOutcome(
            outcome_id=outcome_id,
            command_id=command.command_id,
            idempotency_key=command.idempotency_key,
            command_type=command.command_type,
            command_version=command.command_version,
            world_id=command.world_id,
            correlation_id=command.correlation_id,
            status=status,
            error_code=error_code,
            detail=detail,
        )

    @staticmethod
    def _model(row: dict[str, Any]) -> CommandOutcome:
        def uuid_value(value: Any) -> UUID:
            return value if isinstance(value, UUID) else UUID(value)

        return CommandOutcome.model_validate(
            {
                **row,
                "outcome_id": uuid_value(row["outcome_id"]),
                "command_id": uuid_value(row["command_id"]),
            }
        )

    @staticmethod
    def _conflict(command: TypedOperationalCommand) -> CommandOutcome:
        return CommandOutcome(
            outcome_id=uuid4(),
            command_id=command.command_id,
            idempotency_key=command.idempotency_key,
            command_type=command.command_type,
            command_version=command.command_version,
            world_id=command.world_id,
            correlation_id=command.correlation_id,
            status=OutcomeStatus.CONFLICT,
            effect_verification=EffectVerificationStatus.NOT_VERIFIED,
            error_code="CONFLICT",
            detail="idempotency key already binds another command",
        )
