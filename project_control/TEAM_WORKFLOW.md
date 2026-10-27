# Team workflow — CTRL-PM-011

Historical setup snapshot (superseded by later closure evidence; development review is advisory under CHG-018): CTRL-PM-011 COMPLETE — all four real team identities have active Plane workspace/CAP memberships, verified GitHub access, separate clean clones/profiles and repository-local Git identities. All 179 canonical WPs are assigned to their owners (73/17/32/57) and remain BACKLOG. CTRL-PM-015 remains IN_PROGRESS; its separate control-only pilot is IN_REVIEW and the actual final closure PR is #3; independent review, merge and post-merge validation remain outstanding.

Use one persistent Ubuntu GUI session, `ailab`, with RustDesk attached. Do not create GUI users or switch Ubuntu login sessions. `/srv/ailab/project` is the integration/reference clone and must not be used concurrently for developer work.

| Developer | GitHub | Repository-local commit email | Workspace | Profile |
|---|---|---|---|---|
| Asrın Dündar | Asperant | asrindundar14@hotmail.com (existing verified identity) | /srv/ailab/workspaces/asrin/project | /srv/ailab/user-profiles/asrin |
| Selman Özdemir | selorito | selmanozdemir430@gmail.com | /srv/ailab/workspaces/selman/project | /srv/ailab/user-profiles/selman |
| Batuhan Kaya | Ejlonn | batuhankaya0204@gmail.com | /srv/ailab/workspaces/batuhan/project | /srv/ailab/user-profiles/batuhan |
| Yavuz Gümüş | Yavuzgmus | yavuzzgumus@gmail.com | /srv/ailab/workspaces/yavuz/project | /srv/ailab/user-profiles/yavuz |

Yavuz’s current operational identity is **Yavuz Gümüş**, Plane email **yavuzzgumus@gmail.com**, GitHub **Yavuzgmus**, and Git commit email **yavuzzgumus@gmail.com**. His real Plane account `3ccd9ad8-99e9-4b75-ae65-2325503d347f` is an active workspace/CAP MEMBER (15), with all 57 canonical Yavuz WPs assigned and still BACKLOG. No pending Yavuz invitation remains. The earlier wrong-address invitation was revoked. Historical invitation/workspace snapshots retain their original observations; see the source-bound CTRL-PM-011-yavuz-closure evidence.

Batuhan’s current operational identity is **Batuhan Kaya**, Plane email and Git commit email **batuhankaya0204@gmail.com**, Plane user ID **51137169-2989-42bd-9260-997b26e7e6dd**, GitHub **Ejlonn**. The earlier `eilonn` binding was incorrect and identifies a different account; historical snapshots are retained as history. His workspace/project memberships are active MEMBER (15), and he personally confirmed remote CAP project visibility. His genuine approval on `ee32f2c` remains historical evidence of that revision. Under CHG-018 no new-head human approval is required; actual current-head technical checks remain mandatory.

All four independent clones were prepared from the integrated `main` baseline, with origin set to the canonical GitHub repository, repository-local names/emails and no copied credentials. They will need a normal fetch after individual authentication to receive setup updates. They are not authenticated merely because a clone exists.

## Onboarding

Replace `selman` with your own profile key (`asrin`, `selman`, `batuhan`, `yavuz`):

```sh
python /srv/ailab/project/tools/operations/developer_workspace.py shell selman
git config --local --get-regexp '^user\.'
gh auth login --hostname github.com --git-protocol https
gh api user --jq .login
```

Verify the returned account equals the table before any fetch/push/review. Accept your own GitHub invitation. Configure your own Codex/OpenAI account only within this profile; never copy integration-session credentials. Quit this shell when finished. Use the same launcher for every Git/GitHub command; a terminal outside it may inherit shared-session authentication.

```sh
python /srv/ailab/project/tools/operations/developer_workspace.py code selman
```

This opens VS Code with separate user-data and extension directories. Authenticate extensions individually and verify their account before use. The launcher separates GH_CONFIG_DIR, CODEX_HOME, XDG_CONFIG_HOME and VS Code data, disables global/system Git configuration and removes inherited GitHub/OpenAI/Plane token variables and SSH-agent references. Separate profile directories in the same Linux account are operational isolation, not a security boundary against other processes running as `ailab` or a guarantee about extension/keyring behavior.

Log into Plane yourself using the supplied invitation email. API invitation records were created and read back; email delivery was not proven. If no invitation is visible after login, ask the workspace owner to use Plane's normal invitation UI; do not fabricate membership or copy invitation tokens. After workspace acceptance, an owner must verify active membership and add the real account to Graduation Project/CAP with MEMBER permission. WPs stay unassigned until project membership resolves. Repository invitation acceptance is also personal.

After authentication, fetch the remote normally, inspect its baseline, and use an existing local environment or install the documented projectctl dependencies in your own clone. Run `projectctl validate`, retrieve `projectctl context <WP-ID>`, check readiness, and create `wp/<WP-ID>-<short-slug>` only for an approved canonical WP. Product implementation has not been authorized by setup. Use `control/<CTRL-ID>-<short-slug>` for approved controls; the long-lived setup branch is the approved exception.

Canonical owners never change to compensate for missing accounts. No dummy users, substituted owners, shared tokens, global Git identity, automatic READY/DONE, self-approval or shared concurrent working tree. See ENGINEERING_WORKFLOW.md and canonical docs/08 for review and post-merge evidence rules.


Selman’s verified operational identity is **Selman Özdemir**, Plane/Git commit email **selmanozdemir430@gmail.com**, GitHub **selorito**, Plane user **a3d25336-e7d0-43f8-bfef-c0b5c2137a60**. Fresh API v1 reads confirm active workspace and CAP MEMBER (15), all 17 canonical Selman WPs assigned and BACKLOG, and no pending invitation. GitHub WRITE access is active. The account profile currently has first name Selman and an empty last name: these assignments bind the verified exact email/user UUID rather than guessing from display names. Historical pending observations remain preserved.


## Final advisory development review policy — CHG-018, 15 October 2026

Policy ID: `DEV-REVIEW-2026-10-15-FINAL`. CHG-018 explicitly supersedes CHG-017; CHG-017 and its intermediate 0/2 decision remain historical, unchanged. Active companion: `09_change/development_review_policy.json`; previous companion archived under `09_change/history/CHG-017-development_review_policy.json`.

| Policy ID | Scope | Required human approvals |
|---|---|---|
| DEV-REVIEW-2026-10-15-FINAL | ALL_DEVELOPMENT | 0 |

Every repository development PR, CR-0 through CR-4, normal/high risk, security/auth, protected-action-authority code, destructive migration, secrets/infrastructure, authority boundaries, platform, tooling, docs, product and research implementation has zero required human approvals. Review, requests, comments, suggestions and security advice are ADVISORY. No independent/qualified reviewer quota, self-approval rule, owner override, current-head approval or stale-approval mechanism governs development workflow. GitHub APPROVED, CHANGES_REQUESTED, COMMENTED and DISMISSED are not workflow, merge or DONE gates, and reviewer presence/absence never blocks progress. CODEOWNERS and supporting-reviewer metadata are advisory routing/domain context only.

IN_REVIEW means a real non-draft technically reviewable PR, not waiting for a human. MERGE_READY requires correct canonical WP/approved control scope and branch/PR/head binding, required actual CI/tests/canonical validation, mergeability/no conflict against current main, no out-of-scope changes, applicable DoR-PR/PR DoD, trace/evidence and applicable security/secret/static checks, and no real BLOCKED condition. Actual technical/canonical failures or ambiguity fail closed; a review state alone neither proves nor disproves these facts. Material revisions re-run technical checks/evidence. Rework follows actual revision/technical evidence, not approval invalidation.

MERGED requires an actual GitHub merge. VALIDATING requires actual post-merge validation started. DONE requires all applicable DoD, trace/evidence and actual successful post-merge validation; accountable owner assessment and real artifacts remain required, another person's review/confirmation does not. Development peer/methodology review is advisory even for closure; real protocol, scientific reproducibility, measured acceptance and product-authority evidence remain required. Merged != Done; Implemented != Tested; Tested != Verified; Demoed != Accepted.

This changes ONLY development/GitHub/repository governance. Product HITL, protected-action approval, AuthorityPolicy, authenticated approvers, runtime self-approval prohibition, exact proposal/plan binding and execution authorization are unchanged. Project-owner scope/cancellation decisions and real product acceptance artifacts are not GitHub review approvals and are not fabricated or waived. No Plane test mutation, merge, commit or push is authorized in this pass. Existing historical approvals remain history, never requirements for a current transition.


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

Verified MERGED contract publication and verified UNBLOCKED resolution also trigger the same guarded affected-owner reevaluation; they never imply DONE. A completed transition remains VERIFIED even if subsequent advance needs recovery.


### Lifecycle reconciliation of merged work — CHG-031 (proposed, UNDER_REVIEW)

When a work package's PR really merged but Plane was never advanced, `cap-plane-reconcile <WP-ID> <MERGED|VALIDATING>` can record the current observed fact. It is not a general bypass: only cases allow-listed in `project_control/lifecycle_reconciliation.yaml` work, for the named profile, WP, PR, head, merge commit and parents. Evidence is exactly `pr:N` (plus the policy's `run:N` refs for VALIDATING). The helper re-proves the merge, the complete file scope and the started main runs live, writes a durable INTENT audit row, performs one state PATCH and reads it back; a lost response is read back, never blindly retried. It does not fabricate skipped history, set DONE, clear BLOCKED, call AUTO_NEXT or touch other work, and it is not DoR/DoD or acceptance evidence. Installing it on the host and each live application are separately authorized steps.

### CHG-054 / CTRL-HOST-031 — advisory product execution

The earlier queue/Slot Release scheduling text is historical diagnostic behavior
for product start. Product implementation uses the canonical WP context and
`projectctl startability <WP-ID>`: exact owner, exact scope and no unresolved
`HARD + START` dependency. Plane/queue availability, READY/DoR, proof/cache and
audit continuity do not authorize or deny the start. `cap-plane-queue` is
read-only advisory output; external/downstream BLOCKED work does not consume a
developer's ability to select another WP. MERGE_READY and DONE safeguards remain
unchanged and fail-closed.
