"""Shared builders and the canonical replay trace for the dispatch tests."""

from __future__ import annotations

import json
from collections.abc import Iterable
from fractions import Fraction

from manufacturing_scheduler import (
    POLICIES,
    DispatchContext,
    DispatchDecision,
    DispatchJob,
    JobState,
    OfflineInstanceConfig,
    generate,
)

TICK = "tick"
REPLAY_CONFIG = OfflineInstanceConfig(job_count=40, horizon_ticks=300)
REPLAY_EPOCHS = (0, 50, 150, 300, 600)


def job(
    job_id: str,
    entry: int,
    due: int,
    operation: int,
    remaining: int,
    *,
    state: JobState = JobState.ELIGIBLE,
) -> DispatchJob:
    return DispatchJob(job_id, entry, due, operation, remaining, TICK, state)


def context(now: int, jobs: Iterable[DispatchJob]) -> DispatchContext:
    return DispatchContext(now=now, tick_unit=TICK, candidates=tuple(jobs))


def ranked_ids(decision: DispatchDecision) -> list[str]:
    return [ranked.job_id for ranked in decision.ranking]


def _encode(value: int | Fraction | str) -> str | int:
    return (
        f"{value.numerator}/{value.denominator}"
        if isinstance(value, Fraction)
        else value
    )


def canonical_replay(seed: int) -> str:
    """Instance plus every policy's ranking at fixed epochs, as canonical JSON."""
    instance = generate(REPLAY_CONFIG, seed)
    decisions = {
        f"{policy_id}@{now}": [
            [ranked.job_id, [_encode(part) for part in ranked.key]]
            for ranked in policy.select(instance.context_at(now)).ranking
        ]
        for policy_id, policy in POLICIES.items()
        for now in REPLAY_EPOCHS
    }
    jobs = [
        [
            j.job_id,
            j.queue_entry_tick,
            j.due_tick,
            j.operation_ticks,
            j.remaining_route_ticks,
        ]
        for j in instance.jobs
    ]
    return json.dumps(
        {"id": instance.instance_id, "jobs": jobs, "decisions": decisions},
        sort_keys=True,
        separators=(",", ":"),
    )
