"""A minimal repository with every identity source the trace linter reads."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

MASTER = """\
# 81 — Functional Requirements Catalog

FRC-INV-01 every requirement has one identity. SIM-REAL-INV-01 is a different family.

# 82 — Non-Functional Requirements Catalog

NFR-INV-01 thresholds stay separate. Risk PLAT-R01 and scenario AV-SCEN-01.
IC-AUTO-003 — Typed Operational Command.
"""
ARCHITECTURE = """\
## Part 52

### Architecture Component ID Registry (New — Defined by This Document)

#### `ARCH-PLAT-*`

| ID | Component |
|---|---|
| ARCH-PLAT-CICD | CI pipeline |
| ARCH-INV-001 | not a component |

### Using This Registry

| ARCH-NOT-REGISTERED | outside the registry section |

### Append-only component allocations (CHG-010)

| ID | Home |
|---|---|
| ARCH-DATA-OBJ | object storage |
"""
VERIFICATION = """\
## 9. View D

### 9.X Verification Asset Registry (planned) with backward traceability

| Family | Owner |
|---|---|
| TEST-GOV-TRACELINT | Yavuz |

## 19. RTM Maintenance Protocol

### 19.1 WP-GOV-001 concrete implementation and verification assets

| Concrete asset | Family | Source requirements |
|---|---|---|
| TEST-GOV-001 (`test_gov_001_*`) | TEST-GOV-CATALOG | FR-GOV-001 |

## 20. Rejected Alternatives
"""


def write_sources(repo: Path, requirements: list[str]) -> None:
    for folder in ("docs/adr", "requirements", "ci", "traceability"):
        (repo / folder).mkdir(parents=True, exist_ok=True)
    (repo / "docs/01_Master_Project_Specification.md").write_text(MASTER, "utf-8")
    (repo / "docs/02_System_Architecture_Specification.md").write_text(
        ARCHITECTURE, "utf-8"
    )
    (repo / "docs/adr/0005-seaweedfs-object-storage.md").write_text("# ADR\n", "utf-8")
    catalog = {"requirements": [{"id": r, "status": None} for r in requirements]}
    (repo / "requirements/catalog.json").write_text(json.dumps(catalog), "utf-8")
    strategy = {
        "suites": [{"test_ids": ["TEST-GOV-002-001"]}],
        "test_id": {"legacy": []},
    }
    (repo / "ci/test-strategy.json").write_text(json.dumps(strategy), "utf-8")
    schema = (ROOT / "traceability/trace_schema.json").read_text("utf-8")
    (repo / "traceability/trace_schema.json").write_text(schema, "utf-8")


@pytest.fixture
def mini_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    write_sources(repo, ["FR-GOV-001", "NFR-GOV-009"])
    return repo


def full_rtm(*blocks: str) -> str:
    """An 03 with §17 records plus the §9.X and §19 registries."""
    body = "\n".join(f"### 17.X\n\n```yaml\n{b}```\n" for b in blocks)
    return (
        f"# 03\n\n## 17. Requirement Trace Records\n\n{body}\n## 18. Companion\n\n"
        + VERIFICATION
    )


@pytest.fixture
def write_rtm(mini_repo: Path) -> Callable[..., None]:
    def write(*blocks: str) -> None:
        (mini_repo / "docs/03_Requirements_Traceability_Matrix.md").write_text(
            full_rtm(*blocks), "utf-8"
        )

    return write
