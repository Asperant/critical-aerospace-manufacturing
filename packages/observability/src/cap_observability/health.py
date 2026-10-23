"""Health surface helper: ``cap.health/v1`` reports (WP-OBS-001; NFR-OBS-001).

A service lists its cheap checks (Item 47 §67: no model evaluation, heavy scan
or simulation inside a health check) and returns ``health_report(...)`` from its
health endpoint. The aggregate status is always derived from the checks with
the dependency-class rule of Item 47 §68, so a service cannot claim READY while
a required dependency is down.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

Status = Literal["READY", "DEGRADED", "UNAVAILABLE"]
Kind = Literal["readiness", "dependency", "capability"]
DependencyClass = Literal["REQUIRED", "DEGRADABLE", "OPTIONAL"]


@dataclass(frozen=True)
class Check:
    name: str
    kind: Kind
    dependency_class: DependencyClass
    status: Status
    detail: str | None = None
    duration_ms: float | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "name": self.name,
            "kind": self.kind,
            "class": self.dependency_class,
            "status": self.status,
        }
        if self.detail is not None:
            out["detail"] = self.detail[:256]
        if self.duration_ms is not None:
            out["duration_ms"] = round(max(self.duration_ms, 0.0), 3)
        return out


def aggregate(checks: Sequence[Mapping[str, Any]]) -> Status:
    """Item 47 §68: REQUIRED failure → UNAVAILABLE, DEGRADABLE failure → DEGRADED."""
    status: Status = "READY"
    for check in checks:
        if check["class"] == "OPTIONAL" or check["status"] == "READY":
            continue
        if check["class"] == "REQUIRED" and check["status"] == "UNAVAILABLE":
            return "UNAVAILABLE"
        status = "DEGRADED"
    return status


def health_report(
    service: str,
    environment: str,
    checks: Sequence[Check],
    *,
    live: bool = True,
    correlation_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """A conforming ``cap.health/v1`` document for the given checks."""
    if not checks:
        raise ValueError("a health surface needs at least one check")
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    items = [check.as_dict() for check in checks]
    report: dict[str, Any] = {
        "schema": "cap.health/v1",
        "service": service,
        "environment": environment,
        "checked_at": moment.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "live": live,
        "status": aggregate(items) if live else "UNAVAILABLE",
        "checks": items,
    }
    if correlation_id is not None:
        report["correlation_id"] = correlation_id
    return report
