# CTRL-HOST-003 / CHG-018 — Advisory-only development review

Authority: explicit newer final project-owner decision, 15 October 2026.
CHG-018 supersedes CHG-017. CHG-017.yaml remains byte-identical, SHA-256
`026adf87438dbee71be68d83100b7343963a70d8ab97ad9f14bd8a610f83de9a`.
The CHG-017 0/2 policy companion and canonical bindings are archived under
09_change/history; its earlier execution reports remain historical, not current policy.
Existing uncommitted CHG-017 work was preserved and extended, without reset/revert.

## Policy and boundaries

All development PRs, CR-0 through CR-4 and all risk classes, require zero human
approvals. Review is ADVISORY. No APPROVED/CHANGES_REQUESTED/DISMISSED state,
reviewer presence, qualified/independent quota, self-approval, owner override,
current-head approval or stale-approval mechanism gates workflow, merge or DONE.
CODEOWNERS/supporting reviewers remain advisory routing/domain context.
Actual DoR/DoD, security, research, trace and verification obligations remain.
Product runtime HITL, authenticated approver, runtime self-approval ban, exact
proposal/plan binding and execution authorization are unchanged.

MERGE_READY retains actual canonical WP/control scope, matching branch/PR/head,
non-draft status, current-head required CI/tests/canonical validation, complete
file scope, applicable security/secret/static checks, actual mergeability against
current main, applicable DoR-PR/PR DoD, trace/artifacts and absence of real BLOCKED.
CI evidence checks the actual head-bound Actions run/job and required steps;
a green job with a skipped/missing required technical step is insufficient.
Review-dependent aggregate mergeable_state is not treated as technical conflict.
Technical ambiguity remains fail-closed. DONE still requires actual full DoD,
trace/evidence and successful post-merge validation. All four workflow maxims remain.

The helper no longer queries reviews or computes approvals/overrides.
Real revision change drives technical rework; owner-attributed semantic readiness,
blocker/cancellation/DoD assessments and actual artifacts remain distinct from
peer review. Root credentials, exact sudo grants, canonical owner/Plane assignee,
fixed endpoints, minimal state/BLOCKED payload, fresh GET and audit are preserved.
The same-UID trusted-team operational guard is unchanged; no new session binding.

## Reconciliation and executed checks

Canonical docs01/02/08/09/10, migration history, AGENTS, CHG companions, PR template,
CODEOWNERS, setup/workflow/control-pilot runbooks, projectctl policy validation,
helper/builder, tests and README are reconciled. Historical records retain dates
and decisions. The accompanying file list includes preserved pre-existing edits.

- Full projectctl suite: 221 passed in 67.84s.
- Transition offline fixtures: 67 passed.
- Queue offline fixtures: 13 passed; queue source/installed bytes unchanged.
- projectctl validate --json: PASS; existing need-by ambiguity warnings retained.
- git diff --check: PASS.
- Root install: PASS, including dedicated/full sudoers syntax checks.
- Source manifest/helper hashes, credential root0600/directory0700, unchanged
  queue/audit and actual-key source/output/audit leakage scans: PASS.
- GET-only evaluator guard; execute/PATCH/audit writes disabled in live probe.
- A first read-only assessment exposed an obsolete ten-digit Actions run-ID limit.
  Bounded 18-digit run IDs are now accepted, regression-tested and installed.
  That failed assessment performed no mutation; final results below are fresh.

Canonical semantic projection before/after SHA-256 is unchanged:
`c18ba1bd9fb1c6d950609b039d62ff16ea0b2270cd5ebf55dc6b3e4cae8508a9`.
306 requirements (186 FR/120 NFR), 179 WPs, owners 73/17/32/57, 29 capabilities,
13 cycles, 9 milestones, 100 dependency nodes/217 edges (208 HARD/9 SOFT),
0 HARD cycles, 174 scheduled and the same five unscheduled WPs are preserved.
Offline execution status remains UNAVAILABLE (documentation only).

## Deployment and live read-only assessments

Prior CHG-017 deployed digest:
`06c5553369a65240fd38260836dd034f4ec464509d2907809a0daf3f30d4453b`.
Final CHG-018 installed digest:
`a862eabcef83103c96e3dacec415f102814a436165b72f0f0076beb11e091db9`.
The JSON also records the intermediate installation digest during run-ID repair.
Helper: /usr/local/libexec/cap-plane-transition.
Root policy: /etc/cap-plane-queue/transition-policy.json.
Public digest: /usr/local/share/cap-plane-transition/policy-manifest.json.

PR #7 head eb559a31c37a71759689a318313e495a377bad3c:
ELIGIBLE_READ_ONLY for IN_REVIEW → MERGE_READY under installed CHG-018.
Actual WP-GOV-001 state is IN_REVIEW. Full evaluator passes and a second GitHub
GET verifies unchanged PR/head facts. No Plane transition or merge performed.

PR #6 head 0caa66b4ef29ce1f71eca8b664a80df680ed04a1:
NOT_ELIGIBLE, DRAFT_PR. Actual current-head technical CI and main currency pass;
mergeable true. Full control-scope DoR/DoD is not certified on a draft PR.
Local CHG-017/018 edits are uncommitted and unpublished, so that PR does not yet
contain this migration. No fake canonical WP/control Plane write was introduced.

Fresh full Plane readback: 179 WPs, 177 BACKLOG, 1 READY, 1 IN_REVIEW,
0 IN_PROGRESS. Full sanitized queue snapshot digest before/after is identical:
`443396c691212871de4e2bd3d51e61052a7b6da38811cb329dc89118aaf4d6cb`.
All production Plane requests in this pass are GET; production mutations zero.

## GitHub protection limitation / exact manual settings

GET main/protection, repository rulesets and rules/branches/main all return 403:
“Upgrade to GitHub Pro or make this repository public to enable this feature.”
Actual protection/review settings therefore cannot be confirmed. No settings
mutation was attempted, no repository visibility/plan changed and no CI or
force-push/deletion protection was removed.

With adequate plan/access, inspect Settings → Branches → main protection:
retain Require a pull request and required status checks; disable required
approving reviews, code-owner approval and last-push approval requirements.
Inspect Settings → Rules → Rulesets → main-targeted rules similarly: required
approvals zero/no reviewer-presence requirement; retain required CI and protections
against force pushes/deletion. Any mandatory review-conversation resolution must
not turn advisory comments into an approval gate; actual technical failures still
block. These settings require human inspection under the reported access limit.

## Working tree / limitations

Branch remains control/CTRL-HOST-002-plane-queue, HEAD
0caa66b4ef29ce1f71eca8b664a80df680ed04a1. Changes remain unstaged/uncommitted.
No commit, push, merge, review, Plane mutation, product implementation or changes
to another developer workspace were performed. Root installed policy intentionally
reflects the owner's authorized local migration before publication; governing
source drift continues to fail closed. Evidence is not product acceptance.
