# CTRL-HOST-003 — Evidence-gated developer workflow transitions

This extends CTRL-HOST-002 without modifying `cap-plane-queue`. It is host/control
infrastructure, not product implementation or a second project-management system.
The owner explicitly accepts same-UID impersonation risk: CAP_PROFILE is a
**trusted-team operational guard**, not authentication/security isolation. No new
Unix user, SSH session binding, workspace change or service restart is introduced.

## Invocation

```text
cap-plane-transition <canonical-WP-ID> <TARGET_STATE>
```

Exactly two public arguments. CAP_PROFILE is set by the existing session. Supply
a bounded JSON envelope on stdin with **only** `reason` and `evidence_refs`:

```json
{"reason":"Observed execution event, with actual references","evidence_refs":["pr:123","comment:456","run:789"]}
```

Numbers above are placeholders, not actual evidence. The helper accepts references
`pr:<number>` (at most one), `comment:<number>`, `run:<number>` (at most 16 total).
It rejects URLs, endpoints, arbitrary request bodies, extra fields and extra args.
It never creates comments or any GitHub/Plane entity. Exit 0 means VERIFIED or an
idempotent UNCHANGED; exit 2 means DENIED/UNAVAILABLE/unconfirmed mutation.

## Canonical evaluation, not an edge allowlist

The build uses the existing `projectctl.queries.context` (the same context returned
by `projectctl context <WP-ID>`) and current docs/08 criteria, WP selected criteria,
all source-requirement scope supplements and docs/05 dependency nodes/edges.
Canonical source hashes and installed helper hashes are checked on every call;
confirmation/audit records bind the full installed policy digest. A changed/missing
source in the reference clone fails closed until an owner refreshes the root policy.
Planning prose or documentation-only `projectctl check-ready/check-done` UNKNOWN
never becomes PASS. No existing projectctl parser/gate semantics are changed.

| Operation | Required observed facts / canonical confirmation |
|---|---|
| BACKLOG → READY | Own assigned canonical scheduled WP; no other READY for that profile; owner confirms all 12 DOR-TASK criteria plus selected DOR-WP refs with real immutable artifacts; producer confirms inbound START HARD readiness and precise consumed artifacts |
| READY → IN_PROGRESS | Actual changed, open WP branch/PR, explicit implementation-start event and artifact; WIP <=2 implementation items, <=1 heavy/core; START HARD readiness rechecked |
| IN_PROGRESS → IN_REVIEW | Actual non-draft WP PR with requested review; current required/observed CI green; author confirms all DOR-PR criteria |
| IN_REVIEW → MERGE_READY | Live current-head CI, safe/mergeable against main, no blocking review; one qualified independent current-head approval for normal risk, two for actual high-risk; risk/PR criteria confirmed by a current independent approver |
| MERGE_READY → MERGED | GitHub actually merged into main; single-parent squash-compatible merge shape, source branch deleted; live head CI/reviews and PR DoD confirmations (mergeability is not re-required after merge) |
| MERGED → VALIDATING | Actual main/merge-revision post-merge validation run in progress and owner evidence of start; queued/pre-merge runs do not qualify |
| VALIDATING → DONE | Owner and supporting reviewer confirm all WP DoD plus selected/scope/research obligations; actual current CI/reviews, deleted branch, exact merge-revision successful post-merge run, HARD readiness at relevant stages and real accepted trace/evidence artifacts |
| CANCELED | Actual GitHub project-owner (Asperant) explicit CANCEL decision, bound to WP/current state/revision/policy; a caller flag or agent decision is insufficient |

Normal-risk qualification is impact-based, not a mandatory owner pair. Actual high
risk triggers are authentication/authorization, protected-action authority,
destructive migration, security-sensitive infra/secrets, major authority boundary.
Commit authors/committers, declared pair participants and recognized co-author
trailers cannot supply independent approval. A stale approval cannot be reused.
The bounded historical PR#4 policy migration / PR#5 exact-head owner overrides do
not authorize product WPs, new heads or a general self-approval exception.

Conservative rework is tied to explicit canonical state meaning:

- IN_REVIEW → IN_PROGRESS only if the actual PR is draft again: 01 Item64 #29 /
  08 §3.1, draft PR is not IN_REVIEW; implementation/WIP evidence still required. Relative L bands or Core work are
  conservatively counted as heavy; indicative day text is never a capacity estimate.
- MERGE_READY → IN_REVIEW only with a real reviewable PR requiring review again
  and no current-head approval: 01 Item63 #74–76, revision-bound approvals and
  mandatory re-review after material changes; author review-readiness/CI required.
- DONE → VALIDATING only with supporting-reviewer stale-evidence confirmation,
  actual post-merge validation running: 08 §11 / 09 §14 evidence staleness.
- Other skips/backward transitions fail closed. CANCELED has no outgoing workflow
  transition; a verified orthogonal BLOCKED clear preserves the terminal state.

These are operation guards, not independent product workflow policy. Do not use
this tool to approve/merge PRs, change product HITL authority or assert DONE from
merged/tests/demo alone. Merged != Done; Implemented != Tested; Tested != Verified;
Demoed != Accepted.

## Evidence/confirmation records

The root helper GETs real GitHub facts with the fixed system gh binary, **after
dropping to ailab**, in the existing per-profile GH_CONFIG_DIR and with a clean
environment. The returned authenticated GitHub login must match that profile's
verified account. There is no root execution of repository code, no inherited
GH_TOKEN, no new/copied GitHub credential and no GitHub mutation API. Missing
per-profile authentication fails closed; authenticate the normal profile first.

Qualitative canonical criteria remain accountable owner/reviewer judgments; file
existence or a green run cannot mechanically prove semantic completeness. An
actual GitHub issue/PR comment records that judgment at an exact revision and
policy. This is **not** a caller-provided `PASS` boolean, a raw Plane body, or a
substitute for required independent review. The helper verifies author/role,
revision, policy hashes, required criterion coverage and dereferences artifact
references, alongside actual PR/CI/review/dependency facts. Evidence content and
N/A applicability remain subject to canonical review. Semantic truth is not
claimed to follow from an artifact existing.

Comment body is an exact JSON object with key `cap_plane_transition`:

```text
{
  "cap_plane_transition": {
    "wp_id": "<canonical WP>",
    "from_state": "<fresh Plane workflow state>",
    "to_state": "<requested state or BLOCKED/UNBLOCKED>",
    "head_sha": "<actual PR head or actual merge SHA; main SHA for pre-PR records>",
    "source_manifest": {"<path>": "<exact installed policy source hash>"},
    "policy_digest": "<exact installed canonical-context/helper policy digest>",
    "reason": "<observed execution fact>",
    "checks": {
      "<applicable canonical criterion ID>": {
        "result": "PASS or justified N/A",
        "reason": "<actual assessment; no TBD/unknown presented as PASS>",
        "evidence_refs": ["repo:<immutable file path> or artifact:<artifact ID>"]
      }
    }
  }
}
```

This skeleton is not evidence. Canonical IDs/definitions and exact source_manifest
are published read-only at `/usr/local/share/cap-plane-transition/policy-manifest.json`.
DOR-TASK/DOR-PR/DOD-PR/DOD-WP/DOD-RES IDs come from docs/08. `docs/08#9:F0` etc.
refer to the actual source-requirement class supplements, not new requirements.
`IMPLEMENTATION-STARTED`, `POST-MERGE-VALIDATION-STARTED`, `BLOCKER-OBSERVED`,
`BLOCKER-RESOLVED`, `docs/08#11:EVIDENCE-STALE` are helper event references to the
canonical entry/staleness/blocker rules, not new workflow states or project IDs.
Always-applicable DoD obligations and actual execution events cannot be N/A.
N/A elsewhere requires a reason and real evidence; it is never silently inferred.

For pre-PR readiness/blocker/cancellation, a real owner comment bound to the actual
main revision suffices; implementation is never required **before** DoR. Subsequent
operations require one real WP PR, owner-authored with `wp/<WP-ID>-...` branch and
WP binding in title/body. Post-merge refs bind the actual merge revision.

For review gates the confirming independent approver adds:

```text
"review_risk": "normal or high",
"high_risk_triggers": [],
"qualified_reviewers": ["<relevant independently approving GitHub account>"],
"pairing_participants": []
```

High-risk enum values: `authentication_authorization`, `protected_action_authority`,
`destructive_migration`, `security_sensitive_infra_secrets`, `major_authority_boundary`.
Do not downgrade actual risk by leaving that list empty; the independent risk
assessment remains part of the reviewed governance record.

For inbound HARD dependencies, a real producer-owner confirmation comment at the
same consumer revision/policy (including `policy_digest`) includes `dependency_readiness` keyed by DEP-ID with
`readiness`, `precise_consumer_requirement`, `evidence_refs`. Root policy checks
the node's canonical ordered readiness levels. Producer WP DONE is not substituted
for actual readiness. Automatic fixture/fallback certification is not implemented;
unknown readiness is DENIED, never treated as satisfied because a stub exists.
At WP closure, MILESTONE_EXIT/FREEZE edges require an explicit supporting-reviewer
`dependency_stage_dispositions` entry per DEP-ID with `applies_to_wp_completion`
(boolean), `reason` and actual `evidence_refs`. They are never blindly converted
into WP closure blockers or silently skipped; unknown applicability is DENIED.

## BLOCKED and cancellation

`BLOCKED` / `UNBLOCKED` are operations on the existing BLOCKED label, not states.
They preserve state and all other labels. Setting requires an owner confirmation
with `blocker: {owner: <profile>, wp_id: <canonical blocker WP>}` or a named
`external_dependency`, plus real blocker evidence. Audit records include the
blocker owner/link/external dependency. The returned audit_id identifies it.

Clearing requires `resolves_audit_id` matching the prior verified blocker, actual
resolution artifacts and either a same-revision successful validation run completed
after the blocker was recorded, or a
supporting-reviewer confirmation. Existing blockers with no verified history are
not guessed away. Repeating BLOCKED returns its active blocker audit ID when known.
No WP description/comment is patched to record blockers: their durable reason is
in the referenced GitHub confirmation and secret-free host audit.

Cancellation requires `owner_decision: "CANCEL"` in the actual project-owner
confirmation. That decision must originate from an explicit human owner request;
Codex must not manufacture owner comments to cancel scope. Account attribution
cannot distinguish a human from an agent using that same accepted account/UID.

## Root boundary, audit, deployment

- Launcher `/usr/local/bin/cap-plane-transition`, root helper
  `/usr/local/libexec/cap-plane-transition`, both root:root 0755.
- Existing root-only `/etc/cap-plane-queue/credential.json` stays in place.
- Static canonical policy `/etc/cap-plane-queue/transition-policy.json`, root 0600;
  contains source projections, never execution state. Public manifest has no secret.
- `/etc/sudoers.d/cap-plane-transition`: generated exact profile/WP/target argument
  combinations from canonical ownership. This sudo hygiene does not authorize a
  transition: live predicates are still required. No shell/interpreter/glob grant.
- Root-owned `/var/log/cap-plane-transition/` 0700 and `audit.jsonl` 0600. Each actual
  write gets durable INTENT before PATCH and VERIFIED or UNCONFIRMED outcome after
  fresh GET. Records contain timestamp/profile/WP/from/to/reason/evidence_refs/result
  plus operation/audit_id/blocker-resolution binding. No credential or raw API body.
- The sole Plane write endpoint is the fresh resolved UUID's fixed project issue
  detail. Exactly one constructed body: `{state: mapped_uuid}` or `{labels: existing
  labels plus/minus BLOCKED}`. No create/delete/assignee/description/cycle/module/
  milestone API. No arbitrary request method/body/endpoint argument.
- Queue and transitions share the root-only API pacing lock. Fresh full issue GET
  is checked again immediately before PATCH; fresh GET verifies state/label and
  protected fields afterwards. Only one PATCH, no automatic retry. API has no
  transactional compare-and-swap contract: an external UI write can still race.
  A detected race/uncertain readback fails closed and requires reconciliation;
  never compensate by overwriting unrelated fields or blindly retrying.
- Root code uses isolated Python, clean environment, disabled proxy/redirect/core
  dumps, bounded JSON and sanitized/redacted diagnostics. sudo-rs ignores -E;
  helper isolation does not rely on it. Code/secret/log are not ailab-writable.

Build unprivileged from the reference control clone, then install:

```bash
.venv/bin/python tools/host/plane-transition/build_policy.py
sudo python3 -I /srv/ailab/project/tools/host/plane-transition/install.py
```

Installer preserves credential/audit/queue, validates sudo syntax, starts no service
and sends **no API request**. Re-run is idempotent. Refresh the policy after reviewed
canonical/AGENTS/CI policy changes; do not silently copy an unreviewed workspace as
canonical truth. Rollback: owner disables only the dedicated transition sudoers
file; keep audit/credential protected, leave read-only queue intact. No automatic
Plane rollback.

All transition tests are fixtures/mocks; never exercise a real mutation on a
production WP to test this helper. See `test_transition.py` and control evidence.
