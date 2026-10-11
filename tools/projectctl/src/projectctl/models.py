from pydantic import BaseModel, ConfigDict

from .provenance import SourceRef


class Owner(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_spelling: str
    canonical_name: str | None


OWNER_NAMES = {
    "Asrın": "Asrın Dündar", "Selman": "Selman Özdemir",
    "Batu": "Batuhan Kaya", "Batuhan": "Batuhan Kaya", "Yavuz": "Yavuz Gümüş",
}


def resolve_owner(spelling: str) -> Owner:
    return Owner(source_spelling=spelling, canonical_name=OWNER_NAMES.get(spelling))


class CapabilityArea(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    title: str
    declared_wp_count: int
    provenance: SourceRef


class WorkPackage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    capability_area: str | None
    title: str
    purpose: str | None = None
    primary_owner: Owner | None = None
    supporting_reviewers: list[Owner] | None = None
    scope_class: str | None = None
    nfr_class: str | None = None
    raw_scope: str | None = None
    requirement_refs: list[str] | None = None
    architecture_refs: list[str] | None = None
    readiness_refs: list[str] | None = None
    dependency_refs: list[str] | None = None
    inputs_required_contracts: str | None = None
    deliverables: list[str] | None = None
    major_tasks: list[str] | None = None
    verification_expectations: str | None = None
    evidence_expectations: str | None = None
    milestone: str | None = None
    sprint_window: str | None = None
    raw_planning_window: str | None = None
    dor_refs: list[str] | None = None
    dod_refs: list[str] | None = None
    raw_dor_dod: str | None = None
    cut_fallback: str | None = None
    raw_planning_status: str | None = None
    size_band: str | None = None
    repository_reference: str | None = None
    risk_hooks: str | None = None
    integration_checkpoint: str | None = None
    provenance: SourceRef
