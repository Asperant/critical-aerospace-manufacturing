# WP-CORE-004 implementation start

Accountable owner: Asrın Dündar (Asperant).
Canonical base: `ff56cfeb3142a41e0eb77b0649e6d8ab0fb7c506`.
Implementation branch: `wp/WP-CORE-004-temporal-genealogy`.

The live Asrın queue on 2026-10-24 returned WP-CORE-004 READY, unblocked,
as current_task and next_task. The accepted AUTO_PREPARATION.md is retained
unchanged. This record starts the implementation workstream; it is not
implementation completion, a readiness attestation, or acceptance evidence.

## Canonical scope and preparation review

Read `projectctl context WP-CORE-004`, the complete WBS card (04),
FR-CORE-009 through FR-CORE-012 and their RTM blocks (01/03), the
relational genealogy and manufacturing lifecycle architecture (02),
DEP-029 (05), applicable DoR/DoD and PR criteria (08), and change
classification (09). No requirement or architectural change is proposed.

The outcome is to preserve material history for RCA/exposure analysis.
Deliverables are append-only route-visit history, split/merge relations,
and relational genealogy/exposure queries. The prepared start task is
ReworkDirective execution without overwriting history; the remaining
workstream includes split/merge, exposure queries, and WP-NORMAL-scale
query sanity checks (100 tools / 1,000 active lots, synthetic development
fixtures only).

There is no HARD START edge. DEP-029 is HARD/INTEGRATION at
DN-CORE-LIFECYCLE COMPONENT_READY, requiring genealogy queries over real
lineage. Its precise consumer requirement is not populated in the canonical
edge. This is an integration limitation, not a manufactured START gate.
No lifecycle readiness or real-lineage integration is certified here.

## Implementation and verification plan

Extend only manufacturing-core and this WP's trace/evidence. Preserve the
initial migration and domain/query contracts. Add typed genealogy/rework
values and an additive Core-owned relational history implementation with
immutable component identity, conserved lot membership, permanent lineage,
separate rework execution segments, deterministic temporal traversal and
equipment/time exposure queries. No new graph store or infrastructure.

Keep protected command authorization and lifecycle producer binding at their
canonical boundaries; internal persistence or fixture execution must not
stand in for ExecuteApprovedReworkDirective integration. Do not choose
numeric rework limits or approve merge/rework policy on behalf of owners.

Run focused domain and negative-path tests first, then real disposable
PostgreSQL persistence/concurrency/rollback and temporal query checks.
Use TEST-CORE-GENEALOGY and the relevant rework portion of
TEST-CORE-STATEMACHINE; record WP-NORMAL sanity measurements with actual
environment and sample counts. Run Core typing/lint, contract checks and
canonical trace validation for changed surfaces. AV-SCEN-01,
BENCH-E2E-001 and BENCH-RQ1-001 remain pending until their real integrated
environments, lifecycle binding and evidence are available.

## DoR / DoD boundaries

Accepted preparation supplies DOR-WP-01…08 and DOR-TASK-01…12 start
assessments; no research FINAL access is involved. Work remains within
ARCH-CORE-DB, ARCH-CORE-DOMAIN and ARCH-CORE-GENEALOGY. Supporting review
is advisory; development approvals required: zero.

DOD-WP-01…04, 06, 07 and 12 apply. Update REALIZED_BY/VERIFIED_BY without
claiming more coverage than implemented, retain all negative evidence,
provide capability observability and operator notes, and never promote a
fixture into final evidence. Required CI, post-merge validation and actual
integrated evidence remain necessary for completion. Tests at this start
revision: NOT_EXECUTED. Product artifacts: NOT_PRODUCED. No DONE claim.
