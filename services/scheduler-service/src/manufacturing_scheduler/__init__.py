"""Offline dispatch baselines and scheduling instance generator (WP-SCH-001).

An offline library: it selects jobs for a caller-built context. It has no server,
store or Core access, performs no production constraint validation and executes
nothing.
"""

from manufacturing_scheduler.baselines import (
    BASELINES,
    BaselineDefinition,
    BaselineStrength,
    FreezeStatus,
    LifecycleState,
    NotApplicable,
    get_baseline,
)
from manufacturing_scheduler.errors import (
    DuplicateJobIdError,
    IncompatibleTimeUnitError,
    InvalidContextError,
    InvalidInstanceConfigError,
    InvalidJobError,
    InvalidSeedError,
    InvalidTickError,
    SchedulerError,
    UnsupportedPolicyError,
)
from manufacturing_scheduler.instances import (
    GENERATOR_VERSION,
    MAX_SEED,
    InstanceMetadata,
    OfflineInstanceConfig,
    SchedulingInstance,
    generate,
)
from manufacturing_scheduler.models import (
    DecisionStatus,
    DispatchContext,
    DispatchDecision,
    DispatchJob,
    JobState,
    RankedJob,
    RankingKey,
)
from manufacturing_scheduler.policies import (
    POLICIES,
    CriticalRatioPolicy,
    DispatchPolicy,
    EddPolicy,
    FifoPolicy,
    SptPolicy,
    SrptPolicy,
    get_policy,
)

__all__ = [
    "BASELINES",
    "GENERATOR_VERSION",
    "MAX_SEED",
    "POLICIES",
    "BaselineDefinition",
    "BaselineStrength",
    "CriticalRatioPolicy",
    "DecisionStatus",
    "DispatchContext",
    "DispatchDecision",
    "DispatchJob",
    "DispatchPolicy",
    "DuplicateJobIdError",
    "EddPolicy",
    "FifoPolicy",
    "FreezeStatus",
    "IncompatibleTimeUnitError",
    "InstanceMetadata",
    "InvalidContextError",
    "InvalidInstanceConfigError",
    "InvalidJobError",
    "InvalidSeedError",
    "InvalidTickError",
    "JobState",
    "LifecycleState",
    "NotApplicable",
    "OfflineInstanceConfig",
    "RankedJob",
    "RankingKey",
    "SchedulerError",
    "SchedulingInstance",
    "SptPolicy",
    "SrptPolicy",
    "UnsupportedPolicyError",
    "generate",
    "get_baseline",
    "get_policy",
]
