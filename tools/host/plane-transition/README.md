# CTRL-HOST-003 — Plane workflow projection

This extends CTRL-HOST-002; the read-only queue is unchanged. CAP_PROFILE is a
trusted-team operational guard, not a security boundary between the shared ailab
UID's processes. No new identity layer, SSH change or developer-workspace change.

## Invocation

```text
cap-plane-transition <canonical-WP-ID> <TARGET_STATE>
```

Exactly two arguments; CAP_PROFILE selects the existing profile. Stdin accepts
only a bounded reason/evidence envelope, for example:

```json
{"reason":"Implementation PR is open, review requested, CI green","evidence_refs":["pr:7"]}
```

This example illustrates input; the helper fresh-reads the facts, never trusts the
reason as proof. References: `pr:N` (at most one), `run:N`, `comment:N`, or
`commit:<40-character SHA>` for starting actual work before a PR exists. At most
16 references; a commit and PR cannot be mixed. No URL, endpoint, request body,
extra input field or extra argument. Exit 0 means VERIFIED/UNCHANGED; exit 2 means
DENIED/UNAVAILABLE/unconfirmed mutation.

## Facts first; no additional confirmation protocol

| Transition | Actual evidence required |
|---|---|
| READY → IN_PROGRESS | Changed open canonical WP PR, or verified caller-authored commit at exactly one canonical WP branch head with actual changes ahead of main; owner/assignee, WIP and START HARD dependency checks |
| IN_PROGRESS → IN_REVIEW | Real open non-draft WP PR, required and observed current-head CI green; all development review requests optional |
| IN_REVIEW → MERGE_READY | Current-head CI, mergeable/clean, no real BLOCKED condition; native scope/DoR-PR/applicable pre-merge PR DoD and evidence checks; all development approvals 0 |
| MERGE_READY → MERGED | Actually merged to main, squash-compatible single-parent commit, deleted work branch, actual head CI/technical evidence |
| MERGED → VALIDATING | Actual main validation run in progress at the merge revision; queued or pre-merge runs do not qualify |

These five forward transitions require **no confirmation comment**. Existing PR
metadata/body, commits and CI runs supply the evidence. An extra JSON
comment does not make execution facts more authoritative. No GitHub write occurs.

Review is advisory for every development risk class. The helper does not query GitHub review states, compute approval quotas, require reviewer presence or use owner overrides. Actual technical, canonical, scope and evidence failures still fail closed.

## Semantic evidence remains necessary

- BACKLOG → READY: scheduled own WP, no other READY for the profile, actual owner
  DoR assessment covering canonical DOR-TASK and selected DOR-WP criteria; producer
  evidence for applicable HARD readiness and precise consumer artifacts.
- VALIDATING → DONE: actual accountable-owner assessment of all
  applicable WP/scope/research DoD, accepted trace/evidence, successful actual
  merge-revision validation, actual CI/technical checks and applicable dependency gates.
- CANCELED: explicit human project-owner cancellation decision, not an agent's
  scope decision. Account attribution alone cannot distinguish a human from an
  agent using the same accepted account; this limitation is not concealed.
- BLOCKED / UNBLOCKED: real blocker reason/owner/work or external dependency;
  clearing binds the previously verified blocker audit ID and actual resolution,
  corroborated by a successful same-revision run after the blocker or actual resolution artifacts. No silent clearing of blockers with missing history.

Reuse **existing** PR descriptions, referenced
GitHub comments, or immutable Markdown assessments linked by those artifacts. Reviewers are not required.
No new special JSON comment, source-manifest copy, policy digest copy, or separate
transition-specific confirmation is required. Native semantic evidence uses the
canonical criterion IDs already defined in docs/08, checked Markdown checklists
or tables (`ID | PASS / N/A | assessment and artifact links`). Missing criteria,
unjustified mandatory N/A or conflicting assessments fail closed. Free prose is
not guessed into PASS. An existing linked assessment may live under `evidence/`,
`09_change/` or `project_control/`; one bounded hop, at the actual immutable revision.
Relative repository links and `repo:path` / `artifact:N` evidence are dereferenced.
File existence alone never certifies semantic correctness.

Comments must identify the WP and exact revision (and the actual PR when present).
PR evidence inherits GitHub attribution and actual revision. Ordinary
unrelated comments are ignored. Native blocker notes can use `Blocker owner:`,
`Blocking WP:` or `External dependency:`, and `Resolves blocker:`; owner decisions
use `Owner decision: CANCEL`. These are readable assessments, not mutation-body
fields. Legacy `cap_plane_transition` JSON comments remain optionally readable
with their original revision/policy bindings; they are not required.

Producer readiness can be an existing `DEP-ID | readiness | precise consumer and
artifact links` table. Root policy checks canonical ordered readiness levels; a
producer WP's DONE state alone is insufficient. At closure, MILESTONE_EXIT/FREEZE
applicability needs an accountable-owner assessment (a justified
`DEP-ID | NOT_APPLICABLE | reason and evidence` table is supported). Unknown gates
fail closed; no fixture is promoted to actual readiness.

Conservative canonical rework remains: IN_REVIEW → IN_PROGRESS only with draft
rework, WIP and dependencies; MERGE_READY → IN_REVIEW with actual reviewable work
and a new actual head relative to the prior verified MERGE_READY audit; DONE →
VALIDATING requires actual owner-attributed staleness evidence and running validation. Advisory review state is irrelevant. Other skips/backward transitions
are denied. CANCELED is terminal. BLOCKED is orthogonal; clearing it never revives
a terminal workflow. Merged != Done; Implemented != Tested; Tested != Verified;
Demoed != Accepted. Indicative size bands are relative weights, never day capacity.

## Root boundary and audit

- Launcher `/usr/local/bin/cap-plane-transition`; helper
  `/usr/local/libexec/cap-plane-transition`, root:root 0755.
- Credential `/etc/cap-plane-queue/credential.json`, root:root 0600, directory 0700;
  never exported to a developer environment, workspace, repository or CODEX_HOME.
- Policy `/etc/cap-plane-queue/transition-policy.json`, root 0600, generated from
  real projectctl context and canonical docs. Source/helper hashes fail closed on
  drift. Public non-secret manifest: `/usr/local/share/cap-plane-transition/`.
- Exact profile/WP/target sudo grants in `/etc/sudoers.d/cap-plane-transition`;
  no arbitrary interpreter, shell, URL or body. CAP_PROFILE + canonical owner +
  fresh Plane assignee must match; caller's real per-profile GitHub login must match.
- GitHub reads use the fixed system gh binary after dropping root, a clean
  environment and existing profile login; no copied credential or repository code
  runs as root. Plane uses fixed loopback API v1 endpoints only.
- Sole write: one constructed `{state: mapped_uuid}` or labels preserving all
  existing labels except the orthogonal BLOCKED addition/removal. No other Plane
  field, create/delete operation, arbitrary method or endpoint is exposed.
- Fresh GET before evaluation, another before PATCH, and fresh GET after PATCH;
  ownership and protected fields rechecked. One PATCH only; no blind retry or
  compensating overwrite. An external UI write can still race because Plane has
  no transactional compare-and-swap contract; uncertain readback requires review.
- `/var/log/cap-plane-transition/audit.jsonl`, root 0600 in directory 0700:
  timestamp/profile/WP/from/to/reason/evidence/result, installed policy digest and
  blocker linkage; durable INTENT before writes and VERIFIED/UNCONFIRMED after.
  No secret or raw API response. Queue and transitions share the root pacing lock.

Build unprivileged and install reviewed source from the reference control clone:

```bash
.venv/bin/python tools/host/plane-transition/build_policy.py
sudo python3 -I /srv/ailab/project/tools/host/plane-transition/install.py
```

Installer preserves credentials, audit and queue, validates sudoers, makes no API
call and restarts no service. Refresh after approved source/AGENTS/CI changes.
Rollback disables only transition sudo grants; retain protected audit/credential
and the read-only queue. Never automatically roll back production Plane state.
Tests use fixtures/mocks only; never mutate production to test transitions.

## Final advisory development review policy — CHG-018, 15 October 2026

Policy ID: `DEV-REVIEW-2026-10-15-FINAL`. CHG-018 explicitly supersedes CHG-017; CHG-017 and its intermediate 0/2 decision remain historical, unchanged. Active companion: `09_change/development_review_policy.json`; previous companion archived under `09_change/history/CHG-017-development_review_policy.json`.

| Policy ID | Scope | Required human approvals |
|---|---|---|
| DEV-REVIEW-2026-10-15-FINAL | ALL_DEVELOPMENT | 0 |

Every repository development PR, CR-0 through CR-4, normal/high risk, security/auth, protected-action-authority code, destructive migration, secrets/infrastructure, authority boundaries, platform, tooling, docs, product and research implementation has zero required human approvals. Review, requests, comments, suggestions and security advice are ADVISORY. No independent/qualified reviewer quota, self-approval rule, owner override, current-head approval or stale-approval mechanism governs development workflow. GitHub APPROVED, CHANGES_REQUESTED, COMMENTED and DISMISSED are not workflow, merge or DONE gates, and reviewer presence/absence never blocks progress. CODEOWNERS and supporting-reviewer metadata are advisory routing/domain context only.

IN_REVIEW means a real non-draft technically reviewable PR, not waiting for a human. MERGE_READY requires correct canonical WP/approved control scope and branch/PR/head binding, required actual CI/tests/canonical validation, mergeability/no conflict against current main, no out-of-scope changes, applicable DoR-PR/PR DoD, trace/evidence and applicable security/secret/static checks, and no real BLOCKED condition. Actual technical/canonical failures or ambiguity fail closed; a review state alone neither proves nor disproves these facts. Material revisions re-run technical checks/evidence. Rework follows actual revision/technical evidence, not approval invalidation.

MERGED requires an actual GitHub merge. VALIDATING requires actual post-merge validation started. DONE requires all applicable DoD, trace/evidence and actual successful post-merge validation; accountable owner assessment and real artifacts remain required, another person's review/confirmation does not. Development peer/methodology review is advisory even for closure; real protocol, scientific reproducibility, measured acceptance and product-authority evidence remain required. Merged != Done; Implemented != Tested; Tested != Verified; Demoed != Accepted.

This changes ONLY development/GitHub/repository governance. Product HITL, protected-action approval, AuthorityPolicy, authenticated approvers, runtime self-approval prohibition, exact proposal/plan binding and execution authorization are unchanged. Project-owner scope/cancellation decisions and real product acceptance artifacts are not GitHub review approvals and are not fabricated or waived. No Plane test mutation, merge, commit or push is authorized in this pass. Existing historical approvals remain history, never requirements for a current transition.


CI verification follows the real check → Actions run → job → named steps at the
actual SHA. Syntax sanity, Projectctl tests, Canonical validation and Whitespace /
repository hygiene must have completed successfully; host changes additionally
require the existing queue-security and transition-fixture steps. The complete
actual PR file list is checked for forbidden secret/runtime paths. A fresh PR read
before any mutation rejects concurrent head/branch/base/draft/merge changes.
Optional review bots and aggregate mergeable_state (which can encode human review
requirements) are not gates; actual conflict-free mergeability and current-main
compatibility are checked directly. No review API is queried. No control-item Plane
write is added; control PRs can be assessed read-only without inventing a canonical
WP or a Plane issue.
