"""Replay matrices for WP-SIM-002: equality, partial runs and the controlled negatives.

Usage (repository root, locked CI environment, PYTHONPATH=ci:ci/scripts):
    python evidence/WP-SIM-002/replay_matrix.py
Prints one JSON line and exits non-zero unless every check below holds. The counts are
reported separately and never merged: accepted equality, partial (not accepted)
equality, behaviour differences that must not match, structural corruptions that must
be rejected, and runs that must be refused before any handler is created.

Toy-kernel fixtures only: a bounded development matrix, not BENCH-SIMVAL-001 or
REPRO-NONOWNER-001, and not a proof for arbitrary handlers, NumPy versions or CPUs.
"""

import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
TESTS = REPO / "services/manufacturing-simulator/tests"
SEEDS = (1, 7, 20261028, 424242)
HASH_SEEDS = ("0", "1", "424242", "random")
VARIANTS = ("plain", "shuffled")
PARTIAL_BUDGET = 25


def counting_factory(calls: list[int], inner: Any) -> Any:
    """A handler factory that records each call (a refused run must make none)."""

    def factory() -> Any:
        calls.append(1)
        return inner()

    return factory


def main() -> int:
    sys.path.insert(0, str(TESTS))
    import replay_matrices as rm
    from manufacturing_simulator import (
        FORMAT_VERSION,
        RNG_ALGORITHM,
        CanonicalizationError,
        ComparisonOutcome,
        IncompatibleRuntimeError,
        ReplayResult,
        compare,
        replay,
    )
    from replay_fixtures import IDENTITY, fresh_handlers, make_spec, worker

    match, partial = ComparisonOutcome.MATCH, ComparisonOutcome.PARTIAL_MATCH
    rows: list[dict[str, object]] = []
    partial_rows: list[dict[str, object]] = []
    reference: dict[str, dict[str, object]] = {}
    for seed in SEEDS:
        local = replay(make_spec(seed), fresh_handlers)
        reference[str(seed)] = {
            "events": len(local.events),
            "termination": local.termination.value,
            "event_digest": local.event_digest,
            "state_digest": local.state_digest,
        }
        for variant in VARIANTS:
            for hash_seed in HASH_SEEDS:
                remote = ReplayResult.from_json(worker(seed, variant, hash_seed))
                comparison = compare(local, remote)
                rows.append(
                    {
                        "seed": seed,
                        "variant": variant,
                        "hash_seed": hash_seed,
                        "outcome": comparison.outcome.value,
                        "accepted": comparison.accepted,
                    }
                )
    cut = replay(make_spec(SEEDS[2], max_events=PARTIAL_BUDGET), fresh_handlers)
    for hash_seed in HASH_SEEDS:
        remote = ReplayResult.from_json(worker(SEEDS[2], "partial", hash_seed))
        comparison = compare(cut, remote)
        partial_rows.append(
            {
                "seed": SEEDS[2],
                "hash_seed": hash_seed,
                "events": len(remote.events),
                "termination": remote.termination.value,
                "outcome": comparison.outcome.value,
                "accepted": comparison.accepted,
            }
        )
    behaviour = {n: o.value for n, o in rm.behavior_outcomes().items()}
    objects = {n: rm.rejected(build) for n, build in rm.object_corruptions().items()}
    texts = {
        n: rm.rejected(lambda t=t: ReplayResult.from_json(t))
        for n, t in rm.json_corruptions().items()
    }
    refused: dict[str, dict[str, Any]] = {}
    for label, change in (
        ("false numpy_version", {"numpy_version": "not-the-runtime"}),
        ("false rng_algorithm", {"rng_algorithm": "fake"}),
    ):
        calls: list[int] = []
        spec = make_spec(identity=dataclasses.replace(IDENTITY, **change))
        try:
            replay(spec, counting_factory(calls, fresh_handlers))
            raised = False
        except IncompatibleRuntimeError:
            raised = True
        refused[label] = {"refused": raised, "handler_factory_calls": len(calls)}
    zero = ReplayResult.from_json(worker(SEEDS[2], "hashdep", "0"))
    one = ReplayResult.from_json(worker(SEEDS[2], "hashdep", "1"))
    again = ReplayResult.from_json(worker(SEEDS[2], "hashdep", "1"))
    injected = {
        "different_hash_seeds": compare(zero, one).outcome.value,
        "same_hash_seed": compare(one, again).outcome.value,
    }
    false_matches = sorted(n for n, o in behaviour.items() if o == match.value)
    unexpected = sorted(
        n for n, o in behaviour.items() if o != rm.BEHAVIOR_EXPECTED[n][1].value
    )
    accepted_corruptions = sorted(
        [n for n, ok in objects.items() if not ok]
        + [n for n, ok in texts.items() if not ok]
    )
    ok = (
        all(r["outcome"] == match.value and r["accepted"] for r in rows)
        and all(
            r["outcome"] == partial.value and not r["accepted"] for r in partial_rows
        )
        and not false_matches
        and not unexpected
        and not accepted_corruptions
        and all(
            v["refused"] and not v["handler_factory_calls"] for v in refused.values()
        )
        and injected["different_hash_seeds"] == "EVENT_MISMATCH"
        and injected["same_hash_seed"] == match.value
    )
    document = {
        "kind": "toy-kernel development matrix; not BENCH-SIMVAL-001 or REPRO-NONOWNER-001",
        "format_version": FORMAT_VERSION,
        "rng_algorithm": RNG_ALGORITHM,
        "development_seeds": list(SEEDS),
        "hash_seeds": list(HASH_SEEDS),
        "variants": list(VARIANTS),
        "reference_results": reference,
        "equality_accepted": {
            "cases": len(rows),
            "matches": sum(r["outcome"] == match.value for r in rows),
            "rows": rows,
        },
        "partial_not_accepted": {
            "event_budget": PARTIAL_BUDGET,
            "cases": len(partial_rows),
            "partial_matches": sum(r["outcome"] == partial.value for r in partial_rows),
            "accepted": sum(bool(r["accepted"]) for r in partial_rows),
            "rows": partial_rows,
        },
        "behaviour_differences": {
            "cases": len(behaviour),
            "false_matches": false_matches,
            "unexpected_outcomes": unexpected,
            "outcomes": behaviour,
        },
        "structural_corruptions": {
            "in_memory_cases": len(objects),
            "json_cases": len(texts),
            "accepted": accepted_corruptions,
            "rejected_with": CanonicalizationError.__name__,
        },
        "refused_before_execution": refused,
        "injected_hash_dependence": injected,
        "ok": ok,
    }
    print(json.dumps(document, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
