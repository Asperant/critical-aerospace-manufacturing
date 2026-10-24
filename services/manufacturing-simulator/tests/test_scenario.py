"""TEST-SIM-KERNEL / TEST-SIM-DETERMINISM: kernel-local scenario initialization."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from manufacturing_simulator import (
    EventSpec,
    InitialEventSpec,
    InvalidConfigurationError,
    InvalidSeedError,
    InvalidTimeError,
    KernelScenarioConfig,
    ScenarioEngine,
    TimeUnit,
    UnknownEventKindError,
    make_payload,
)

KINDS = ("alpha", "beta")


def config(**overrides: Any) -> KernelScenarioConfig:
    values: dict[str, Any] = {
        "scenario_id": "scn",
        "scenario_version": "1",
        "seed": 11,
        "simulator_version": "sim-0",
        "horizon": 100,
        "initial_events": (
            InitialEventSpec("e1", 5, "alpha", make_payload({"component": "C-1"})),
            InitialEventSpec("e2", 5, "beta", make_payload({"component": "C-1"})),
            InitialEventSpec("e3", 0, "alpha"),
        ),
    }
    values.update(overrides)
    return KernelScenarioConfig(**values)


def mapping() -> dict[str, Any]:
    return {
        "scenario_id": "scn",
        "scenario_version": "1",
        "seed": 11,
        "simulator_version": "sim-0",
        "horizon": 100,
        "time_unit": "us",
        "initial_events": [
            {"event_id": "e1", "time": 5, "kind": "alpha", "payload": {"a": 1}},
            {"event_id": "e2", "time": 0, "kind": "beta"},
        ],
    }


def test_initialize_builds_a_fresh_ordered_world() -> None:
    world = ScenarioEngine(KINDS).initialize(config())
    assert world.clock.now == 0 and world.clock.unit is TimeUnit.MICROSECOND
    assert world.state == {}
    assert world.rng.master_seed == 11
    assert world.correlation_id == "scn/1/seed-11"
    assert [(e.time, e.event_id) for e in world.queue.pending()] == [
        (0, "e3"),
        (5, "e1"),
        (5, "e2"),
    ]


def test_listed_order_decides_equal_time_order() -> None:
    forward = config(
        initial_events=(
            InitialEventSpec("x", 3, "alpha"),
            InitialEventSpec("y", 3, "alpha"),
        )
    )
    backward = config(
        initial_events=(
            InitialEventSpec("y", 3, "alpha"),
            InitialEventSpec("x", 3, "alpha"),
        )
    )
    engine = ScenarioEngine(KINDS)
    assert [e.event_id for e in engine.initialize(forward).queue.pending()] == [
        "x",
        "y",
    ]
    assert [e.event_id for e in engine.initialize(backward).queue.pending()] == [
        "y",
        "x",
    ]


def test_repeated_opaque_entity_references_are_allowed() -> None:
    world = ScenarioEngine(KINDS).initialize(config())
    refs = [dict(e.payload).get("component") for e in world.queue.pending()]
    assert refs.count("C-1") == 2


def test_two_worlds_share_no_mutable_state() -> None:
    engine = ScenarioEngine(KINDS)
    cfg = config()
    first, second = engine.initialize(cfg), engine.initialize(cfg)
    assert first is not second
    assert first.queue is not second.queue
    assert first.rng is not second.rng
    assert first.clock is not second.clock
    assert first.state is not second.state
    first.queue.pop()
    first.clock.advance_to(9)
    first.state["touched"] = 1
    first.rng.stream("arrival").random(10)
    assert len(second.queue) == 3 and second.clock.now == 0 and second.state == {}
    fresh = engine.initialize(cfg)
    assert (
        second.rng.stream("arrival").random(3).tolist()
        == fresh.rng.stream("arrival").random(3).tolist()
    )


def test_configuration_is_immutable() -> None:
    cfg = config()
    with pytest.raises(AttributeError):
        cfg.seed = 2  # pyright: ignore[reportAttributeAccessIssue]
    assert isinstance(cfg.initial_events, tuple)
    listed = config(initial_events=[InitialEventSpec("z", 1, "alpha")])
    assert isinstance(listed.initial_events, tuple)


def test_unregistered_kind_is_rejected_and_engine_stays_usable() -> None:
    engine = ScenarioEngine(["alpha"])
    with pytest.raises(UnknownEventKindError):
        engine.initialize(config())
    assert engine.registered_kinds == frozenset({"alpha"})
    ok = config(initial_events=(InitialEventSpec("e", 1, "alpha"),))
    assert len(engine.initialize(ok).queue) == 1


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"seed": -1}, InvalidSeedError),
        ({"seed": True}, InvalidSeedError),
        ({"seed": 1.5}, InvalidSeedError),
        ({"seed": 2**200}, InvalidSeedError),
        ({"horizon": -1}, InvalidTimeError),
        ({"horizon": 1.0}, InvalidTimeError),
        ({"horizon": True}, InvalidTimeError),
        ({"scenario_id": ""}, InvalidConfigurationError),
        ({"scenario_id": " x"}, InvalidConfigurationError),
        ({"scenario_version": None}, InvalidConfigurationError),
        ({"simulator_version": ""}, InvalidConfigurationError),
        ({"time_unit": "us"}, InvalidConfigurationError),
        ({"initial_events": ("not-an-event",)}, InvalidConfigurationError),
    ],
)
def test_malformed_configuration_is_rejected(
    overrides: dict[str, Any], error: type[Exception]
) -> None:
    with pytest.raises(error):
        config(**overrides)


def test_duplicate_initial_event_ids_are_rejected() -> None:
    with pytest.raises(InvalidConfigurationError):
        config(
            initial_events=(
                InitialEventSpec("dup", 1, "alpha"),
                InitialEventSpec("dup", 2, "beta"),
            )
        )


def test_initial_event_beyond_horizon_is_rejected() -> None:
    with pytest.raises(InvalidTimeError):
        config(horizon=10, initial_events=(InitialEventSpec("late", 11, "alpha"),))
    ok = config(horizon=10, initial_events=(InitialEventSpec("edge", 10, "alpha"),))
    assert ok.initial_events[0].time == 10


@pytest.mark.parametrize(
    "kwargs",
    [
        {"event_id": "", "time": 1, "kind": "alpha"},
        {"event_id": "e", "time": -1, "kind": "alpha"},
        {"event_id": "e", "time": 1, "kind": ""},
        {"event_id": "e", "time": True, "kind": "alpha"},
    ],
)
def test_malformed_initial_events_are_rejected(kwargs: dict[str, Any]) -> None:
    with pytest.raises((InvalidConfigurationError, InvalidTimeError)):
        InitialEventSpec(**kwargs)


def test_initial_events_become_event_specs_with_ids() -> None:
    spec = InitialEventSpec("e", 4, "alpha", make_payload({"k": 1})).to_event_spec()
    assert spec == EventSpec(4, "alpha", (("k", 1),), "e")


def test_initialize_rejects_non_config_input() -> None:
    with pytest.raises(InvalidConfigurationError):
        ScenarioEngine(KINDS).initialize({"seed": 1})  # pyright: ignore[reportArgumentType]


def test_engine_rejects_malformed_registered_kinds() -> None:
    with pytest.raises(InvalidConfigurationError):
        ScenarioEngine(["ok", ""])


def test_from_mapping_reads_a_valid_mapping() -> None:
    cfg = KernelScenarioConfig.from_mapping(mapping())
    assert cfg.seed == 11 and cfg.time_unit is TimeUnit.MICROSECOND
    assert [e.event_id for e in cfg.initial_events] == ["e1", "e2"]
    assert cfg.initial_events[0].payload == (("a", 1),)
    assert cfg.initial_events[1].payload == ()


def test_from_mapping_defaults_optional_keys() -> None:
    data = mapping()
    del data["time_unit"], data["initial_events"]
    cfg = KernelScenarioConfig.from_mapping(data)
    assert cfg.time_unit is TimeUnit.MICROSECOND and cfg.initial_events == ()


def test_from_mapping_does_not_modify_its_input() -> None:
    data = mapping()
    snapshot = copy.deepcopy(data)
    KernelScenarioConfig.from_mapping(data)
    assert data == snapshot


def mutate_unknown_top_level(data: dict[str, Any]) -> None:
    data["topology"] = {"machines": 3}


def mutate_unknown_event_key(data: dict[str, Any]) -> None:
    data["initial_events"][0]["route"] = "R1"


def mutate_missing_seed(data: dict[str, Any]) -> None:
    del data["seed"]


def mutate_missing_event_kind(data: dict[str, Any]) -> None:
    del data["initial_events"][0]["kind"]


def mutate_bad_unit(data: dict[str, Any]) -> None:
    data["time_unit"] = "ms"


def mutate_events_as_string(data: dict[str, Any]) -> None:
    data["initial_events"] = "e1"


def mutate_event_not_mapping(data: dict[str, Any]) -> None:
    data["initial_events"] = [["e1", 1, "alpha"]]


def mutate_payload_nested(data: dict[str, Any]) -> None:
    data["initial_events"][0]["payload"] = {"a": {"b": 1}}


@pytest.mark.parametrize(
    "mutate",
    [
        mutate_unknown_top_level,
        mutate_unknown_event_key,
        mutate_missing_seed,
        mutate_missing_event_kind,
        mutate_bad_unit,
        mutate_events_as_string,
        mutate_event_not_mapping,
        mutate_payload_nested,
    ],
)
def test_from_mapping_rejects_malformed_input(mutate: Any) -> None:
    data = mapping()
    mutate(data)
    with pytest.raises(InvalidConfigurationError):
        KernelScenarioConfig.from_mapping(data)


def test_from_mapping_rejects_non_mapping() -> None:
    with pytest.raises(InvalidConfigurationError):
        KernelScenarioConfig.from_mapping(["seed"])  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize(
    "bad_payload",
    [
        False,
        True,
        0,
        1,
        "",
        "text",
        None,
        [],
        [["a", 1]],
        [["a"]],
        [["a", 1, 2]],
        [[1, 2]],
        [("a", 1)],
        ["ab"],
        3.5,
    ],
)
def test_from_mapping_rejects_every_non_mapping_payload(bad_payload: Any) -> None:
    data = mapping()
    data["initial_events"][0]["payload"] = bad_payload
    snapshot = copy.deepcopy(data)
    with pytest.raises(InvalidConfigurationError):
        KernelScenarioConfig.from_mapping(data)
    assert data == snapshot


def test_from_mapping_accepts_omitted_and_empty_object_payloads() -> None:
    data = mapping()
    del data["initial_events"][0]["payload"]
    omitted = KernelScenarioConfig.from_mapping(data)
    data["initial_events"][0]["payload"] = {}
    empty = KernelScenarioConfig.from_mapping(data)
    assert omitted.initial_events[0].payload == empty.initial_events[0].payload == ()
    data["initial_events"][0]["payload"] = {"b": 2, "a": 1}
    full = KernelScenarioConfig.from_mapping(data)
    assert full.initial_events[0].payload == (("a", 1), ("b", 2))
