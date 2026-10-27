"""Replay results are validated independently of their digests (review R1), and
behaviour differences never compare as MATCH.

The corruption cases are results no real replay could produce, built in memory and as
JSON with recomputed digests, so only structure can reject them. The behaviour cases
are real alternative executions (several differ only in type).
"""

from __future__ import annotations

import dataclasses
import subprocess
import sys
import textwrap
import time

import pytest
from manufacturing_simulator import (
    CanonicalizationError,
    ComparisonOutcome,
    ReplayResult,
    compare,
    replay,
)
from replay_fixtures import (
    SRC_DIR,
    TESTS_DIR,
    fresh_handlers_with,
    make_spec,
    variant_handlers,
)
from replay_matrices import (
    BEHAVIOR_EXPECTED,
    baseline,
    behavior_outcomes,
    json_corruptions,
    object_corruptions,
    rejected,
)

OBJECT_CASES = object_corruptions()
JSON_CASES = json_corruptions()


@pytest.mark.parametrize("name", sorted(OBJECT_CASES))
def test_an_impossible_result_cannot_be_constructed(name: str) -> None:
    with pytest.raises(CanonicalizationError):
        OBJECT_CASES[name]()


@pytest.mark.parametrize("name", sorted(JSON_CASES))
def test_impossible_json_is_rejected_even_with_recomputed_digests(name: str) -> None:
    with pytest.raises(CanonicalizationError):
        ReplayResult.from_json(JSON_CASES[name])


def test_the_reviewed_reproductions_are_rejected() -> None:
    assert rejected(OBJECT_CASES["unsupported format"])  # was MATCH against itself
    assert rejected(OBJECT_CASES["negative clock"])  # now=-1, next_sequence=-1
    assert rejected(lambda: ReplayResult.from_json(JSON_CASES["reversed events"]))


def test_compare_revalidates_a_result_that_bypassed_construction() -> None:
    good = baseline()
    forged = dataclasses.replace(good)
    object.__setattr__(forged, "format_version", "unsupported")
    with pytest.raises(CanonicalizationError):
        compare(forged, forged)
    clock = dataclasses.replace(good)
    object.__setattr__(
        clock, "final_state", dataclasses.replace(good.final_state, now=-1)
    )
    with pytest.raises(CanonicalizationError):
        compare(good, clock)


def test_the_corruption_matrix_has_zero_accepted_cases() -> None:
    accepted = [n for n, build in OBJECT_CASES.items() if not rejected(build)]
    accepted += [
        n
        for n, text in JSON_CASES.items()
        if not rejected(lambda text=text: ReplayResult.from_json(text))
    ]
    assert accepted == []
    assert len(OBJECT_CASES) == 33 and len(JSON_CASES) == 17


def test_behaviour_differences_are_typed_mismatches_and_never_match() -> None:
    outcomes = behavior_outcomes()
    assert outcomes == {n: expected for n, (_, expected) in BEHAVIOR_EXPECTED.items()}
    assert ComparisonOutcome.MATCH not in outcomes.values()
    # The equal pair is counted separately: the baseline matches its own replay.
    again = replay(make_spec(), variant_handlers)
    assert compare(baseline(), again).outcome is ComparisonOutcome.MATCH


def test_type_only_differences_are_equal_to_python_but_not_to_compare() -> None:
    base = baseline()
    other = replay(make_spec(), lambda: variant_handlers(marker=1.0))
    # Python's == calls 1 and 1.0 equal, so the two final states are "equal" to it...
    assert base.final_state.local_state == other.final_state.local_state
    assert base.final_state.pending == other.final_state.pending
    # ...but the tagged comparison, and the digests, tell them apart.
    assert compare(base, other).outcome is ComparisonOutcome.STATE_MISMATCH
    assert base.state_digest != other.state_digest


def test_a_huge_counter_is_rejected_promptly_without_allocating_for_it() -> None:
    good = baseline()
    started = time.perf_counter()
    with pytest.raises(CanonicalizationError):
        dataclasses.replace(
            good,
            final_state=dataclasses.replace(good.final_state, next_sequence=10**30),
        )
    with pytest.raises(CanonicalizationError):
        ReplayResult.from_json(JSON_CASES["next sequence astronomically large"])
    assert time.perf_counter() - started < 2.0


MEMORY_CAPPED = """
import dataclasses, resource
from manufacturing_simulator import CanonicalizationError, ReplayResult
from replay_matrices import baseline, json_corruptions

good = baseline()
text = json_corruptions()["next sequence astronomically large"]
used = int(open("/proc/self/statm").read().split()[0]) * resource.getpagesize()
hard = resource.getrlimit(resource.RLIMIT_AS)[1]
resource.setrlimit(resource.RLIMIT_AS, (used + 64 * 2**20, hard))
for build in (
    lambda: dataclasses.replace(
        good, final_state=dataclasses.replace(good.final_state, next_sequence=10**30)
    ),
    lambda: ReplayResult.from_json(text),
):
    try:
        build()
    except CanonicalizationError:
        continue
    raise SystemExit("accepted")
print("rejected under the cap")
"""


def test_huge_counters_are_rejected_inside_a_memory_cap() -> None:
    # Before the fix this raised MemoryError after building set(range(10**30)); the cap
    # (existing address space + 64 MiB) keeps the probe bounded on the shared host.
    done = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(MEMORY_CAPPED)],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": f"{SRC_DIR}:{TESTS_DIR}", "PATH": "/usr/bin:/bin"},
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr[-400:]
    assert "rejected under the cap" in done.stdout


def test_valid_sequences_that_are_reordered_by_time_still_pass() -> None:
    result = baseline()
    sequences = [e.sequence for e in result.events]
    # Later-inserted events with earlier times run first: sequence does not rise globally.
    assert any(b < a for a, b in zip(sequences, sequences[1:], strict=False))
    assert dataclasses.replace(result) == result
    # A moderately large valid run (hundreds of events) validates too.
    big = replay(make_spec(horizon=60_000), lambda: fresh_handlers_with(500))
    assert len(big.events) > 1000 and compare(big, big).outcome is (
        ComparisonOutcome.MATCH
    )
