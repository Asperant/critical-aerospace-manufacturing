from pathlib import Path

import pytest


@pytest.fixture
def root():
    return Path(__file__).resolve().parents[3]


@pytest.fixture
def corpus(root):
    return (root / "docs/04_Work_Breakdown_Structure.md").read_text(encoding="utf-8")


@pytest.fixture
def sample():
    return """# WBS
## 4. Definitions
### 4.1 DoR
| ID | Rule |
|---|---|
| DOR-WP-01 | Source known |
| DOR-WP-02 | Target known |
### 4.2 DoD
| ID | Rule |
|---|---|
| DOD-WP-01 | Delivered |
| DOD-WP-02 | Traced |
## 6. Capability Areas and Work Packages
### 6.1 Simulator (`WP-SIM-*`, 1 work packages)
| WP | Title | Owner | Scope | Milestone | Size band |
|---|---|---|---|---|---|
| WP-SIM-001 | Kernel | Batu | F0 | M1 | M |
#### WP-SIM-001 — Kernel
| Field | Value |
|---|---|
| PrimaryOwner | Batu |
| Supporting owner (most frequent reviewer) | Asrın |
| ScopeClass | F0 |
| Target milestone / sprint window | M1 / S2 |
| Readiness node (05) | DN-SIM-KERNEL |
| Size band (indicative, no hour estimates) | M (indicative) |
| Status | NOT_STARTED |
**Purpose.** Deterministic execution.
**Source requirements (03).** FR-SIM-001, NFR-REP-001
**Architecture components (02).** ARCH-SIM-ENGINE
**Inputs / required contracts.** gated by DEP-001; WP-NORMAL is a workload
**Deliverables.**
- kernel
- RNG registry
**Major tasks.**
- implement clock
**Verification work (03 planned families).** TEST-SIM-KERNEL
**Expected evidence artifact.** CI evidence; NOT_YET_EXECUTED
**DoR / DoD.** DOR-WP-01…02 apply; DoD: DOD-WP-01…02.
**Cut / fallback semantics.** No cut.
## 7. Coverage
"""
