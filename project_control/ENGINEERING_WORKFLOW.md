# Engineering workflow (CTRL-PM-012)

Use individual developer clones and Git identities. Branches: `wp/<WP-ID>-<short-slug>` for canonical work, `control/<CTRL-ID>-<short-slug>` for approved setup. PR titles: `[WP-...] title` or `[CTRL-...] title`. The existing setup program uses its explicitly approved long-lived `setup/project-management-bootstrap` branch. Retrieve canonical WP context before implementation; control scope comes from the master execution specification.

Use the PR template to declare requirements, architecture surfaces, change class, review risk class, tests, negative paths, evidence, docs/trace impact and Plane references. Review and merge rules remain those in docs/01 Items 63–64, docs/08 and docs/09; all development human approval counts are zero; review is advisory for every class (CHG-018). Real CI/tests/canonical/scope/evidence gates remain mandatory. Unknown identities are not fabricated into CODEOWNERS.

The projectctl workflow runs actual existing tests, offline canonical validation, syntax compilation, whitespace checks and tracked-path hygiene. It makes no product test or evidence certification claim. Pull-request workflows receive read-only contents permissions and no Plane credentials. All required technical/canonical checks must pass before merge; review states are not gates; never bypass failed checks, retry until green or merge setup solely for demonstration.

GitHub currently returns HTTP 403 for main branch protection: “Upgrade to GitHub Pro or make this repository public to enable this feature.” Repository is private and authenticated permissions include admin. Protection is unavailable under the current plan; repository visibility is not changed. A human must enable a supported plan/protection mechanism and configure required technical checks, no required approving reviews (all classes 0). Until then the technical governance remains mandatory; manual review is advisory; this is an enforcement limitation, not permission to bypass it.

GitHub owns code/PR/review/evidence. Plane owns execution coordination. docs/ owns canonical semantics. projectctl validates deterministic projections. No GitHub project board is created. Merged != Done: post-merge validation and applicable actual DoD evidence are required before closure.


## AUTO_NEXT — CHG-019 / CTRL-HOST-004 (22 October 2026)

Canonical planning preference lives in `project_control/execution_preferences.yaml`.
Every scheduled owned WP appears exactly once; the five unscheduled WPs stay outside.
Earlier milestone/window comes first, then canonical security/data-integrity,
cross-owner enabling and milestone work, then primary work; the owner's roadmap
section 9 order is the explicit final planning tie-breaker. Current broken-main or
security incidents are not invented from titles; actual repair remains governed
by the Task Priority Rule. This artifact is priority only, never readiness/evidence.

AUTO_NEXT scans preference and skips ineligible work with precise reasons. It uses
canonical node readiness and HARD START gates, not producer-WP DONE. Later-stage
HARD gates retain their actual stage; SOFT gaps are visible. UNKNOWN is not PASS.
Existing attributable current-revision DoR/dependency assessments and exact artifacts
are required; automation never generates confirmations or certifies from planning.

Any READY, IN_PROGRESS, IN_REVIEW, MERGE_READY, MERGED or VALIDATING work prevents
automatic release of another READY. BLOCKED active work is surfaced. This conservative
automatic-release policy does not change the global implementation WIP doctrine.
After VERIFIED DONE, the owner and canonical node consumers are evaluated under the
shared lock. Only BACKLOG -> READY may be automatically written, through the existing
transition evaluator, durable INTENT, one PATCH and fresh verified readback. External
writer races fail closed and require recomputation; timeout is never blindly retried.
No assignment, cycle, module, label, title, description or dependency backfill occurs.

Run `cap-plane-queue` in the real account/profile. JSON compatibility is retained;
`display_status` explains CURRENT/READY/NO_TASK/BLOCKED. NO_TASK includes fresh
eligibility reasons; never choose BACKLOG yourself. `projectctl next` remains
planning-only. Recovery: `cap-plane-advance` for own profile; root administration:
`sudo cap-plane-advance --all`. Both use the same resolver and guards. Offline
`projectctl execution-preferences` validates coverage; `queue-preview` reads explicit
live/evidence snapshots and never authorizes or performs a transition.

Separate Linux accounts asrin/selman/batuhan/yavuz and private workspaces/profiles
are authoritative. The helper drops GitHub reads to the matching account; root-only
installed code/policy is used, never writable repository imports. CAP_PROFILE must
match the real sudo caller. Historical shared-ailab descriptions are superseded for
this workflow; no workspace permissions, SSH or profile paths are changed.
CHG-018 zero-development-approval policy remains; product HITL stays unchanged.

Deploy only merged reference source. The dedicated AUTO_NEXT installer creates a
root-only timestamped `/root` backup and rollback script before replacing helper
files, refreshes source/helper hashes, verifies sudoers and preserves audit. Rollback
restores deployment only; never replay a stale Plane DB or state snapshot. No service
restart is required. Missing evidence results in NO_TASK, never synthetic READY.


### Lifecycle reconciliation of merged work — CHG-031 (proposed, UNDER_REVIEW)

When a work package's PR really merged but Plane was never advanced, `cap-plane-reconcile <WP-ID> <MERGED|VALIDATING>` can record the current observed fact. It is not a general bypass: only cases allow-listed in `project_control/lifecycle_reconciliation.yaml` work, for the named profile, WP, PR, head, merge commit and parents. Evidence is exactly `pr:N` (plus the policy's `run:N` refs for VALIDATING). The helper re-proves the merge, the complete file scope and the started main runs live, writes a durable INTENT audit row, performs one state PATCH and reads it back; a lost response is read back, never blindly retried. It does not fabricate skipped history, set DONE, clear BLOCKED, call AUTO_NEXT or touch other work, and it is not DoR/DoD or acceptance evidence. Installing it on the host and each live application are separately authorized steps.
