"""The five mandatory dispatch rules (FR-SCH-010; SCH-B1..SCH-B5).

Every rule ranks the released, eligible candidates of one ``DispatchContext`` by a
primary key and breaks ties by queue-entry tick, then job ID, so the result never
depends on the order of the input. Keys are exact integers or ``Fraction`` values;
no float is involved. A rule only selects: it executes nothing, keeps no state and
reads no clock.
"""

from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction
from types import MappingProxyType
from typing import Protocol

from manufacturing_scheduler.errors import UnsupportedPolicyError
from manufacturing_scheduler.models import (
    DecisionStatus,
    DispatchContext,
    DispatchDecision,
    DispatchJob,
    RankedJob,
    RankingKey,
)


class DispatchPolicy(Protocol):
    """Common decision interface of every baseline rule."""

    @property
    def policy_id(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def select(self, context: DispatchContext) -> DispatchDecision: ...


class _RankingPolicy:
    policy_id: str
    name: str
    version: str = "1.0.0"

    def primary_key(self, job: DispatchJob, now: int) -> int | Fraction:
        raise NotImplementedError

    def select(self, context: DispatchContext) -> DispatchDecision:
        ranked = sorted(
            (
                RankedJob(
                    job.job_id,
                    (
                        self.primary_key(job, context.now),
                        job.queue_entry_tick,
                        job.job_id,
                    ),
                )
                for job in context.candidates
                if job.is_dispatchable(context.now)
            ),
            key=_key_of,
        )
        return DispatchDecision(
            status=DecisionStatus.SELECTED if ranked else DecisionStatus.NO_CANDIDATES,
            policy_id=self.policy_id,
            policy_name=self.name,
            policy_version=self.version,
            decision_tick=context.now,
            selected_job_id=ranked[0].job_id if ranked else None,
            ranking=tuple(ranked),
        )


def _key_of(ranked: RankedJob) -> RankingKey:
    return ranked.key


class FifoPolicy(_RankingPolicy):
    """SCH-B1: earliest queue-entry tick first."""

    policy_id = "SCH-B1"
    name = "FIFO"

    def primary_key(self, job: DispatchJob, now: int) -> int:
        return job.queue_entry_tick


class EddPolicy(_RankingPolicy):
    """SCH-B2: earliest due tick first. Overdue jobs have the earliest due ticks."""

    policy_id = "SCH-B2"
    name = "EDD"

    def primary_key(self, job: DispatchJob, now: int) -> int:
        return job.due_tick


class CriticalRatioPolicy(_RankingPolicy):
    """SCH-B3: smallest ``(due_tick - now) / remaining_route_ticks`` first.

    The ratio is an exact ``Fraction``. ``remaining_route_ticks`` of a dispatchable
    job is at least 1, so there is no division by zero. A negative ratio means the
    job is already overdue and is kept, so the most overdue work ranks first.
    """

    policy_id = "SCH-B3"
    name = "CR"

    def primary_key(self, job: DispatchJob, now: int) -> Fraction:
        return Fraction(job.due_tick - now, job.remaining_route_ticks)


class SptPolicy(_RankingPolicy):
    """SCH-B4: shortest processing time of the *next operation* first."""

    policy_id = "SCH-B4"
    name = "SPT"

    def primary_key(self, job: DispatchJob, now: int) -> int:
        return job.operation_ticks


class SrptPolicy(_RankingPolicy):
    """SCH-B5: shortest processing time of the *whole remaining route* first.

    A ranking at the supplied decision epoch only. Nothing is preempted: a
    running operation is outside this rule's input.
    """

    policy_id = "SCH-B5"
    name = "SRPT"

    def primary_key(self, job: DispatchJob, now: int) -> int:
        return job.remaining_route_ticks


POLICIES: Mapping[str, DispatchPolicy] = MappingProxyType(
    {
        policy.policy_id: policy
        for policy in (
            FifoPolicy(),
            EddPolicy(),
            CriticalRatioPolicy(),
            SptPolicy(),
            SrptPolicy(),
        )
    }
)


def get_policy(policy_id: object) -> DispatchPolicy:
    """The registered rule for ``policy_id`` (``SCH-B1``..``SCH-B5``)."""
    if not isinstance(policy_id, str) or policy_id not in POLICIES:
        raise UnsupportedPolicyError(
            f"unsupported policy {policy_id!r}; supported: {sorted(POLICIES)}"
        )
    return POLICIES[policy_id]
