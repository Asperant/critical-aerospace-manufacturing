"""Specs and handler bundles for the replay tests (toy scenario, kernel mechanics only).

Shared by ``test_replay`` and ``replay_api_worker`` so both build the same replay.
The deliberately nondeterministic bundles exist only to prove the detection paths.
"""

from __future__ import annotations

import itertools
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from manufacturing_simulator import (
    EventSpec,
    ExecutionContext,
    PayloadValue,
    ReplayIdentity,
    ReplayResult,
    ReplaySpec,
    ScheduledEvent,
    make_payload,
    replay,
)
from sim_fixtures import toy_config, toy_handlers

TESTS_DIR = Path(__file__).resolve().parent
SRC_DIR = TESTS_DIR.parent / "src"
SEED = 20261028
IDENTITY = ReplayIdentity.for_current_runtime("test-source-0", "toy-handlers/1")
INITIAL_STATE = {"scale": 1.5, "note": "initial"}


def make_spec(
    seed: int = SEED,
    *,
    horizon: int = 5000,
    max_events: int = 10_000,
    initial_state: Any = INITIAL_STATE,
    until: int | None = None,
    identity: ReplayIdentity = IDENTITY,
) -> ReplaySpec:
    return ReplaySpec(
        config=toy_config(seed, horizon=horizon),
        identity=identity,
        max_events=max_events,
        initial_state=initial_state,
        until=until,
    )


def fresh_handlers() -> dict[str, Any]:
    return toy_handlers()


def fresh_handlers_with(arrivals: int) -> dict[str, Any]:
    """The toy bundle with a chosen number of arrivals (a larger, still valid run)."""
    return toy_handlers(arrivals=arrivals)


def reversed_handlers() -> dict[str, Any]:
    """The same bundle built in the opposite mapping order."""
    return dict(reversed(list(toy_handlers().items())))


def _with_start_extra(extra: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    handlers = toy_handlers()

    def start(event: ScheduledEvent, ctx: ExecutionContext) -> None:
        payload = dict(event.payload)
        duration = payload["duration"]
        assert isinstance(duration, int)
        ctx.schedule(
            EventSpec(
                ctx.now + duration, "finish", make_payload({**payload, **extra()})
            )
        )

    handlers["start"] = start
    return handlers


def hash_dependent_handlers() -> dict[str, Any]:
    """Injected nondeterminism: depends on the Python hash seed of the process."""
    return _with_start_extra(lambda: {"h": hash("probe") % 1000})


_SHARED_CALLS = itertools.count()


def shared_state_handlers() -> dict[str, Any]:
    """Injected nondeterminism: state shared between replays through a global."""
    return _with_start_extra(lambda: {"n": next(_SHARED_CALLS)})


def variant_handlers(
    *,
    tag: PayloadValue = 1,
    marker: PayloadValue = 1,
    late_tag: str = "a",
    late_time: int = 10**6,
    order: str = "xy",
    extra_draws: int = 0,
) -> dict[str, Any]:
    """The toy bundle with small, deliberate behaviour differences.

    ``tag`` rides on every ``finish`` payload and ``marker`` lands in the local state;
    ``1``, ``1.0`` and ``True`` compare equal in Python but are different values.
    ``order`` inserts two same-time events in that order. ``late_tag`` tags an event
    that stays pending beyond the horizon (so only the final queue differs) unless
    ``late_time`` moves it inside the run, where it executes as one extra last event.
    """
    handlers = toy_handlers(extra_draws=extra_draws)
    inner_arrive, inner_finish = handlers["arrive"], handlers["finish"]

    def arrive(event: ScheduledEvent, ctx: ExecutionContext) -> None:
        first = ctx.state.get("arrivals", 0) == 0
        inner_arrive(event, ctx)
        if first:
            for letter in order:
                ctx.schedule(EventSpec(10, "finish", make_payload({"tag": letter})))
            ctx.schedule(
                EventSpec(late_time, "finish", make_payload({"tag": late_tag}))
            )

    def start(event: ScheduledEvent, ctx: ExecutionContext) -> None:
        payload = dict(event.payload)
        duration = payload["duration"]
        assert isinstance(duration, int)
        ctx.schedule(
            EventSpec(
                ctx.now + duration, "finish", make_payload({**payload, "tag": tag})
            )
        )

    def finish(event: ScheduledEvent, ctx: ExecutionContext) -> None:
        inner_finish(event, ctx)
        ctx.state["marker"] = marker

    handlers.update(arrive=arrive, start=start, finish=finish)
    return handlers


def run_replay(seed: int = SEED, **spec: Any) -> ReplayResult:
    """One replay of the toy bundle in this process."""
    return replay(make_spec(seed, **spec), fresh_handlers)


def worker(seed: int, variant: str, hash_seed: str, timeout: float = 120) -> str:
    """Stdout of ``replay_api_worker.py`` run in a fresh process with that hash seed."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONHASHSEED"}
    env["PYTHONHASHSEED"] = hash_seed
    env["PYTHONPATH"] = os.pathsep.join([str(SRC_DIR), str(TESTS_DIR)])
    done = subprocess.run(
        [sys.executable, str(TESTS_DIR / "replay_api_worker.py"), str(seed), variant],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        check=False,
    )
    assert done.returncode == 0, f"worker exit {done.returncode}: {done.stderr}"
    return done.stdout
