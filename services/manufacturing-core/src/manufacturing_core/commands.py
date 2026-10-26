"""Core typed operational commands and transport-independent acceptance.

This module deliberately separates command acceptance from effect verification:
``ACCEPTED`` means that Core durably accepted the request, never that a physical
or downstream effect was verified.  The command ledger is distinct from the
event-consumer processed-message ledger.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from threading import RLock
from typing import Annotated, Literal, Protocol, Self
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    model_validator,
)

Identity = Annotated[str, StringConstraints(strict=True, pattern=r"^\S+$")]
Detail = Annotated[str, StringConstraints(strict=True, min_length=1)]


class CommandType(StrEnum):
    PLACE_LOT_ON_HOLD = "PlaceLotOnHold"
    RELEASE_MATERIAL_HOLD = "ReleaseMaterialHold"
    DISPATCH_LOT = "DispatchLot"
    CREATE_MAINTENANCE_WORK_ORDER = "CreateMaintenanceWorkOrder"


class OutcomeStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    UNRESOLVED = "UNRESOLVED"
    CONFLICT = "CONFLICT"


class EffectVerificationStatus(StrEnum):
    NOT_VERIFIED = "NOT_VERIFIED"


class CommandTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_type: Identity
    entity_id: Identity


class FreshnessPrecondition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expected_revision: Identity | None = None
    observed_at: datetime | None = None
    max_age_seconds: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def has_constraint(self) -> Self:
        if self.expected_revision is None and self.observed_at is None:
            raise ValueError("expected revision or freshness timestamp is required")
        if self.max_age_seconds is not None and self.observed_at is None:
            raise ValueError("max_age_seconds requires observed_at")
        return self


class TypedOperationalCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    command_type: CommandType
    command_version: Literal[1] = 1
    command_id: UUID = Field(default_factory=uuid4)
    idempotency_key: Identity
    world_id: Identity
    correlation_id: Identity
    causation_id: Identity | None = None
    target: CommandTarget
    expected: FreshnessPrecondition

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class PlaceLotOnHold(TypedOperationalCommand):
    command_type: Literal[CommandType.PLACE_LOT_ON_HOLD] = CommandType.PLACE_LOT_ON_HOLD  # type: ignore[reportIncompatibleVariableOverride]
    target: CommandTarget = Field(
        ..., description="The lot whose canonical manufacturing state is held"
    )
    hold_reason: Detail
    material_hold_id: Identity


class ReleaseMaterialHold(TypedOperationalCommand):
    command_type: Literal[CommandType.RELEASE_MATERIAL_HOLD] = (  # type: ignore[reportIncompatibleVariableOverride]
        CommandType.RELEASE_MATERIAL_HOLD
    )
    hold_id: Identity
    release_reason: Detail


class DispatchLot(TypedOperationalCommand):
    command_type: Literal[CommandType.DISPATCH_LOT] = CommandType.DISPATCH_LOT  # type: ignore[reportIncompatibleVariableOverride]
    operation_id: Identity
    resource_id: Identity


class CreateMaintenanceWorkOrder(TypedOperationalCommand):
    command_type: Literal[CommandType.CREATE_MAINTENANCE_WORK_ORDER] = (  # type: ignore[reportIncompatibleVariableOverride]
        CommandType.CREATE_MAINTENANCE_WORK_ORDER
    )
    maintenance_reason: Detail
    requested_by: Identity


OperationalCommandV1 = Annotated[
    PlaceLotOnHold | ReleaseMaterialHold | DispatchLot | CreateMaintenanceWorkOrder,
    Field(discriminator="command_type"),
]


class CommandOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outcome_id: UUID
    command_id: UUID
    idempotency_key: Identity
    command_type: CommandType
    command_version: Literal[1]
    world_id: Identity
    correlation_id: Identity
    status: OutcomeStatus
    effect_verification: EffectVerificationStatus = (
        EffectVerificationStatus.NOT_VERIFIED
    )
    error_code: Identity | None = None
    detail: Detail | None = None


class CommandRejected(Exception):
    """A deterministic domain/precondition rejection to persist as REJECTED."""

    def __init__(self, code: str, detail: str) -> None:
        self.code, self.detail = code, detail
        super().__init__(code)


class UnresolvedEffect(Exception):
    """The effect cannot be safely classified and must remain inspectable."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class RevisionSource(Protocol):
    def __call__(self, target: CommandTarget) -> str | None: ...


def validate_preconditions(
    command: TypedOperationalCommand,
    *,
    current_revision: str | None,
    now: datetime | None = None,
) -> None:
    """Fail closed for absent, stale or conflicting opaque revisions/freshness."""
    expected = command.expected
    if expected.expected_revision is not None:
        if current_revision is None:
            raise CommandRejected("UNRESOLVED", "current revision unavailable")
        if current_revision != expected.expected_revision:
            raise CommandRejected("STALE", "expected revision is not current")
    if expected.observed_at is not None and expected.max_age_seconds is not None:
        if now is None:
            raise CommandRejected("UNRESOLVED", "freshness clock unavailable")
        observed = expected.observed_at
        age = (now - observed).total_seconds()
        if age < 0 or age > expected.max_age_seconds:
            raise CommandRejected("STALE", "freshness window expired")


def validate_command_context(
    command: TypedOperationalCommand, *, expected_world_id: str | None = None
) -> None:
    """Require the caller's explicit world scope; no primary-world fallback."""
    if expected_world_id is not None and command.world_id != expected_world_id:
        raise CommandRejected(
            "WORLD_MISMATCH", "command world is outside the caller scope"
        )


def reconciliation_action(outcome: CommandOutcome) -> str:
    """Return the safe operator action without changing canonical state."""
    if outcome.status is OutcomeStatus.UNRESOLVED:
        return "LOOKUP_CANONICAL_EFFECT_BEFORE_RETRY"
    if outcome.status is OutcomeStatus.ACCEPTED:
        return "VERIFY_CANONICAL_EFFECT"
    if outcome.status is OutcomeStatus.REJECTED:
        return "CORRECT_PRECONDITION_OR_POLICY"
    return "DO_NOT_RETRY_WITH_SAME_IDEMPOTENCY_KEY"


class CommandLedger(Protocol):
    def accept(
        self,
        command: TypedOperationalCommand,
        *,
        current_revision: str | None,
        mutate: Callable[[], None] | None = None,
        now: datetime | None = None,
        expected_world_id: str | None = None,
    ) -> CommandOutcome: ...

    def get_outcome(self, outcome_id: UUID) -> CommandOutcome | None: ...

    def get_by_idempotency(self, key: str) -> CommandOutcome | None: ...


class InMemoryCommandLedger:
    """Deterministic test-double with the same immutable-key semantics as SQL."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._entries: dict[str, tuple[str, CommandOutcome]] = {}
        self.effect_count = 0

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
        with self._lock:
            existing = self._entries.get(command.idempotency_key)
            if existing is not None:
                prior_fingerprint, prior = existing
                if prior_fingerprint != fingerprint:
                    return self._conflict(
                        command, "idempotency key already binds another command"
                    )
                return prior
            try:
                validate_command_context(command, expected_world_id=expected_world_id)
                validate_preconditions(
                    command, current_revision=current_revision, now=now
                )
                if mutate is not None:
                    mutate()
                    self.effect_count += 1
                outcome = self._outcome(command, OutcomeStatus.ACCEPTED)
            except CommandRejected as error:
                outcome = self._outcome(
                    command, OutcomeStatus.REJECTED, error.code, error.detail
                )
            except UnresolvedEffect as error:
                outcome = self._outcome(
                    command, OutcomeStatus.UNRESOLVED, "UNRESOLVED", error.detail
                )
            self._entries[command.idempotency_key] = (fingerprint, outcome)
            return outcome

    def get_outcome(self, outcome_id: UUID) -> CommandOutcome | None:
        with self._lock:
            return next(
                (v[1] for v in self._entries.values() if v[1].outcome_id == outcome_id),
                None,
            )

    def get_by_idempotency(self, key: str) -> CommandOutcome | None:
        with self._lock:
            entry = self._entries.get(key)
            return None if entry is None else entry[1]

    @staticmethod
    def _outcome(
        command: TypedOperationalCommand,
        status: OutcomeStatus,
        error_code: str | None = None,
        detail: str | None = None,
    ) -> CommandOutcome:
        return CommandOutcome(
            outcome_id=uuid4(),
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

    @classmethod
    def _conflict(cls, command: TypedOperationalCommand, detail: str) -> CommandOutcome:
        return cls._outcome(command, OutcomeStatus.CONFLICT, "CONFLICT", detail)


def command_schema() -> dict[str, object]:
    """Published JSON Schema source for the registry contract."""
    return TypeAdapter(OperationalCommandV1).json_schema()  # type: ignore[reportArgumentType]
