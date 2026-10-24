# WP-CORE-004 closeout — part 1

Owner: Asrın Dündar (Asperant). Date: 24 October 2026.
Branch: `wp/WP-CORE-004-temporal-genealogy`.
Implemented product head reviewed: `342ca511c698ee9c217c0973cd6802c115ba3e32`.
This document belongs to its containing closeout commit. It reconciles existing
engineering evidence, not Plane state or acceptance/readiness certification.

## Completed slices and evidence bindings

| Capability | Implementation commit | Retained evidence | Focused result recorded at that revision |
|---|---|---|---|
| Immutable directive-linked rework history model | `5a858a9facf3b384f8cd3af74be923fad63166e5` | [SLICE1.md](SLICE1.md) | 23 model tests passed |
| Append-only relational rework persistence | `d82b74f2a8f75748b90d5179042152b731f6b35a` | [SLICE2.md](SLICE2.md) | 24 PostgreSQL tests passed |
| Immutable split/merge temporal lineage model | `e0da2ec387d5ccfee428dd147028fcd851446b71` | [SLICE3.md](SLICE3.md) | 38 model tests passed |
| Relational split/merge lineage persistence | `6c140b8ad7f2ce89c1ecbc6dca18595d0b9201b1` | [SLICE4.md](SLICE4.md) | 30 PostgreSQL tests passed |
| Stored genealogy and equipment exposure query interface | `342ca511c698ee9c217c0973cd6802c115ba3e32` | [GENEALOGY-QUERIES.md](GENEALOGY-QUERIES.md) | 24 PostgreSQL tests passed; bounded synthetic WP-NORMAL sanity recorded |

These are separate historical focused runs, not a newly executed combined suite
or a current-head CI pass. Each source record retains its environment, exact
commands, limitations, negative paths and static/canonical check results. No
historical evidence is deleted or promoted to final accepted evidence. Earlier
start/transition-denial records remain historical only, not current blocker truth.

FR-CORE-009 is partially realized by rework values/history persistence;
`ExecuteApprovedReworkDirective` is not implemented. FR-CORE-010/011 have model,
persistence and ancestry reads; FR-CORE-012 has stored component/lot history and
actual equipment/time exposure reads. RTM references identify those actual files.
Coverage stays ALLOCATED; final evidence stays NOT_YET_EXECUTED. No accepted
EvidenceID, full-WP completion, current-head CI, real producer integration or
post-merge validation is claimed.

## Exact remaining blocked requirement

`ExecuteApprovedReworkDirective` is blocked by missing authoritative approval
lookup, lifecycle transition interface, and frozen protected-command contract.

Concrete missing bindings on this branch:

- No authoritative pre-execution approved-directive source or approval verifier
  exists. The persisted `approval_state`/`policy_state` strings are historical
  provenance, not authenticated approval or authorization. The current repository
  inserts directive snapshots as part of an already-supplied execution segment;
  it is not an approved-but-unexecuted directive registry.
- `SerializedComponent` has identity/revision/lot reference but no manufacturing
  lifecycle state or transition interface to validate and atomically apply legal
  rework execution. Core's Plane transition tooling is not such an interface.
- No frozen `ExecuteApprovedReworkDirective` protected-command contract binds
  target, actor, WorldID, proposal/plan version, state revision, expiry, policy and
  idempotency. The normative final reconciliation in
  `docs/01_Master_Project_Specification.md`, "One identity per protected action",
  requires those bindings to be frozen in the applicable contract WP before
  protected execution. Existing BFF command routing does not define them.

The previous statement that this gap was currently owner-executable is corrected:
it is an unimplemented product requirement with missing prerequisite bindings,
not another independently executable history/query slice. There is no verified
owner-executable remainder on the inspected branch while those bindings are
absent. This does not cancel or complete the requirement, declare another WP DONE,
certify readiness or manufacture a new canonical dependency edge. Existing
DEP-029 integration requirements and broader real-lineage/acceptance evidence
remain unproven. Producer/contract work must supply the actual bindings before
this command can be implemented without inventing approval/lifecycle semantics.

## Branch verification and part 1 boundary

Compared with fetched `origin/main` at
`471a9b19dbd1319727443cee4f50215a371af716`, the reviewed branch contains seven
WP-CORE-004 workstream commits: two start/denial evidence commits and five product
slice commits. The product diff is confined to manufacturing-core, its focused
tests/runbook, this WP's evidence and FR-CORE-009…012 realization references.
There are no control-plane, other-WP, approval-binding or lifecycle changes.
`git merge-tree --write-tree origin/main HEAD` reported no conflict before the
closeout documentation change. Local product HEAD matched the remote WP branch.
The containing closeout commit changes only evidence/trace/runbook documentation.

Only whitespace, canonical-document validation and read-only branch/PR checks
are performed for part 1. Broad tests are not run; earlier focused results are
not rerun or relabeled. A normal non-draft development PR carries the implemented
scope and this exact open blocker. Opening it is not MERGE_READY or DONE. CI is
not awaited. Plane/lifecycle, AUTO_NEXT, protected bindings and the two existing
untracked Asrın audit files remain untouched.
