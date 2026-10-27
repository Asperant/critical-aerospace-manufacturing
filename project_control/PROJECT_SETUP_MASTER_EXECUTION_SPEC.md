# PROJECT SETUP MASTER EXECUTION SPECIFICATION

**Control Program:** PROJECT-SETUP<br>
**Repository:** `Asperant/critical-aerospace-manufacturing`<br>
**Local canonical clone:** `/srv/ailab/project`<br>
**Intended repository location:** `project_control/PROJECT_SETUP_MASTER_EXECUTION_SPEC.md`<br>
**Status:** EXECUTION SPECIFICATION

## 1. Mission

This document defines the remaining setup program for **Kritik Havacılık ve Uzay Komponentleri için Akıllı Üretim Operasyon Platformu / Intelligent Manufacturing Operations Platform for Critical Aerospace Components**.

The program must complete project-control validation, Plane integration, GitHub workflow, team operating discipline, backup/recovery, and a governed pilot workflow before product implementation begins.

This document is not a product specification and does not replace the canonical material under `docs/`.

The authority boundary is:

- `docs/` = canonical specification and governance truth.
- GitHub = code, PR, review, engineering-work, and evidence truth.
- Plane = execution planning, coordination, and status view.
- `projectctl` = deterministic validation and synchronization bridge.

Plane or projectctl must never redefine canonical semantics.

## 2. Governing authority

Before any edit, read and obey:

1. `AGENTS.md`
2. `docs/01_Master_Project_Specification.md`
3. `docs/02_System_Architecture_Specification.md`
4. stable IDs/invariants/schemas/contracts
5. `docs/03_Requirements_Traceability_Matrix.md`
6. `docs/04_Work_Breakdown_Structure.md`
7. `docs/05_Dependency_Graph.md`
8. `docs/06A_Asrin_Engineering_Roadmap.md`
9. `docs/06B_Selman_Engineering_Roadmap.md`
10. `docs/06C_Batu_Engineering_Roadmap.md`
11. `docs/06D_Yavuz_Engineering_Roadmap.md`
12. `docs/07_Milestone_and_Release_Plan.md`
13. `docs/08_Definition_of_Ready_and_Done.md`
14. `docs/09_Change_Control_Process.md`
15. `docs/10_Pre_Implementation_Red_Team_Review.md`
16. `docs/00_Downstream_Artifact_Production_Guide.md`

Source precedence:

`01 → 02 → stable IDs/invariants/contracts → 03 → 04–07 → 08 → 09 → 10 → 00`

Precedence identifies governing authority. It does not authorize silent conflict resolution.

## 3. Absolute rules

### 3.1 Canonical docs are read-only during this setup program

Do not modify anything under `docs/`.

Known inconsistencies remain diagnostics/findings for later reconciliation. Do not silently repair them.

### 3.2 Stable IDs are authoritative

The canonical project contains **179 Work Packages**. Plane IDs such as `CAP-42` are local references only. Canonical IDs such as `WP-CORE-001` must remain visible and stable.

### 3.3 Do not manufacture expected values

Expected counts are assertions to verify, never parsing limits or targets to force. If observed values differ, fail the affected control item.

### 3.4 Planning state is not execution state

Do not infer:

- `NOT_STARTED` ⇒ Plane `BACKLOG`
- merged ⇒ DONE
- tested ⇒ VERIFIED
- demoed ⇒ ACCEPTED
- milestone target ⇒ milestone PASS

Canonical workflow:

`BACKLOG → READY → IN_PROGRESS → IN_REVIEW → MERGE_READY → MERGED → VALIDATING → DONE`

`CANCELED` is terminal. `BLOCKED` is orthogonal and must remain a label/condition, not a workflow state.

### 3.5 Human-governed acceptance

Do not automatically certify READY, DONE, VERIFIED, milestone PASS, change approval, or evidence acceptance unless an explicit deterministic checker has the required real execution evidence.

### 3.6 Secret handling

Never commit passwords, tokens, Plane credentials, GitHub tokens, database passwords, SSH keys, SMTP credentials, or Keycloak secrets. Use ignored local config or environment variables.

### 3.7 Technology restraint

Do not add Kubernetes, Neo4j, another database, another broker, or another PM system.

For projectctl/setup work prefer Python, Typer, Pydantic, PyYAML, Rich, and the standard library. Add `httpx` only when live Plane integration is reached.

### 3.8 Git discipline

Do not work directly on `main`. Use a setup branch or per-control-item branch. Each completed control item requires passing tests, passing validation, clean `git diff --check`, and no unintended canonical-doc changes.

### 3.9 Plane mutation discipline

Before a live Plane mutation:

1. verify workspace/project identity,
2. verify authentication,
3. run a deterministic dry-run,
4. prove idempotency strategy,
5. show mutation preview,
6. stop for explicit approval before first live mutation.

Never delete Plane entities automatically.

## 4. Baseline invariants

### Requirements

- total: **306**
- FR: **186**
  - F0: 17
  - F1: 159
  - R1: 10
- NFR: **120**
  - H0: 52
  - A1: 41
  - S2: 23
  - C3: 4

### Work Packages

- canonical WPs: **179**
- Asrın Dündar: **73**
- Selman Özdemir: **17**
- Batuhan Kaya: **32**
- Yavuz Gümüş: **57**
- capability areas: **29**

### Dependency graph

- nodes: **100**
- edges: **217**
- HARD: **208**
- SOFT: **9**
- HARD cycles: **0**

### Schedule

- scheduled WPs: **174**
- unscheduled WPs: **5**
- exact unscheduled IDs:
  - `WP-R2-001`
  - `WP-R2-002`
  - `WP-R2-003`
  - `WP-S-001`
  - `WP-X-001`
- cycles: `S1` through `S13`
- milestones: `M0` through `M8`

## 5. Preflight

At execution start:

1. inspect current branch,
2. inspect `git status`,
3. inspect latest commits,
4. verify CTRL-PM-001 is integrated into the active baseline,
5. activate `.venv`,
6. run current projectctl tests,
7. run `projectctl validate`,
8. confirm `docs/` has no uncommitted changes,
9. determine the first incomplete control item.

If CTRL-PM-001 is not integrated, stop with:

`BLOCKED_FOR_HUMAN: CTRL-PM-001 baseline not integrated`

Do not duplicate CTRL-PM-001.

# 6. Control program

## CTRL-PM-002 — Schedule, Cycle, and Milestone Model

Goal: extend projectctl so it parses and cross-checks schedule data deterministically.

Primary source:

- `docs/07_Milestone_and_Release_Plan.md`

Cross-check:

- `docs/04_Work_Breakdown_Structure.md`
- `docs/06A_Asrin_Engineering_Roadmap.md`
- `docs/06B_Selman_Engineering_Roadmap.md`
- `docs/06C_Batu_Engineering_Roadmap.md`
- `docs/06D_Yavuz_Engineering_Roadmap.md`
- relevant semantics in 01

Add minimal normalized models:

- `Cycle`
- `Milestone`
- `ScheduleProjection`

Preserve source provenance.

Validate:

- S1–S13 exactly
- 13 cycles
- two-effective-week cadence
- M0–M8 exactly
- 9 milestones
- 174 scheduled WPs
- exact 5 unscheduled WPs
- no duplicate scheduled identity
- owner roadmap membership agrees with WBS owner
- cycle membership agrees between 06A–D and 07
- WBS milestone references resolve
- schedule metadata never becomes execution state

Extend `projectctl validate` and `projectctl status`. Optional read-only `projectctl schedule` is allowed.

Acceptance: all prior tests plus new schedule tests pass.

## CTRL-PM-003 — Dependency Graph Parser and Validator

Goal: parse and validate `docs/05_Dependency_Graph.md` without runtime state.

Add:

- `DependencyNode`
- `DependencyEdge`
- typed readiness/strength/kind/stage representations where source-supported

Validate:

- 100 nodes
- 217 edges
- 208 HARD
- 9 SOFT
- 0 HARD cycles
- endpoints exist
- duplicate node/edge IDs fail
- HARD cycles return a concrete witness
- SOFT edges never become blocking
- endpoint owner assertions agree with registry
- readiness-level incompatibilities are surfaced
- ambiguous need-by values remain ambiguous
- missing precision is surfaced, never invented

Known findings must remain visible. Do not repair readiness-ladder mismatches, precision gaps, or fixture-semantic findings.

Use standard-library graph traversal unless a real technical need justifies another dependency. Do not add NetworkX merely for convenience.

## CTRL-PM-004 — Requirement and RTM Parser

Goal: parse the canonical requirement catalog and cross-check traceability.

Primary requirement authority:

- `docs/01_Master_Project_Specification.md`

Traceability projection:

- `docs/03_Requirements_Traceability_Matrix.md`

Cross-check:

- `docs/04_Work_Breakdown_Structure.md`

Add:

- `Requirement`
- requirement kind
- FR scope class
- NFR quality class
- source-supported verification/evidence metadata
- `TraceOverlay`

Validate:

- 306 total
- 186 FR
- 120 NFR
- FR: 17 F0 / 159 F1 / 10 R1
- NFR: 52 H0 / 41 A1 / 23 S2 / 4 C3
- no duplicate canonical IDs
- every WBS requirement reference resolves
- RTM class/owner assertions match canonical requirement records
- missing fields remain missing
- stale citations become diagnostics, not edits

Do not reinterpret external datasets. Existing SECOM/WM-811K migration defects remain findings for later documentation reconciliation.

## CTRL-PM-005 — Unified Offline Project Model

Goal: combine WBS, schedule, dependency, and requirement models into one deterministic offline project model.

Required commands:

- `projectctl parse`
- `projectctl validate`
- `projectctl status`
- `projectctl context <WP-ID>`
- `projectctl next --owner <owner> [--cycle <cycle>]`

`context` must show canonical identity, capability area, owner/reviewers, requirements, architecture refs, dependency/readiness refs, cycle, milestone, DoR/DoD refs, verification/evidence expectations, conflicts, and provenance.

`next` is planning-only. It never certifies READY. Label results as candidates. Do not silently select unscheduled or optional work.

A single `projectctl validate` must cover the full baseline and return nonzero on canonical invariant failure.

## CTRL-PM-006 — Plane Read-Only Adapter

Goal: connect projectctl to Plane without mutation.

Only now may `httpx` be added if required.

Plane config must come from environment variables or ignored local config. Never commit secrets.

Read-only discovery should cover, where API supports it:

- workspace
- project
- states
- labels
- modules
- cycles
- work items
- members/users

No POST/PUT/PATCH/DELETE in this control item. Tests must prove read-only behavior.

If credentials or exact workspace/project identifiers are missing, stop with:

`BLOCKED_FOR_HUMAN: PLANE_READ_CREDENTIALS_REQUIRED`

State exactly what local value is needed and where to store it. Do not request that secrets be committed.

## CTRL-PM-007 — Plane Bootstrap Dry-Run Planner

Goal: compute desired Plane state without mutation.

Desired structures:

- 29 Modules, one per capability area
- Cycles S1–S13
- milestone labels `MS:M0` through `MS:M8`
- 179 canonical WP work items

Do not depend on paid/native milestone features.

Each intended WP must preserve:

- canonical WP ID
- title
- owner mapping
- module
- cycle when scheduled
- milestone metadata
- initialization policy
- auditable canonical metadata

All imported WPs initially map to `BACKLOG`. No automatic READY.

Dry-run output must categorize:

- create
- update
- unchanged
- conflict
- ambiguous mapping
- missing owner
- duplicate canonical ID

Logical identity is canonical WP ID, never title-only matching.

## CTRL-PM-008 — Plane Structural Bootstrap

Goal: idempotently create only missing non-WP project structures.

Allowed live mutations after approval:

- 29 modules
- S1–S13 cycles
- `MS:M0` … `MS:M8` labels
- required stable control labels
- verify/preserve `BLOCKED`

Never auto-delete.

Before first live mutation, show the complete mutation preview and stop with:

`HUMAN_APPROVAL_REQUIRED: FIRST_PLANE_MUTATION`

After explicit human approval, resume from this control item and execute idempotently.

Re-read Plane and audit exact resulting structures.

## CTRL-PM-009 — 180 WP Idempotent Plane Import

Goal: import all canonical WPs exactly once.

Rules:

- 180 canonical WPs
- a missing WP is created in BACKLOG; an existing valid Plane lifecycle state is preserved
- no automatic READY
- canonical WP ID visibly preserved
- assign owner only when correct Plane member exists
- assign module from capability area
- assign cycle for 174 scheduled WPs
- exact five unscheduled WPs remain without cycle
- apply milestone metadata where applicable
- do not create 306 requirements as ordinary work items
- do not create dependency nodes as ordinary work items
- do not blindly convert all 217 edges into Plane blockers

If an owner is not a Plane member, do not assign to a wrong person. Preserve canonical owner metadata and report the missing membership.

Run import twice. Second run must create zero duplicates and zero static semantic drift; intentionally preserved valid lifecycle-state differences are reported, not reset.

CHG-049 / CTRL-PM-016 defines the generic reconciliation rule for this import:
canonical owner binding, milestone labels and structured planning metadata on
owned `projectctl` issues may be repaired by an exact allowlisted PATCH plus fresh
read-back. Identity, parent, relationship and unknown-state conflicts remain
fail-closed. Registered control-only items, including
`CTRL-PM-015-PILOT-001`, remain separate and are never deleted.

CHG-050 / CTRL-PM-017 defines the generic relationship reconciliation rule:
canonical module and coordination-cycle memberships are read from the full live
inventory. For an existing WP, non-target canonical associations may be removed
only through the exact association endpoint and only when the canonical target
is deterministic; the target is then added if absent. Unscheduled WPs have no
cycle association. Each association mutation requires a fresh relationship
read-back. Plane issues, workflow state, control-item membership and lifecycle
transitions are never changed by this rule. Unknown relationship entities,
duplicate relationship evidence, identity/parent/state conflicts and ambiguous
read-backs remain fail-closed.

CHG-053 / CTRL-PM-018 restores the approved operational Plane projection:
every canonical WP is assigned to its verified canonical owner member, while
queue selection remains profile-scoped and never treats assignment as a global
queue filter. Every scheduled WP receives exactly one Plane cycle using the
first cycle in its canonical ordered window; the full window remains in
metadata and the five unscheduled WPs remain cycleless. Terminal-cycle
selection is not used. Lifecycle state, BLOCKED projection, Slot Release
proofs, module/milestone membership, control items and product WP state are
never changed by this rule.

## CTRL-PM-010 — Plane Post-Import Audit

Goal: prove Plane matches canonical planning data.

Assert:

- 180 canonical WP identities
- 29 modules
- 13 cycles
- S1–S13
- 174 scheduled / 5 unscheduled
- exact five unscheduled IDs
- milestone metadata M0–M8
- no automatic READY
- no duplicate canonical IDs
- canonical owner metadata remains 73 / 17 / 32 / 57

Produce a machine-readable audit to stdout. Do not create a second persistent PM database.

## CTRL-PM-011 — Team Identity and Clone Discipline

Goal: prepare safe multi-developer operation.

No shared Git identity and no four-person use of one working tree.

Preferred model:

- `/srv/ailab/project` = integration/reference clone
- separate developer clones for active developers
- separate Linux users where practical

Required people:

- Asrın Dündar
- Selman Özdemir
- Batuhan Kaya
- Yavuz Gümüş

If Plane invitations require unknown email addresses, stop with:

`BLOCKED_FOR_HUMAN: TEAM_EMAILS_REQUIRED`

Request only missing addresses. Never invent them.

If GitHub collaborator usernames are required and unavailable, report exactly which usernames are needed.

## CTRL-PM-012 — GitHub Engineering Workflow

Goal: establish repository workflow without duplicating Plane.

Add a PR template requiring:

- WP/control ID
- summary
- requirements
- architecture surfaces
- change class
- tests
- negative paths
- evidence
- docs impact
- Plane reference where applicable

Branch conventions:

- WP: `wp/<WP-ID>-<short-slug>`
- control: `control/<CTRL-ID>-<short-slug>`

PR titles:

- `[WP-...] title`
- `[CTRL-...] title`

CI must minimally run:

- projectctl tests
- `projectctl validate`
- appropriate syntax/sanity checks
- repository hygiene checks

Do not fabricate product tests that do not exist yet.

Attempt branch protection only when supported by current permissions/account plan. If unavailable, report the limitation; do not weaken the rule semantically.

## CTRL-PM-013 — Governed Workflow Transition Support

Goal: support deterministic lifecycle transitions without making projectctl a second PM engine.

Lifecycle:

`BACKLOG → READY → IN_PROGRESS → IN_REVIEW → MERGE_READY → MERGED → VALIDATING → DONE`

Potential deterministic transitions:

- explicit implementation start → IN_PROGRESS
- real non-draft technically reviewable PR → IN_REVIEW; no reviewer/request required (CHG-018)
- required technical/canonical/test checks green → MERGE_READY; no review-state gate (CHG-018)
- merged PR → MERGED
- post-merge validation start → VALIDATING

Critical rule: MERGED does not imply DONE.

Implement:

- `projectctl check-ready <WP-ID>`
- `projectctl check-done <WP-ID>`

Allowed results:

- PASS
- FAIL
- UNKNOWN

Fail closed. If execution/evidence data is unavailable, return UNKNOWN. Never infer evidence from planned verification prose.

## CTRL-PM-014 — Backup, Restore, and Host Operations

Goal: make Plane/project-control setup recoverable.

Establish and test Plane backup using `/srv/ailab/backups` or another approved local backup path.

A backup archive alone is insufficient. Perform safe restore verification where practical, preferably into a disposable target. Never overwrite the live instance without explicit approval.

Verify:

- disk availability
- Plane restart behavior
- Docker restart persistence
- backup integrity
- repository independence from Plane runtime

The secondary NVMe may later be mounted at a stable path such as `/srv/ailab/data`, but do not reformat or change partitions automatically. Persistent-mount changes are a human gate unless already configured safely.

Plane is not part of the product SUT and may be stopped during final benchmark runs if host contention would contaminate benchmark evidence.

## CTRL-PM-015 — End-to-End Setup Rehearsal

Goal: prove the governed development-management workflow before real product implementation.

Use a non-destructive setup/control pilot. Do not mark a canonical WP DONE merely for rehearsal unless its actual DoR/DoD and evidence are genuinely satisfied.

Rehearse:

1. item represented in Plane
2. canonical identity preserved
3. readiness evaluated
4. branch created
5. implementation change made
6. tests run
7. PR opened
8. real technical check state reflected; review is advisory (CHG-018)
9. merge reflected as MERGED
10. post-merge validation represented
11. DONE withheld until evidence exists
12. audit trail remains understandable

Acceptance must prove the tooling never collapses recommendation into execution, merge into done, planning into evidence, or Plane state into canonical semantics.

# 7. Plane mapping contract

## Modules

29 capability areas → 29 Plane Modules.

## Cycles

S1–S13 → Plane Cycles.

## Milestones

Use stable labels/metadata:

- `MS:M0`
- `MS:M1`
- `MS:M2`
- `MS:M3`
- `MS:M4`
- `MS:M5`
- `MS:M6`
- `MS:M7`
- `MS:M8`

## BLOCKED

`BLOCKED` remains a label/condition, not a workflow state.

## Requirements

306 requirements remain canonical references, not 306 ordinary Plane work items.

## Dependencies

217 dependency edges are not blindly mapped into Plane blocker links. The canonical graph remains a projectctl/document concern unless an operational projection is explicitly justified.

# 8. Generated-data policy

Generated projections must remain reproducible views, never hand-maintained canonical truth.

Do not create a local PM-state database.

Do not create copied registries that require manual synchronization with `docs/`.

Generated outputs should bind to source provenance and parser/schema version when applicable.

Default commands should write to stdout unless an explicit output path is requested.

# 9. Human gates

Codex should continue automatically unless one of the following occurs.

### H1 — Baseline not integrated

Stop if required prior setup is not on the active baseline.

### H2 — Plane credentials missing

Stop and request exact missing local config.

### H3 — First Plane live mutation

Show mutation preview and require explicit approval.

### H4 — Team identities missing

Request only missing email addresses or GitHub usernames.

### H5 — Destructive action

Any delete/reset/overwrite/format/destructive operation requires explicit approval.

### H6 — Canonical inconsistency blocks deterministic behavior

Report exact conflicting sources and values. Do not repair docs.

# 10. Branch and commit strategy

Preferred for the remaining setup program:

Use one long-lived branch:

`setup/project-management-bootstrap`

Create one atomic commit per control item:

- `[CTRL-PM-002] ...`
- `[CTRL-PM-003] ...`
- ...
- `[CTRL-PM-015] ...`

Push checkpoints when useful.

Do not mix product implementation into this branch.

Open a final review PR after all non-human-gated setup work is complete.

If repository policy or execution constraints make that unsafe, use one branch/PR per control item instead and report the reason.

# 11. Failure policy

If a control item fails:

1. do not weaken tests,
2. do not change expected invariants to match buggy output,
3. do not silently skip it,
4. do not continue into a dependent live-mutation step,
5. report the failed control item, command, exit code, diagnostic, files changed, repository state, rollback need, and recommended next action.

Read-only later analysis may continue only if it cannot contaminate state.

# 12. Required execution log per control item

Every completed control item must record:

- CONTROL ITEM
- GOAL
- FILES CHANGED
- TESTS RUN
- TEST RESULTS
- VALIDATION RESULT
- OBSERVED INVARIANTS
- PLANE READS
- PLANE MUTATIONS
- GITHUB MUTATIONS
- NETWORK MUTATIONS
- KNOWN LIMITATIONS
- SPEC CONFLICTS
- COMMIT SHA
- NEXT CONTROL ITEM

Do not claim completion when acceptance checks were not actually run.

# 13. Definition of Setup Complete

The setup program is complete only when all applicable items below are proven.

## projectctl

- 179 WPs parsed
- 306 requirements parsed
- 29 capability areas parsed
- 100 dependency nodes parsed
- 217 dependency edges parsed
- 208 HARD / 9 SOFT verified
- 0 HARD cycles verified
- 174 scheduled / 5 unscheduled verified
- exact five unscheduled IDs verified
- S1–S13 verified
- M0–M8 verified
- `context` works
- `status` works
- `validate` works
- `next` remains planning-only
- `check-ready` fails closed
- `check-done` fails closed

## Plane

- workspace identity verified
- project identity verified
- 29 modules
- 13 cycles
- milestone metadata M0–M8
- 179 canonical WP identities
- no duplicates
- imported WPs initially BACKLOG
- no automatic READY
- 174 scheduled WPs assigned to cycles
- exact 5 unscheduled remain unscheduled
- canonical owner metadata preserved
- BLOCKED remains orthogonal

## GitHub

- canonical repository baseline clean
- PR template present
- branch convention documented
- CI present
- projectctl tests run in CI
- projectctl validation runs in CI
- code/PR/evidence authority boundary preserved

## Team workflow

- separate identities defined
- shared-working-tree risk addressed
- developer clone strategy implemented/documented
- Plane membership completed or explicit human-owned outstanding invitations documented

## Governance

- Merged != Done enforced
- planning != evidence enforced
- no requirement/WP semantic drift introduced
- no canonical docs silently modified
- no secrets committed
- no second PM database created

## Operations

- Plane backup procedure exists
- backup executed
- restore verified safely, or a clearly documented human-owned outstanding gate remains
- host restart behavior checked
- SUT/Plane benchmark separation documented

## Rehearsal

- governed pilot workflow completed
- audit trail understandable
- no false DONE/VERIFIED state generated

Only then may Codex report:

`SETUP COMPLETE`

# 14. Final setup report

At the end produce:

### A. Executive result

`SETUP COMPLETE` or `SETUP INCOMPLETE`

### B. Control-item matrix

For CTRL-PM-002 through CTRL-PM-015:

- status
- commit
- tests
- mutations
- remaining human gates

### C. Canonical invariant report

Observed counts for requirements, WPs, owners, modules, nodes, edges, HARD/SOFT, hard cycles, scheduled/unscheduled, cycles, milestones.

### D. Plane audit

Exact observed counts, duplicate status, state initialization, membership gaps.

### E. GitHub audit

CI, templates, branch/policy state.

### F. Security audit

Confirm no secrets committed.

### G. Outstanding findings

Preserve unresolved documentation findings without falsely closing them.

### H. Next action

If complete:

`Ready to begin canonical product implementation using projectctl-governed Work Packages.`

If incomplete, state the single next blocking gate clearly.

# 15. Codex operating instruction

Codex is the implementation agent for this setup program.

It must:

- read before editing,
- preserve canonical boundaries,
- work deterministically,
- test every increment,
- use exact stable IDs,
- stop only at defined human gates or failed acceptance gates,
- avoid speculative architecture changes,
- avoid documentation repair,
- avoid Plane mutation before dry-run and approval,
- avoid secrets,
- leave the repository reviewable at every checkpoint.

Do not optimize for speed by weakening governance. Correctness, traceability, idempotency, and reversibility are more important than finishing quickly.
