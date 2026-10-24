"""Simulator-owned deterministic discrete-event kernel (WP-SIM-001).

Simulated execution only: output is simulation data and is never real-factory
data. The kernel has no Core mutation path, persistence, broker or endpoint.
"""

from manufacturing_simulator.clock import SimulationClock, TimeUnit
from manufacturing_simulator.errors import (
    DuplicateHandlerError,
    HandlerExecutionError,
    InvalidConfigurationError,
    InvalidSeedError,
    InvalidTimeError,
    PastSchedulingError,
    RunFailedError,
    SimulatorError,
    UnknownEventKindError,
    UnknownStreamError,
)
from manufacturing_simulator.events import (
    EventSpec,
    FutureEventQueue,
    Payload,
    PayloadValue,
    ScheduledEvent,
    freeze_payload,
    make_payload,
)
from manufacturing_simulator.kernel import (
    PROVENANCE,
    EventHandler,
    ExecutionContext,
    ExecutionRecord,
    Kernel,
    KernelStatus,
    RecordOutcome,
    RunResult,
    RunStatus,
    StepOutcome,
    StepResult,
    TerminationReason,
)
from manufacturing_simulator.rng import (
    MAX_SEED,
    STREAM_IDS,
    RandomnessManager,
    StreamName,
    validate_seed,
)
from manufacturing_simulator.scenario import (
    InitialEventSpec,
    KernelScenarioConfig,
    ScenarioEngine,
    WorldState,
)

__all__ = [
    "MAX_SEED",
    "PROVENANCE",
    "STREAM_IDS",
    "DuplicateHandlerError",
    "EventHandler",
    "EventSpec",
    "ExecutionContext",
    "ExecutionRecord",
    "FutureEventQueue",
    "HandlerExecutionError",
    "InitialEventSpec",
    "InvalidConfigurationError",
    "InvalidSeedError",
    "InvalidTimeError",
    "Kernel",
    "KernelScenarioConfig",
    "KernelStatus",
    "PastSchedulingError",
    "Payload",
    "PayloadValue",
    "RandomnessManager",
    "RecordOutcome",
    "RunFailedError",
    "RunResult",
    "RunStatus",
    "ScenarioEngine",
    "ScheduledEvent",
    "SimulationClock",
    "SimulatorError",
    "StepOutcome",
    "StepResult",
    "StreamName",
    "TerminationReason",
    "TimeUnit",
    "UnknownEventKindError",
    "UnknownStreamError",
    "WorldState",
    "freeze_payload",
    "make_payload",
    "validate_seed",
]
