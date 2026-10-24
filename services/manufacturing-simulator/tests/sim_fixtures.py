"""Toy scenario used to exercise kernel mechanics.

The handlers carry no manufacturing semantics: they are opaque counters over the
kernel's scheduling and random-stream surfaces. Passing tests on this fixture
establish kernel mechanics only, not integrated acceptance or realism.
"""

from __future__ import annotations

import json
from typing import Any

from manufacturing_simulator import (
    EventSpec,
    ExecutionContext,
    InitialEventSpec,
    Kernel,
    KernelScenarioConfig,
    ScenarioEngine,
    ScheduledEvent,
    make_payload,
)

KINDS = ("arrive", "start", "finish")
SIMULATOR_VERSION = "kernel-test-0"


def count(ctx: ExecutionContext, key: str) -> int:
    value = ctx.state.get(key, 0)
    assert isinstance(value, int)
    return value


def _arrive(
    event: ScheduledEvent, ctx: ExecutionContext, *, arrivals: int, reverse: bool
) -> None:
    index = count(ctx, "arrivals")
    ctx.state["arrivals"] = index + 1
    if reverse:
        gap = int(ctx.stream("arrival").integers(1, 30))
        duration = int(ctx.stream("processing").integers(1, 50))
    else:
        duration = int(ctx.stream("processing").integers(1, 50))
        gap = int(ctx.stream("arrival").integers(1, 30))
    ctx.schedule(
        EventSpec(
            ctx.now,
            "start",
            make_payload({"item": f"I-{index}", "duration": duration}),
        )
    )
    if index + 1 < arrivals:
        ctx.schedule(EventSpec(ctx.now + gap, "arrive"))


def _start(event: ScheduledEvent, ctx: ExecutionContext) -> None:
    payload = dict(event.payload)
    duration = payload["duration"]
    assert isinstance(duration, int)
    ctx.schedule(EventSpec(ctx.now + duration, "finish", event.payload))


def _finish(event: ScheduledEvent, ctx: ExecutionContext, *, extra_draws: int) -> None:
    ctx.state["finished"] = count(ctx, "finished") + 1
    quality = ctx.stream("quality")
    for _ in range(extra_draws):
        quality.random()
    if float(quality.random()) < 0.1:
        ctx.state["defects"] = count(ctx, "defects") + 1


def toy_handlers(
    *, arrivals: int = 20, reverse: bool = False, extra_draws: int = 0
) -> dict[str, Any]:
    return {
        "arrive": lambda e, c: _arrive(e, c, arrivals=arrivals, reverse=reverse),
        "start": _start,
        "finish": lambda e, c: _finish(e, c, extra_draws=extra_draws),
    }


def toy_config(seed: int, *, horizon: int = 5000) -> KernelScenarioConfig:
    return KernelScenarioConfig(
        scenario_id="toy-kernel",
        scenario_version="1",
        seed=seed,
        simulator_version=SIMULATOR_VERSION,
        horizon=horizon,
        initial_events=(
            InitialEventSpec("init-arrive", 0, "arrive"),
            InitialEventSpec(
                "init-late-arrive", 0, "arrive", make_payload({"note": "same-time"})
            ),
        ),
    )


def build_kernel(
    seed: int,
    *,
    horizon: int = 5000,
    arrivals: int = 20,
    reverse: bool = False,
    extra_draws: int = 0,
) -> Kernel:
    handlers = toy_handlers(arrivals=arrivals, reverse=reverse, extra_draws=extra_draws)
    world = ScenarioEngine(KINDS).initialize(toy_config(seed, horizon=horizon))
    return Kernel(world, handlers)


def canonical_trace(kernel: Kernel) -> dict[str, Any]:
    """Complete local trace plus final local state, in a JSON-comparable form."""
    return {
        "records": [
            [
                r.sequence,
                r.time,
                r.kind,
                r.event_id,
                [list(pair) for pair in r.payload],
                r.outcome.value,
            ]
            for r in kernel.records()
        ],
        "state": sorted(kernel.world.state.items()),
        "now": kernel.world.clock.now,
        "queue_depth": len(kernel.world.queue),
    }


def run_toy(seed: int, **kwargs: Any) -> dict[str, Any]:
    kernel = build_kernel(seed, **kwargs)
    kernel.run_to_horizon(10_000)
    return canonical_trace(kernel)


def dumps(trace: dict[str, Any]) -> str:
    return json.dumps(trace, sort_keys=True, separators=(",", ":"))
