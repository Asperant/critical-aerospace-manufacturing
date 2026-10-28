"""BaselineDefinition records SCH-B1..SCH-B5 (docs/01 Item 14 metadata; FR-SCH-010).

A record says what each rule is. It is not a research status: every record is
``IMPLEMENTED``, ``NOT_FROZEN`` and unevaluated. Comparator class and strength cite
their basis; where the canonical text gives none, the value is an implementation
proposal for owner review, not a published benchmark claim.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from manufacturing_scheduler.errors import UnsupportedPolicyError
from manufacturing_scheduler.policies import POLICIES


class LifecycleState(Enum):
    CANDIDATE = "CANDIDATE"
    IMPLEMENTED = "IMPLEMENTED"
    VERIFIED = "VERIFIED"
    TUNED = "TUNED"
    FROZEN = "FROZEN"
    EVALUATED = "EVALUATED"
    RETIRED = "RETIRED"


class FreezeStatus(Enum):
    NOT_FROZEN = "NOT_FROZEN"
    FROZEN = "FROZEN"


class BaselineStrength(Enum):
    SANITY = "SANITY"
    SIMPLE = "SIMPLE"
    STANDARD = "STANDARD"
    STRONG = "STRONG"


@dataclass(frozen=True, slots=True)
class NotApplicable:
    reason: str


@dataclass(frozen=True, slots=True)
class BaselineDefinition:
    baseline_id: str
    baseline_family: str
    research_question_ids: tuple[str, ...]
    comparator_class: str
    comparator_class_basis: str
    baseline_strength: BaselineStrength
    strength_basis: str
    method_description: str
    implementation_version: str
    git_sha: str | None
    git_sha_binding: str
    information_access: str
    training_datasets: NotApplicable
    preprocessing: str
    output_contract: str
    hyperparameters: tuple[tuple[str, str], ...]
    tuning_protocol: str
    compute_budget: str
    api_token_budget: NotApplicable
    seed_policy: str
    failure_policy: str
    references: tuple[str, ...]
    limitations: tuple[str, ...]
    freeze_status: FreezeStatus
    lifecycle_state: LifecycleState


_OPERATIONAL = "BC-2 Operational Baseline"
_PROPOSAL = "implementation proposal for owner review; docs give no strength grade"
_TIE_BREAK = ("tie_break", "queue_entry_tick, then job_id")


def _record(
    baseline_id: str,
    *,
    comparator_class: str = _OPERATIONAL,
    comparator_class_basis: str = "docs/02 comparator taxonomy lists dispatch rules as BC-2",
    baseline_strength: BaselineStrength = BaselineStrength.STANDARD,
    strength_basis: str = _PROPOSAL,
    method_description: str,
    hyperparameters: tuple[tuple[str, str], ...] = (),
    limitations: tuple[str, ...],
) -> BaselineDefinition:
    policy = POLICIES[baseline_id]
    return BaselineDefinition(
        baseline_id=baseline_id,
        baseline_family="RQ-2 scheduling dispatch heuristics (FIFO/EDD/CR/SPT/SRPT)",
        research_question_ids=("RQ-2",),
        comparator_class=comparator_class,
        comparator_class_basis=comparator_class_basis,
        baseline_strength=baseline_strength,
        strength_basis=strength_basis,
        method_description=method_description,
        implementation_version=policy.version,
        git_sha=None,
        git_sha_binding="resolved from the checked-out source when a run is captured",
        information_access=(
            "released, eligible jobs only: queue-entry tick, due tick, next-operation "
            "and remaining-route processing ticks; no Oracle label, future arrival, "
            "Core or Twin state"
        ),
        training_datasets=NotApplicable("rule-based method; nothing is trained"),
        preprocessing="none; integer ticks are validated, never scaled or rounded",
        output_contract=(
            "DispatchDecision: SELECTED job ID with the full ranking keys, or "
            "NO_CANDIDATES; no state is mutated and nothing is executed"
        ),
        hyperparameters=(*hyperparameters, _TIE_BREAK),
        tuning_protocol="none; a deterministic untuned rule, no tuning on any data",
        compute_budget=(
            "pure Python, one process, O(n log n) per decision over n candidates; "
            "no GPU or network; no time limit is imposed by this package"
        ),
        api_token_budget=NotApplicable("no model or external API is used"),
        seed_policy=(
            "the rule consumes no randomness; compared runs share the instance "
            "generator seed set"
        ),
        failure_policy=(
            "invalid input raises a named SchedulerError before any decision; an "
            "empty dispatchable queue is NO_CANDIDATES; nothing is dropped silently"
        ),
        references=(
            "docs/01_Master_Project_Specification.md (RQ-2 baseline family SCH-B1..B5; "
            "BaselineDefinition metadata)",
            "docs/02_System_Architecture_Specification.md (Baseline Methodology)",
            "docs/04_Work_Breakdown_Structure.md (WP-SCH-001)",
        ),
        limitations=(
            "job eligibility is caller-supplied; no production constraint, "
            "qualification or hold validation",
            "evaluated on synthetic offline fixtures only; no campaign has been run",
            *limitations,
        ),
        freeze_status=FreezeStatus.NOT_FROZEN,
        lifecycle_state=LifecycleState.IMPLEMENTED,
    )


_DEFINITIONS = (
    _record(
        "SCH-B1",
        comparator_class_basis="docs/01 SCH-B1 'Operational baseline'; docs/02 BC-2",
        baseline_strength=BaselineStrength.SIMPLE,
        method_description="First in, first out: the earliest queue-entry tick first.",
        limitations=("ignores due dates and processing times",),
    ),
    _record(
        "SCH-B2",
        method_description="Earliest due date: the smallest due tick first.",
        limitations=("ignores processing times",),
    ),
    _record(
        "SCH-B3",
        method_description=(
            "Critical ratio: the smallest (due_tick - now) / remaining_route_ticks "
            "first, as an exact rational; an overdue job keeps its negative ratio."
        ),
        hyperparameters=(
            ("ratio", "(due_tick - now) / remaining_route_ticks"),
            ("arithmetic", "exact fractions.Fraction"),
        ),
        limitations=(
            "this formula is one documented variant; docs/01 leaves the exact "
            "versioned formula to the implementation",
        ),
    ),
    _record(
        "SCH-B4",
        method_description=(
            "Shortest processing time: the smallest next-operation processing time "
            "first. Not the remaining-route time, which is SCH-B5."
        ),
        limitations=("ignores due dates and the work left after the next operation",),
    ),
    _record(
        "SCH-B5",
        comparator_class="BC-3 Strong Baseline",
        comparator_class_basis="docs/01 SCH-B5 'Strong heuristic comparator'",
        baseline_strength=BaselineStrength.STRONG,
        strength_basis="docs/01 SCH-B5 'Strong heuristic comparator'; not benchmarked",
        method_description=(
            "Shortest remaining processing time: the smallest remaining-route "
            "processing time first, ranked at the supplied decision epoch."
        ),
        limitations=(
            "a ranking only; a running operation is never preempted",
            "ignores due dates",
        ),
    ),
)

BASELINES: Mapping[str, BaselineDefinition] = MappingProxyType(
    {definition.baseline_id: definition for definition in _DEFINITIONS}
)


def get_baseline(baseline_id: object) -> BaselineDefinition:
    """The record for ``baseline_id`` (``SCH-B1``..``SCH-B5``)."""
    if not isinstance(baseline_id, str) or baseline_id not in BASELINES:
        raise UnsupportedPolicyError(
            f"unsupported baseline {baseline_id!r}; supported: {sorted(BASELINES)}"
        )
    return BASELINES[baseline_id]
