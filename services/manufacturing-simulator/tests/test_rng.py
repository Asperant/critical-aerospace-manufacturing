"""TEST-SIM-DETERMINISM (FR-SIM-007): named, seeded, independent random streams."""

from __future__ import annotations

import random
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from manufacturing_simulator import (
    MAX_SEED,
    STREAM_IDS,
    InvalidSeedError,
    RandomnessManager,
    StreamName,
    UnknownStreamError,
)

REQUIRED = ("arrival", "processing", "failure", "repair", "quality", "inspection")

# Recorded from NumPy 2.4.6 (PCG64 + SeedSequence) when this suite was written. They
# were not derived independently: they pin the stream-id mapping and the pinned NumPy
# behaviour, so drift in either shows up as a failure here. Replay guarantees are
# stated for this NumPy version only.
KNOWN_DRAWS_SEED_12345 = {
    "arrival": [3306082668, 1619526548, 398670237],
    "processing": [1078825733, 607047513, 775930576],
    "failure": [3954220855, 1683448464, 2444903473],
    "repair": [967369246, 3517235412, 842153206],
    "quality": [747051247, 721536971, 910111105],
    "inspection": [2466913474, 1088543876, 174422320],
    "telemetry": [649070245, 4222061228, 3416324402],
    "transport": [1821229264, 917626043, 230545241],
}

seeds = st.integers(min_value=0, max_value=MAX_SEED)


def draws(manager: RandomnessManager, name: str, count: int = 5) -> list[int]:
    return manager.stream(name).integers(0, 2**32, size=count).tolist()


def test_required_and_architecture_streams_are_registered() -> None:
    names = {name.value for name in StreamName}
    assert set(REQUIRED) <= names
    assert {"telemetry", "transport"} <= names


def test_stream_ids_are_fixed_and_unique() -> None:
    assert {name.value: ident for name, ident in STREAM_IDS.items()} == {
        "arrival": 1,
        "processing": 2,
        "failure": 3,
        "repair": 4,
        "quality": 5,
        "inspection": 6,
        "telemetry": 7,
        "transport": 8,
    }
    assert len(set(STREAM_IDS.values())) == len(STREAM_IDS)
    assert set(STREAM_IDS) == set(StreamName)


@pytest.mark.parametrize("name", sorted(KNOWN_DRAWS_SEED_12345))
def test_known_draws_for_fixed_seed(name: str) -> None:
    manager = RandomnessManager(12345)
    assert draws(manager, name, 3) == KNOWN_DRAWS_SEED_12345[name]


def test_generators_are_pcg64_backed() -> None:
    generator = RandomnessManager(1).stream(StreamName.ARRIVAL)
    assert isinstance(generator, np.random.Generator)
    assert isinstance(generator.bit_generator, np.random.PCG64)


@given(seeds)
def test_same_seed_gives_same_draws_in_every_stream(seed: int) -> None:
    first, second = RandomnessManager(seed), RandomnessManager(seed)
    for name in StreamName:
        assert draws(first, name) == draws(second, name)


def test_different_seeds_give_different_draw_fixtures() -> None:
    # Specified fixtures only: a claim about these seeds, not about every scenario.
    for name in StreamName:
        assert draws(RandomnessManager(12345), name) != draws(
            RandomnessManager(54321), name
        )


def test_streams_differ_from_each_other_for_one_seed() -> None:
    manager = RandomnessManager(7)
    first_draws = {name: tuple(draws(manager, name)) for name in StreamName}
    assert len(set(first_draws.values())) == len(StreamName)


@given(seeds, st.permutations(list(StreamName)))
def test_lookup_order_does_not_change_any_stream(
    seed: int, order: list[StreamName]
) -> None:
    reference = RandomnessManager(seed)
    expected = {name: draws(reference, name) for name in StreamName}
    shuffled = RandomnessManager(seed)
    assert {name: draws(shuffled, name) for name in order} == expected


@given(seeds, st.integers(min_value=1, max_value=200))
def test_sampling_one_stream_never_perturbs_another(seed: int, extra: int) -> None:
    quiet, noisy = RandomnessManager(seed), RandomnessManager(seed)
    noisy.stream("quality").random(extra)
    noisy.stream("arrival").normal(size=extra)
    for name in ("failure", "repair", "processing", "inspection"):
        assert draws(noisy, name) == draws(quiet, name)


def test_repeated_lookup_continues_the_same_stream() -> None:
    manager = RandomnessManager(99)
    assert manager.stream("arrival") is manager.stream(StreamName.ARRIVAL)
    split = draws(manager, "arrival", 3) + draws(manager, "arrival", 3)
    assert split == draws(RandomnessManager(99), "arrival", 6)


def test_global_random_state_has_no_influence() -> None:
    expected = draws(RandomnessManager(5), "arrival")
    np.random.seed(0)
    random.seed(0)
    np.random.random(10)
    assert draws(RandomnessManager(5), "arrival") == expected
    np.random.seed(123456)
    random.seed(123456)
    assert draws(RandomnessManager(5), "arrival") == expected


def test_managers_share_no_state() -> None:
    first, second = RandomnessManager(3), RandomnessManager(3)
    assert first.stream("arrival") is not second.stream("arrival")
    first.stream("arrival").random(50)
    assert draws(second, "arrival") == draws(RandomnessManager(3), "arrival")


@pytest.mark.parametrize("bad", ["bogus", "", "Arrival", "ARRIVAL ", 5, None, ("a",)])
def test_unknown_streams_fail_explicitly(bad: Any) -> None:
    with pytest.raises(UnknownStreamError):
        RandomnessManager(1).stream(bad)


@pytest.mark.parametrize(
    "bad", [-1, True, False, 1.5, "1", None, MAX_SEED + 1, 2**200, b"1"]
)
def test_invalid_seeds_are_rejected(bad: Any) -> None:
    with pytest.raises(InvalidSeedError):
        RandomnessManager(bad)


@pytest.mark.parametrize("seed", [0, 1, MAX_SEED])
def test_seed_boundaries_are_accepted(seed: int) -> None:
    manager = RandomnessManager(seed)
    assert manager.master_seed == seed
    assert len(draws(manager, "arrival")) == 5


def test_master_seed_is_immutable() -> None:
    manager = RandomnessManager(4)
    with pytest.raises(AttributeError):
        manager.master_seed = 5  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(TypeError):
        STREAM_IDS[StreamName.ARRIVAL] = 9  # pyright: ignore[reportIndexIssue]
