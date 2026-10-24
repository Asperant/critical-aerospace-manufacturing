"""Kernel-local scenario initialization (ARCH-SIM-SCENARIO).

``KernelScenarioConfig`` is a minimal in-memory fixture shape for exercising the
kernel. It is NOT the canonical ScenarioDefinition schema: it carries no
topology, route, resource, failure-model or quality-model fields, and unknown
input is rejected rather than ignored. Component and resource references are
opaque payload values; no Core identity is interpreted here.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, cast

from manufacturing_simulator.clock import SimulationClock, TimeUnit
from manufacturing_simulator.errors import (
    InvalidConfigurationError,
    InvalidTimeError,
    UnknownEventKindError,
)
from manufacturing_simulator.events import (
    EventSpec,
    FutureEventQueue,
    Payload,
    PayloadValue,
    freeze_payload,
    make_payload,
)
from manufacturing_simulator.rng import RandomnessManager, validate_seed
from manufacturing_simulator.validation import require_text, require_time


@dataclass(frozen=True)
class InitialEventSpec:
    """An initial event; ``event_id`` must be unique within a scenario."""

    event_id: str
    time: int
    kind: str
    payload: Payload = ()

    def __post_init__(self) -> None:
        require_text(self.event_id, "initial event_id")
        require_time(self.time, "initial event time")
        require_text(self.kind, "initial event kind")
        object.__setattr__(self, "payload", freeze_payload(self.payload))

    def to_event_spec(self) -> EventSpec:
        return EventSpec(
            time=self.time,
            kind=self.kind,
            payload=self.payload,
            event_id=self.event_id,
        )


_EVENT_KEYS = frozenset({"event_id", "time", "kind", "payload"})
_CONFIG_KEYS = frozenset(
    {
        "scenario_id",
        "scenario_version",
        "seed",
        "simulator_version",
        "time_unit",
        "horizon",
        "initial_events",
    }
)


def _reject_unknown_keys(
    data: Mapping[str, Any],
    allowed: frozenset[str],
    required: frozenset[str],
    what: str,
) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise InvalidConfigurationError(f"unknown {what} keys: {unknown}")
    missing = sorted(required - set(data))
    if missing:
        raise InvalidConfigurationError(f"missing {what} keys: {missing}")


@dataclass(frozen=True)
class KernelScenarioConfig:
    """Validated, immutable kernel-local scenario configuration."""

    scenario_id: str
    scenario_version: str
    seed: int
    simulator_version: str
    horizon: int
    time_unit: TimeUnit = TimeUnit.MICROSECOND
    initial_events: Sequence[InitialEventSpec] = field(default=())

    def __post_init__(self) -> None:
        require_text(self.scenario_id, "scenario_id")
        require_text(self.scenario_version, "scenario_version")
        require_text(self.simulator_version, "simulator_version")
        validate_seed(self.seed)
        require_time(self.horizon, "horizon")
        if not isinstance(self.time_unit, TimeUnit):
            raise InvalidConfigurationError("time_unit must be a TimeUnit")
        events = tuple(self.initial_events)
        seen: set[str] = set()
        for event in events:
            if not isinstance(event, InitialEventSpec):
                raise InvalidConfigurationError(
                    "initial_events must contain InitialEventSpec items"
                )
            if event.time > self.horizon:
                raise InvalidTimeError(
                    f"initial event {event.event_id!r} at {event.time} is beyond "
                    f"horizon {self.horizon}"
                )
            if event.event_id in seen:
                raise InvalidConfigurationError(
                    f"duplicate initial event_id {event.event_id!r}"
                )
            seen.add(event.event_id)
        object.__setattr__(self, "initial_events", events)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> KernelScenarioConfig:
        """Read a plain mapping; unknown or missing keys are rejected."""
        if not isinstance(data, Mapping):
            raise InvalidConfigurationError("scenario config must be a mapping")
        _reject_unknown_keys(
            data,
            _CONFIG_KEYS,
            _CONFIG_KEYS - {"time_unit", "initial_events"},
            "scenario config",
        )
        try:
            unit = TimeUnit(data.get("time_unit", TimeUnit.MICROSECOND))
        except ValueError:
            raise InvalidConfigurationError(
                f"unsupported time_unit: {data.get('time_unit')!r}"
            ) from None
        raw_events = data.get("initial_events", ())
        if isinstance(raw_events, str | bytes) or not isinstance(raw_events, Sequence):
            raise InvalidConfigurationError("initial_events must be a list")
        events = tuple(_event_from_mapping(item) for item in raw_events)
        return cls(
            scenario_id=data["scenario_id"],
            scenario_version=data["scenario_version"],
            seed=data["seed"],
            simulator_version=data["simulator_version"],
            horizon=data["horizon"],
            time_unit=unit,
            initial_events=events,
        )


def _event_from_mapping(item: object) -> InitialEventSpec:
    if not isinstance(item, Mapping):
        raise InvalidConfigurationError("each initial event must be a mapping")
    data: Mapping[str, Any] = item
    _reject_unknown_keys(data, _EVENT_KEYS, _EVENT_KEYS - {"payload"}, "initial event")
    payload: Payload = ()
    if "payload" in data:
        raw_payload = data["payload"]
        if not isinstance(raw_payload, Mapping):
            raise InvalidConfigurationError(
                "initial event payload must be a mapping (an object)"
            )
        payload = make_payload(cast(Mapping[str, PayloadValue], raw_payload))
    return InitialEventSpec(
        event_id=data["event_id"],
        time=data["time"],
        kind=data["kind"],
        payload=payload,
    )


@dataclass
class WorldState:
    """One simulation world: nothing in it is shared with any other world."""

    config: KernelScenarioConfig
    clock: SimulationClock
    queue: FutureEventQueue
    rng: RandomnessManager
    state: dict[str, PayloadValue] = field(default_factory=lambda: {})

    @property
    def correlation_id(self) -> str:
        """Deterministic scenario/run correlation identity (no clock, no uuid)."""
        cfg = self.config
        return f"{cfg.scenario_id}/{cfg.scenario_version}/seed-{cfg.seed}"


class ScenarioEngine:
    """Builds fresh worlds from validated configurations."""

    def __init__(self, registered_kinds: Iterable[str]) -> None:
        kinds = frozenset(registered_kinds)
        for kind in kinds:
            require_text(kind, "registered event kind")
        self._kinds = kinds

    @property
    def registered_kinds(self) -> frozenset[str]:
        return self._kinds

    def initialize(self, config: KernelScenarioConfig) -> WorldState:
        """Return a fresh world; every check runs before any world is built."""
        if not isinstance(config, KernelScenarioConfig):
            raise InvalidConfigurationError("config must be a KernelScenarioConfig")
        for event in config.initial_events:
            if event.kind not in self._kinds:
                raise UnknownEventKindError(
                    f"initial event {event.event_id!r} has unregistered kind "
                    f"{event.kind!r}"
                )
        world = WorldState(
            config=config,
            clock=SimulationClock(config.time_unit),
            queue=FutureEventQueue(),
            rng=RandomnessManager(config.seed),
        )
        for event in config.initial_events:
            world.queue.schedule(event.to_event_spec(), now=0)
        return world
