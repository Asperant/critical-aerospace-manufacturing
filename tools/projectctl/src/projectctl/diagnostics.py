from pydantic import BaseModel, ConfigDict

from .enums import Severity
from .provenance import SourceRef


class Diagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    code: str
    severity: Severity
    message: str
    source: SourceRef | None = None
    record_id: str | None = None


def ordered(diagnostics: list[Diagnostic]) -> list[Diagnostic]:
    return sorted(diagnostics, key=lambda d: (
        d.code, d.record_id or "", d.source.path if d.source else "",
        d.source.line_start if d.source else 0, d.message,
    ))
