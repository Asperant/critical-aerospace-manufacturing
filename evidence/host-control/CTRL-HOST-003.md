# CTRL-HOST-003 — Evidence-gated developer Plane transitions

Date: 2026-10-15 (Europe/Istanbul). Owner explicitly authorizes workflow/BLOCKED
mutation on the caller's own assigned canonical WPs. The owner explicitly accepts
same-UID CAP_PROFILE impersonation risk and prohibits an added SSH session-binding
identity layer. This is a **trusted-team operational guard**, not Unix isolation.

## Scope and authority

Only the reference clone/control branch and host helper/config/audit locations
were changed. No active workspace was read or changed, including Asrın's active
WP-GOV-001 branch. No product implementation, canonical docs edit, assignment,
cycle, milestone, module, WP description, create/delete, review/merge authority or
product HITL/protected-action authority is introduced.

`cap-plane-queue` source/deployed bytes and its read-only behavior are unchanged.
New command is `cap-plane-transition <WP-ID> <TARGET_STATE>` with a bounded
reason/evidence_refs-only JSON envelope on stdin. References resolve through
fixed GET-only GitHub API families and existing per-profile authentication after
dropping root; arbitrary URLs/Plane bodies/extra arguments are not accepted.

Root API credential remains `/etc/cap-plane-queue/credential.json` (root 0600,
parent 0700). No credential is copied into a developer profile, CODEX_HOME, repo,
argv or environment. No GitHub credential is copied/provisioned by this change.
Root-owned launch/helper paths are `/usr/local/bin/cap-plane-transition` and
`/usr/local/libexec/cap-plane-transition`. Sudo grants exact canonical
owner-profile/WP/target combinations; helper still checks fresh identity, assignment,
canonical context, actual evidence, workflow and applicable gates. A sudo argument
grant by itself never authorizes a transition.

## Canonical interpretation

- Context is compiled using the same `projectctl.queries.context` as the CLI.
  Canonical source/helper hashes and full policy digest bind every confirmation
  and audit. Changed/missing governing sources fail closed pending policy refresh.
- 08 §5 task/PR DoR, §7 PR/WP DoD, §8 research DoD, §9 scope supplements and
  selected 04 criteria are evaluated with actual owner/reviewer confirmations,
  immutable artifact refs and fresh GitHub/PR/CI/review/run observations.
- HARD readiness uses 05 node levels and producer confirmation, at the declared
  stage with precise consumer artifacts. Producer WP DONE is not readiness proof.
  MILESTONE_EXIT/FREEZE applicability to WP closure requires explicit supporting
  reviewer disposition; those edges are not blindly turned into blockers/skipped.
- Current 01/09 owner policy: one qualified independent current-head approval for
  normal risk, two for actual high risk, relevant expertise, no self/pair approval.
  Historical PR#4/#5 bounded control overrides do not authorize product WPs or
  arbitrary new revisions. Risk assessment is from an actual current independent
  approver, not a caller-provided risk flag.
- IN_REVIEW -> IN_PROGRESS requires actual draft PR (01 Item64 #29 / 08 §3.1).
  MERGE_READY -> IN_REVIEW requires real review readiness and missing current-head
  approval (01 Item63 #74–76 revision/re-review rules). DONE -> VALIDATING requires
  stale-evidence confirmation and actual validation start (08 §11 / 09 §14).
  Other unsupported backwards/skipping transitions are denied, not invented.
- CANCELED requires an actual project-owner GitHub CANCEL decision bound to exact
  WP/state/revision/policy. Agents must not manufacture an owner cancellation
  record. Accepted account/UID attribution cannot prove whether a human typed it.
- Qualitative criteria still require accountable semantic assessment: existence
  of a file or green run alone is not semantic verification. The helper does not
  replace required canonical owner/supporting-reviewer confirmation with AI belief.
  Documentation-only check-ready/check-done UNKNOWN is not changed to PASS.

## Write and audit boundary

The sole Plane mutation is one PATCH to the fresh, canonical-resolved issue UUID
in the fixed CAP project. Only one generated key is sent: state mapped from live
canonical states, or existing labels plus/minus the existing BLOCKED label. Other
labels and protected fields are verified unchanged on fresh GET. No arbitrary API
route/body/method is exposed.

BLOCKED has a real owner/link/external dependency and reason/observed artifacts.
UNBLOCKED binds the previous verified blocker audit ID, actual resolution artifacts
and a successful relevant run or supporting-reviewer confirmation. It never silently
clears an unknown legacy blocker. BLOCKED remains orthogonal to workflow state.

`/var/log/cap-plane-transition/audit.jsonl`, root 0600, directory 0700: durable
INTENT before write; VERIFIED/UNCONFIRMED after fresh GET, including timestamp,
profile, WP, from/to, reason, evidence_refs, result, operation, policy_digest and
blocker/audit binding. No raw response/exception/secret logging. One PATCH, no
blind retry. An ambiguous/lost PATCH response is reconciled by GET, not another
PATCH. Detected concurrent changes/protected-field changes fail closed. API has
no verified atomic compare-and-swap contract; external UI writes can still race.

## Actual executed checks

- **34 transition tests PASS**, all using fixtures/mocks, no production credential
  loaded or API called by tests. Covers four profiles, canonical ownership/live
  assignee matching, forward/rework/invalid/terminal transitions, wrong/noncanonical
  WPs, arbitrary arguments/body/path, BLOCKED set/clear/resolution, explicit owner
  cancellation, CI/current-head review/high-risk/pair independence, post-merge
  events, stage applicability, protected-field readback, timeout/lost response,
  idempotency, audit failure, secret input/output guards, policy-source drift,
  orthogonal blocker resolution without terminal workflow resurrection, and actual
  raw size-band labels used only as relative heavy-work classes (no day estimates).
- **13 existing queue tests PASS**; **205 existing projectctl tests PASS**
  (`205 passed in 65.51s`). Canonical validation **PASS**; 306 requirements,
  179 WPs, 29 capability areas, 13 cycles, zero HARD cycles. No counts manufactured.
- `git diff --check` PASS; `docs/` unchanged.
- Idempotent root installer re-run; both visudo checks PASS; root ownership/modes,
  deployed/source hashes and unchanged deployed queue verified.
- Real host negative smoke: unknown envelope body field is rejected before any
  API/credential use. Sudo rejects extra args, wrong profile/WP and noncanonical WP.
  No production valid-transition invocation or mutation test was executed.
- Actual-key scan against source, outputs, empty audit and recent journal: no
  secret match. Fixture secret leakage checks also PASS.
- RustDesk PID1785 / Tailscale PID1154321 unchanged and active; all four personal
  SSH sockets remain active. No SSH/session/profile isolation configuration change.

## Fresh production readback

Before and final-after observations: **179 WPs, 177 BACKLOG / 1 IN_PROGRESS /
1 READY**. Canonical ID/title/profile assignment/state/BLOCKED/cycle digest:
`f7f26e6fd776018cebd5a9255bfaffb3d0d4a92b85f43c18258ec2ff564b73f5`.
Comparison: **UNCHANGED**, audit file **empty**, all audit reads **GET only**.
Adjacent verification JSON records actual results. No production Plane test
mutation, assignment, workflow advancement or product WP completion occurred.

## Availability and limitations

- Isolated GitHub user GET verified Asrın's profile. Selman/Batuhan/Yavuz profile
  authentication was unavailable or mismatched. Each must authenticate their own
  existing profile with normal gh auth login before GitHub-dependent operations;
  tokens were not copied or identities substituted. This is normal developer
  authentication, not an added session-binding layer.
- Missing canonical confirmations, unknown dependency readiness/applicability,
  unimplemented fixture/fallback certification, incomplete API pagination or
  unavailable GitHub/Plane fail closed. No fabricated PASS/defaults.
- Exact source/helper policy changes require root policy refresh. Existing blockers
  with no verified host audit history need explicit owner reconciliation; they are
  not automatically cleared. No automatic production WP repair/rollback.
- Same-UID malicious impersonation/full sudo access remain accepted outside this
  operational guard; no stronger security isolation claim is made.
- AGENTS.md and source/evidence remain on the separate control PR; active workspaces
  are not pulled, modified or made to inherit new AGENTS content mid-implementation.

Change class: C2 host workflow/authority behavior; CR-3 actual credential/sudo/
mutation boundary. Independent high-risk code reviews remain required before
merge. This report does not claim review approval, merge or product WP completion.
