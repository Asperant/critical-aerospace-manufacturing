"""Named, independent, seeded random streams (FR-SIM-007, ARCH-SIM-ENGINE).

Each stream is a NumPy ``Generator`` over ``PCG64`` seeded from a
``SeedSequence`` whose entropy is the master seed and whose spawn key is the
stream's fixed integer identifier. A stream therefore depends only on
``(master_seed, stream_id)``: not on lookup order, not on how many other
streams exist, not on Python hash randomisation, and not on any global state.

Replay guarantees hold for identical NumPy versions only; no cross-version
promise is made.
"""

from __future__ import annotations

from enum import StrEnum
from types import MappingProxyType

import numpy as np

from manufacturing_simulator.errors import InvalidSeedError, UnknownStreamError
from manufacturing_simulator.validation import require_int


class StreamName(StrEnum):
    """The registered stream names.

    The first six are mandated by WP-SIM-001; telemetry and transport are named
    by the architecture and reserved here without any domain model behind them.
    """

    ARRIVAL = "arrival"
    PROCESSING = "processing"
    FAILURE = "failure"
    REPAIR = "repair"
    QUALITY = "quality"
    INSPECTION = "inspection"
    TELEMETRY = "telemetry"
    TRANSPORT = "transport"


STREAM_IDS = MappingProxyType(
    {
        StreamName.ARRIVAL: 1,
        StreamName.PROCESSING: 2,
        StreamName.FAILURE: 3,
        StreamName.REPAIR: 4,
        StreamName.QUALITY: 5,
        StreamName.INSPECTION: 6,
        StreamName.TELEMETRY: 7,
        StreamName.TRANSPORT: 8,
    }
)
"""Fixed stream identifiers. Never renumber: it would change every replay."""

MAX_SEED = 2**128 - 1


def validate_seed(seed: object) -> int:
    """A master seed is a non-negative ``int`` (not ``bool``) below ``2**128``."""
    value = require_int(seed, "seed", minimum=0, error=InvalidSeedError)
    if value > MAX_SEED:
        raise InvalidSeedError(f"seed must be <= {MAX_SEED}")
    return value


class RandomnessManager:
    """Registry of the named streams derived from one immutable master seed."""

    def __init__(self, master_seed: int) -> None:
        self._master_seed = validate_seed(master_seed)
        self._streams: dict[StreamName, np.random.Generator] = {}

    @property
    def master_seed(self) -> int:
        return self._master_seed

    @property
    def stream_ids(self) -> MappingProxyType[StreamName, int]:
        return STREAM_IDS

    def stream(self, name: StreamName | str) -> np.random.Generator:
        """Return the stream ``name``; repeated lookups continue the same stream."""
        key = self._resolve(name)
        generator = self._streams.get(key)
        if generator is None:
            sequence = np.random.SeedSequence(
                entropy=self._master_seed, spawn_key=(STREAM_IDS[key],)
            )
            generator = np.random.Generator(np.random.PCG64(sequence))
            self._streams[key] = generator
        return generator

    @staticmethod
    def _resolve(name: StreamName | str) -> StreamName:
        try:
            return StreamName(name)
        except ValueError:
            raise UnknownStreamError(f"unknown random stream: {name!r}") from None
