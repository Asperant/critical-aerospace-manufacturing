"""Telemetry coverage of the mandatory deployables (WP-OBS-001; NFR-OBS-001/002).

``infra/observability/coverage.json`` declares, for each of the nine mandatory
deployables (02 "Mandatory Logical Deployables"), whether it already uses the
standard logging (``configure``) and health surface (``health_report``). This
module checks the declaration against the repository, so coverage can only be
claimed where the code really uses the helpers:

* a deployable that does not exist yet must be ``NOT_PRESENT``;
* a deployable that exists must be ``ADOPTED`` or ``PENDING``;
* ``ADOPTED`` (Python) means its pyproject depends on cap-observability and its
  sources call ``configure(`` (logging) or ``health_report(`` (health);
* ``PENDING`` needs an exemption with an owner and an expiry at most 30 days
  ahead, so a gap can never become permanent silently (like ci/flaky_tests.yaml).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

MANDATORY = (
    "command-center-web",
    "operations-bff",
    "manufacturing-core",
    "manufacturing-simulator",
    "digital-twin-service",
    "vision-service",
    "ai-intelligence-service",
    "scheduler-service",
    "automation-service",
)
OWNERS = {"Asrın", "Selman", "Batu", "Yavuz"}
MAX_EXEMPTION_DAYS = 30
SIGNALS = {"logging": "configure(", "health": "health_report("}


@dataclass
class Coverage:
    present: list[str] = field(default_factory=list)
    adopted: dict[str, list[str]] = field(
        default_factory=lambda: {"logging": [], "health": []}
    )
    pending: dict[str, list[str]] = field(
        default_factory=lambda: {"logging": [], "health": []}
    )
    violations: list[str] = field(default_factory=list)

    def summary(self) -> str:
        total = len(self.present)
        parts = [
            f"{signal} {len(self.adopted[signal])}/{total} adopted"
            + (
                f" ({len(self.pending[signal])} pending)"
                if self.pending[signal]
                else ""
            )
            for signal in SIGNALS
        ]
        absent = len(MANDATORY) - total
        return (
            f"telemetry coverage: {total}/{len(MANDATORY)} mandatory deployables exist; "
            + "; ".join(parts)
            + f"; {absent} not yet present"
        )


def _sources(path: Path) -> str:
    return "\n".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in sorted(path.rglob("*.py"))
        if ".venv" not in p.parts and "tests" not in p.parts
    )


def _uses_package(path: Path) -> bool:
    pyproject = path / "pyproject.toml"
    return pyproject.is_file() and "cap-observability" in pyproject.read_text("utf-8")


def check(registry: dict[str, Any], root: Path, today: date) -> Coverage:
    result = Coverage()
    entries: list[dict[str, Any]] = registry.get("deployables", [])
    names = [entry.get("name") for entry in entries]
    if sorted(map(str, names)) != sorted(MANDATORY):
        result.violations.append(
            f"registry must list exactly the nine mandatory deployables: {MANDATORY}"
        )
    for entry in entries:
        name = str(entry.get("name"))
        path = root / str(entry.get("path", ""))
        present = path.is_dir()
        if present:
            result.present.append(name)
        if entry.get("owner") not in OWNERS:
            result.violations.append(f"{name}: unknown owner {entry.get('owner')!r}")
        sources = _sources(path) if present else ""
        for signal, marker in SIGNALS.items():
            status = entry.get(signal)
            if not present:
                if status != "NOT_PRESENT":
                    result.violations.append(
                        f"{name}: {path} does not exist, {signal} must be NOT_PRESENT"
                    )
                continue
            if status == "NOT_PRESENT":
                result.violations.append(
                    f"{name}: exists at {path}; declare {signal} ADOPTED or PENDING"
                )
            elif status == "ADOPTED":
                if entry.get("runtime") == "python" and not (
                    _uses_package(path) and marker in sources
                ):
                    result.violations.append(
                        f"{name}: {signal} ADOPTED but {path} does not depend on "
                        f"cap-observability and call {marker}...)"
                    )
                else:
                    result.adopted[signal].append(name)
            elif status == "PENDING":
                problem = _exemption_problem(entry.get("exemption"), today)
                if problem:
                    result.violations.append(f"{name}: {signal} PENDING {problem}")
                else:
                    result.pending[signal].append(name)
            else:
                result.violations.append(f"{name}: unknown {signal} status {status!r}")
    return result


def _exemption_problem(exemption: Any, today: date) -> str | None:
    if not isinstance(exemption, dict):
        return "needs an exemption {reason, owner, expires_on}"
    exemption_data: dict[str, Any] = exemption  # type: ignore[reportUnknownVariableType]
    if not str(exemption_data.get("reason", "")).strip():
        return "exemption needs a reason"
    if exemption_data.get("owner") not in OWNERS:
        return "exemption needs a team owner"
    try:
        expires = date.fromisoformat(str(exemption_data.get("expires_on")))
    except ValueError:
        return "exemption expires_on must be YYYY-MM-DD"
    if expires < today:
        return f"exemption expired on {expires}"
    if expires > today + timedelta(days=MAX_EXEMPTION_DAYS):
        return f"exemption longer than {MAX_EXEMPTION_DAYS} days"
    return None


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: registry must be a JSON object")
    return data  # type: ignore[reportUnknownVariableType]
