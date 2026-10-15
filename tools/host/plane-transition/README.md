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
| IN_PROGRESS → IN_REVIEW | Real open non-draft WP PR, requested review/review activity, required and observed current-head CI green |
| IN_REVIEW → MERGE_READY | Current-head CI, mergeable/clean, no blocking review; current qualified independent approval(s) and actual declared risk |
| MERGE_READY → MERGED | Actually merged to main, squash-compatible single-parent commit, deleted work branch, actual head CI/reviews |
| MERGED → VALIDATING | Actual main validation run in progress at the merge revision; queued or pre-merge runs do not qualify |

These five forward transitions require **no confirmation comment**. Existing PR
metadata/body, reviews, commits and CI runs supply the evidence. An extra JSON
comment does not make execution facts more authoritative. No GitHub write occurs.

Review risk comes from the existing PR/review risk declaration: normal risk needs
one qualified independent current-head approval; actual high risk needs two,
including authority/security expertise. CR-3 denotes actual high risk; CR-4 alone
does not impose two reviews. Unknown/conflicting risk is denied. Relevant canonical
supporting reviewers provide qualification; no blanket Batuhan approval. Actual
commit authors/committers, co-author trailers and declared pairing participants
cannot independently approve. Missing approvals, unresolved findings or stale
reviews are never replaced by a tool confirmation. Historical owner overrides for
control PRs #4/#5 do not authorize product WPs or new heads.

## Semantic evidence remains necessary

- BACKLOG → READY: scheduled own WP, no other READY for the profile, actual owner
  DoR assessment covering canonical DOR-TASK and selected DOR-WP criteria; producer
  evidence for applicable HARD readiness and precise consumer artifacts.
- VALIDATING → DONE: actual owner and supporting-reviewer assessment of all
  applicable WP/scope/research DoD, accepted trace/evidence, successful actual
  merge-revision validation, reviews/CI and applicable dependency gates.
- CANCELED: explicit human project-owner cancellation decision, not an agent's
  scope decision. Account attribution alone cannot distinguish a human from an
  agent using the same accepted account; this limitation is not concealed.
- BLOCKED / UNBLOCKED: real blocker reason/owner/work or external dependency;
  clearing binds the previously verified blocker audit ID and actual resolution,
  corroborated by a successful same-revision run after the blocker or a supporting
  reviewer. No silent clearing of blockers with missing history.

Reuse **existing** PR descriptions, current-revision review bodies, referenced
GitHub comments, or immutable Markdown assessments linked by those artifacts.
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
PR/review evidence inherits GitHub attribution and actual revision. Ordinary
unrelated comments are ignored. Native blocker notes can use `Blocker owner:`,
`Blocking WP:` or `External dependency:`, and `Resolves blocker:`; owner decisions
use `Owner decision: CANCEL`. These are readable assessments, not mutation-body
fields. Legacy `cap_plane_transition` JSON comments remain optionally readable
with their original revision/policy bindings; they are not required.

Producer readiness can be an existing `DEP-ID | readiness | precise consumer and
artifact links` table. Root policy checks canonical ordered readiness levels; a
producer WP's DONE state alone is insufficient. At closure, MILESTONE_EXIT/FREEZE
applicability needs a supporting-reviewer assessment (a justified
`DEP-ID | NOT_APPLICABLE | reason and evidence` table is supported). Unknown gates
fail closed; no fixture is promoted to actual readiness.

Conservative canonical rework remains: IN_REVIEW → IN_PROGRESS only with draft
rework, WIP and dependencies; MERGE_READY → IN_REVIEW with actual reviewable work
and invalidated current approval; DONE → VALIDATING requires supporting-reviewer
staleness evidence and actual running validation. Other skips/backward transitions
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
