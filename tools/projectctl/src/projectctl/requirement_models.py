from enum import StrEnum
from pydantic import BaseModel, ConfigDict

from .enums import ScopeClass
from .models import Owner
from .provenance import SourceRef


class RequirementKind(StrEnum):
    FR = "FR"
    NFR = "NFR"


class QualityClass(StrEnum):
    H0 = "H0"
    A1 = "A1"
    S2 = "S2"
    C3 = "C3"


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    kind: RequirementKind
    title: str | None
    statement: str
    scope_class: ScopeClass | None
    quality_class: QualityClass | None
    primary_owner: Owner
    verification_codes: list[str] | None
    evidence_codes: list[str] | None
    revision: str | None = None
    catalog_status: str | None = None
    measurement_context: str | None = None
    provenance: SourceRef


class TraceOverlay(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    requirement_id: str
    assertions: dict
    provenance: SourceRef
