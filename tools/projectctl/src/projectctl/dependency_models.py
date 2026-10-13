from enum import StrEnum
from pydantic import BaseModel, ConfigDict

from .provenance import SourceRef


class Readiness(StrEnum):
    DEFINED = "DEFINED"
    CONTRACT_READY = "CONTRACT_READY"
    SKELETON_READY = "SKELETON_READY"
    COMPONENT_READY = "COMPONENT_READY"
    INTEGRATION_READY = "INTEGRATION_READY"
    EVALUATION_READY = "EVALUATION_READY"
    FROZEN = "FROZEN"


class Strength(StrEnum):
    HARD = "HARD"
    SOFT = "SOFT"


class Kind(StrEnum):
    CONTRACT = "CONTRACT"
    CAPABILITY = "CAPABILITY"
    DATA = "DATA"
    RUNTIME = "RUNTIME"
    EVIDENCE = "EVIDENCE"
    FREEZE = "FREEZE"


class Stage(StrEnum):
    START = "START"
    INTEGRATION = "INTEGRATION"
    MILESTONE_EXIT = "MILESTONE_EXIT"
    FREEZE = "FREEZE"


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Endpoint(Record):
    node: str
    owner: str


class Semantics(Record):
    kind: Kind
    strength: Strength
    blocking_stage: Stage
    required_readiness: Readiness | None


class DependencyNode(Record):
    id: str
    name: str
    type: str
    raw_owner: str
    readiness_levels: list[Readiness]
    raw_readiness: str
    architecture_refs: list[str]
    raw_requirement_refs: str
    provenance: SourceRef


class DependencyEdge(Record):
    id: str
    predecessor: Endpoint
    successor: Endpoint
    semantics: Semantics
    need_by: str
    fallback: str | None
    unblock_evidence: str
    precise_requirement: str | None
    risk_class: str | None
    source: str
    status: str
    provenance: SourceRef

    @property
    def blocking(self):
        return self.semantics.strength == Strength.HARD
