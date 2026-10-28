"""Offline synthetic scheduling instances for development tests.

``generate(config, seed)`` draws from its own seeded ``PCG64`` stream (the same
generator family and ``SeedSequence`` derivation the simulator kernel uses, with
its own stream ID). No global state, hash seed or clock is involved. Replay
guarantees hold for the pinned NumPy version only.

The jobs are synthetic fixtures. They are not real factory data, not a canonical
ScenarioDefinition and not final research evidence.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

import numpy as np

from manufacturing_scheduler.errors import (
    InvalidInstanceConfigError,
    InvalidSeedError,
)
from manufacturing_scheduler.models import DispatchContext, DispatchJob
from manufacturing_scheduler.validation import require_int, require_text

GENERATOR_VERSION = "1.0.0"
STREAM_NAME = "instance-generator"
STREAM_ID = 1
MAX_SEED = 2**63 - 1
MAX_JOBS = 500
MAX_HORIZON_TICKS = 100_000
MAX_PROCESSING_TICKS = 10_000
PROVENANCE = "SYNTHETIC_OFFLINE_FIXTURE: not real factory data"


@dataclass(frozen=True, slots=True)
class OfflineInstanceConfig:
    """Bounds of one synthetic instance; every drawn value is uniform in range."""

    job_count: int
    horizon_ticks: int
    min_operation_ticks: int = 1
    max_operation_ticks: int = 20
    max_extra_route_ticks: int = 40
    min_due_offset_ticks: int = 0
    max_due_offset_ticks: int = 200
    tick_unit: str = "tick"

    def __post_init__(self) -> None:
        error = InvalidInstanceConfigError
        require_int(
            self.job_count, "job_count", minimum=1, maximum=MAX_JOBS, error=error
        )
        require_int(
            self.horizon_ticks,
            "horizon_ticks",
            minimum=0,
            maximum=MAX_HORIZON_TICKS,
            error=error,
        )
        require_int(
            self.min_operation_ticks,
            "min_operation_ticks",
            minimum=1,
            maximum=MAX_PROCESSING_TICKS,
            error=error,
        )
        require_int(
            self.max_operation_ticks,
            "max_operation_ticks",
            minimum=self.min_operation_ticks,
            maximum=MAX_PROCESSING_TICKS,
            error=error,
        )
        require_int(
            self.max_extra_route_ticks,
            "max_extra_route_ticks",
            minimum=0,
            maximum=MAX_PROCESSING_TICKS,
            error=error,
        )
        require_int(
            self.min_due_offset_ticks,
            "min_due_offset_ticks",
            minimum=0,
            maximum=MAX_HORIZON_TICKS,
            error=error,
        )
        require_int(
            self.max_due_offset_ticks,
            "max_due_offset_ticks",
            minimum=self.min_due_offset_ticks,
            maximum=MAX_HORIZON_TICKS,
            error=error,
        )
        require_text(self.tick_unit, "tick_unit", error=error)


@dataclass(frozen=True, slots=True)
class InstanceMetadata:
    """What a replay needs: the exact inputs and the random-number recipe."""

    provenance: str
    generator_version: str
    rng_algorithm: str
    stream_name: str
    seed_derivation: str
    seed: int
    config: OfflineInstanceConfig
    config_sha256: str


@dataclass(frozen=True, slots=True)
class SchedulingInstance:
    instance_id: str
    jobs: tuple[DispatchJob, ...]
    tick_unit: str
    metadata: InstanceMetadata

    def context_at(self, now: int) -> DispatchContext:
        """The same immutable job set seen at decision epoch ``now``."""
        return DispatchContext(now=now, tick_unit=self.tick_unit, candidates=self.jobs)


def generate(config: OfflineInstanceConfig, seed: int) -> SchedulingInstance:
    """Build the instance determined by ``config`` and ``seed`` alone."""
    if not isinstance(config, OfflineInstanceConfig):
        raise InvalidInstanceConfigError(
            f"config must be an OfflineInstanceConfig, got {type(config).__name__}"
        )
    require_int(seed, "seed", minimum=0, maximum=MAX_SEED, error=InvalidSeedError)
    rng = np.random.Generator(
        np.random.PCG64(np.random.SeedSequence(seed, spawn_key=(STREAM_ID,)))
    )
    n = config.job_count

    def draw(low: int, high: int) -> list[int]:
        return [int(v) for v in rng.integers(low, high + 1, size=n)]

    entries = draw(0, config.horizon_ticks)
    operations = draw(config.min_operation_ticks, config.max_operation_ticks)
    extras = draw(0, config.max_extra_route_ticks)
    due_offsets = draw(config.min_due_offset_ticks, config.max_due_offset_ticks)
    jobs = tuple(
        DispatchJob(
            job_id=f"J{index:04d}",
            queue_entry_tick=entries[index],
            due_tick=entries[index] + due_offsets[index],
            operation_ticks=operations[index],
            remaining_route_ticks=operations[index] + extras[index],
            tick_unit=config.tick_unit,
        )
        for index in range(n)
    )
    digest = hashlib.sha256(
        json.dumps(asdict(config), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return SchedulingInstance(
        instance_id=f"SYN-{GENERATOR_VERSION}-{seed}-{digest[:12]}",
        jobs=jobs,
        tick_unit=config.tick_unit,
        metadata=InstanceMetadata(
            provenance=PROVENANCE,
            generator_version=GENERATOR_VERSION,
            rng_algorithm="numpy.random.PCG64",
            stream_name=STREAM_NAME,
            seed_derivation=f"SeedSequence(seed, spawn_key=({STREAM_ID},))",
            seed=seed,
            config=config,
            config_sha256=digest,
        ),
    )
