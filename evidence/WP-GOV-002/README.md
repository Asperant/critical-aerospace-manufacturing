# WP-GOV-002 — Trace registry, edges and trace linter: evidence

Owner: Yavuz Gümüş · supporting reviewer: Asrın (advisory, CHG-018) · F1 · M2/S3–S4 ·
readiness node DN-PLAT-REPO · requirements FR-GOV-004, FR-GOV-005, FR-GOV-009,
NFR-GOV-009. DoR assessment on issue #79 (READY verified 2026-10-25); no inbound
dependency edge (early unlocker).

## Deliverables (04 card)

| Deliverable | Where |
|---|---|
| trace_edges registry + JSON Schema (seeded from 03 draft) | `traceability/trace_edges.yaml`, `traceability/trace_schema.json` (`cap.trace-registry/v1`), seeded from the 03 §17 records by `cap_trace.seed` |
| trace linter with checks TL-01…TL-13 (03 §18.1) | `tools/trace/src/cap_trace/` (`lint.py`, `references.py`, `sources.py`, `rules.py`, `views.py`, `impact.py`); CI step "Trace registry lint and tests (WP-GOV-002)" and, on pull requests, "PR Requirement-Impact (TL-13, WP-GOV-002)" |
| `mfgctl trace` generation of 03 views | `tools/mfgctl/src/mfgctl/trace.py`; `mfgctl trace` with validate, generate, seed, drift, impact, requirement, orphans; views in `traceability/generated/` |
| PR Requirement-Impact template | the existing `Requirements (...)` field of `.github/pull_request_template.md`, checked by TL-13; declared requirements are listed with their owners for advisory review |

## Slices

| Slice | Content |
|---|---|
| 1 | schema, loader, seed from 03 §17 (306 records), TL-01/04/05, drift report, CI step, CODEOWNERS |
| 2 | TL-02 referenced IDs (catalog, 01 items and invariants, 02 registry with its append-only allocations, 03 verification registry and §19 assets, ADRs, scenarios, risks, contracts, repository paths), TL-03, TL-10 prefix-boundary matching |
| 3 | TL-06 runs/evidence/claims, TL-08 completeness (FR-GOV-004/005) and regression against `origin/main`, TL-09, TL-11 class sufficiency and verify codes, TL-12 (NFR-GOV-009) |
| 4 | generated views, TL-07 freshness, `mfgctl trace` |
| 5 | TL-13 PR Requirement-Impact with owner routing; decision of 25 October 2026 (option A): 03 §17 stays the source, `mfgctl trace seed` in the same PR, CI runs `drift --strict` |
| 6 | TL-13 calibration (host control plane and CODEOWNERS are not product behavior), trace (03 delta, §17, §19.10), 04 repository reference, RUN-GOV-002-DEV-001 |

## Verification

| Asset | Family | Boundary mode | Where it runs |
|---|---|---|---|
| `tools/trace/tests/` (TEST-GOV-002-001…005, 03 §19.10) | TEST-GOV-TRACELINT | FIXTURE_ALLOWED for the rejection cases; the real registry, 01/02/03, catalog and team table are checked as well | CI t1-unit |
| `python -m cap_trace validate --base origin/main`, `drift --strict` | TEST-GOV-TRACELINT | REAL (the repository itself) | CI t1-unit |
| `python -m cap_trace impact` | TEST-GOV-TRACELINT | REAL (the PR description and its changed files) | CI t1-unit, pull requests |
| RUN-GOV-002-DEV-001 | all of the above | REAL | shared host (DEV) |

Negative paths covered: invalid schema, unknown and vague relations, duplicate
edges, undeclared sources, requirements missing from or foreign to the catalog,
retired requirements, unresolvable items, invariants, components, verification
assets, ADRs, scenarios, risks, contracts and repository paths (including path
traversal), identities glued to other text, unknown runs, evidence bundles and
claims, removed coverage edges with and without a CHG reference, claims on
STALE evidence, F0 without an integrated path, inspection-only H0, unmatched
verify codes, VERIFIED without evidence, missing/stale/foreign views, missing,
empty and invalid PR declarations, unreadable inputs and unknown base revisions.

## TL-13 calibration

Before enabling TL-13 for every pull request it was run against the last 25
merged PRs. Five did not pass the first rule: host-control and automatic
START-preparation PRs (#82, #77, #66, #59) touch only `tools/host/`, change
records, evidence, project control and CODEOWNERS, which are not product
behavior and are now exempt; #52 left the template field empty and still fails,
which is the intended result.

## RUN-GOV-002-DEV-001

`collect_run.py` records a run on the shared host against the actual repository
(boundary mode REAL): the full lint with the TL-08 base, strict drift, a
reproducibility check (seed and generate leave the tree unchanged), the trace
tests, four TL-13 probes, a negative probe (one ALLOCATED_TO edge rewritten to
an unknown component must fail TL-02; the registry is restored) and the orphan
summary. Results are in `RUN-GOV-002-DEV-001/record.json` with the raw outputs
next to it; host paths and the host name are redacted.

## What this evidence does not claim

INSP-GOV-ACCEPT (generated acceptance coverage and release acceptance record
reviewed at EVALUATION) belongs to WP-GOV-003, so FR-GOV-009 and NFR-GOV-009 stay
EVIDENCE_PENDING. The DERIVED_FROM edges of FR-GOV-004 remain the 03 projection
pending owner confirmation (GAP-RTM-006). Artifact-type relations (USES_DATA,
USES_MODEL, GOVERNED_BY) and descriptive interface surfaces have no identity
registry yet; `validate` counts them instead of resolving them. No EvidenceID,
accepted measurement or VERIFIED state is claimed.
