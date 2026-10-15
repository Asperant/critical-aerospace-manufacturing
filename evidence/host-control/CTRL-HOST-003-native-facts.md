# CTRL-HOST-003 — Native execution facts revision

Historical native-facts deployment report for commit 0caa66b. The later final
15 October2026 owner decision replaces the normal-risk one-approval quota with zero;
see [current policy migration](CTRL-HOST-003-review-policy-2026-10-15.md). Recorded
checks/digests/readbacks below retain their original historical attribution.

Date: 2026-10-15, Europe/Istanbul. This follows the owner's explicit simplification
of cap-plane-transition after WP-GOV-001 IN_PROGRESS → IN_REVIEW was rejected for
a missing special JSON confirmation despite an actual reviewable PR. The previous
report is historical; its tests/deployment results are not rewritten.

## Result

The five mechanical forward edges READY → IN_PROGRESS → IN_REVIEW → MERGE_READY
→ MERGED → VALIDATING no longer require a transition confirmation comment.
Actual GitHub/Plane facts are sufficient subject to ownership, WIP, applicable
readiness, current-head review/risk/CI and merge/validation predicates. Starting
work may reference a real caller-authored commit on exactly one actual WP branch
before opening a PR. Non-draft PRs still require actual requested review and green
CI before IN_REVIEW. Risk comes from the native PR/current-review declaration;
unknown/conflicting risk is denied. Independent approvals retain revision binding.

BACKLOG → READY, VALIDATING → DONE, cancellation, blocker resolution and evidence
staleness still need genuine accountable assessment/decision. Existing PR/review
checklists, referenced comments and immutable linked Markdown assessments can
provide it; no special JSON/source-manifest/policy-digest duplication is needed.
Canonical IDs, actual author/role/revision, criterion coverage and evidence links
are checked. Free prose is not guessed into PASS. Legacy JSON is optional backward
compatibility. No new general owner override or self-approval exception is added.

The accepted same-UID operational model, root credential, exact sudo grants,
canonical/Plane ownership matching, fixed endpoints, minimal state/BLOCKED PATCH,
fresh reads and protected-field checks, pacing, audit and fail-closed behavior
remain. Merged != Done; Implemented != Tested; Tested != Verified; Demoed !=
Accepted. AGENTS execution-queue text now explicitly distinguishes observed facts
from semantic assessments. Canonical docs and projectctl behavior are unchanged.

## Executed verification

- Offline transition suite: **47 PASS**. Includes PR #7-style regression without
  comments, all five mechanical edges, four-profile isolation, real-branch start,
  noncanonical/foreign/invalid/arbitrary input rejection, current CI/review/merge
  guards, native DoR/DoD and linked evidence, native producer readiness, explicit
  cancellation, blocker set/clear, idempotency, audit/secret/readback failures.
- Existing offline queue suite: **13 PASS**.
- Existing complete projectctl suite: **205 PASS in 68.06 seconds**.
- `projectctl validate --json`: **PASS**; 306 requirements (186 FR, 120 NFR),
  179 WPs, ownership 73/17/32/57, 29 capabilities, 13 cycles, 9 milestones,
  100 dependency nodes / 217 edges (208 HARD, 9 SOFT), zero HARD cycles,
  174 scheduled / five canonical unscheduled WPs. Offline execution remains
  UNAVAILABLE (documentation only), as designed.
- `git diff --check`: PASS. No canonical docs or active developer workspace changes.
- Root installer: completed; dedicated/full sudoers syntax PASS; no service restart.
- Installed policy/helper source verification: PASS; queue bytes unchanged.
- Credential still root:root 0600 in root:root 0700 directory; no secret in checked
  source, output or audit. Production audit unchanged during deployment/probe.
- Actual PR #7 head `eb559a31c37a71759689a318313e495a377bad3c` was fresh-read:
  open, non-draft, Yavuz review requested, two projectctl checks SUCCESS.
- Administrative GET-only evaluation of actual WP-GOV-001 IN_PROGRESS → IN_REVIEW:
  **ELIGIBLE_READ_ONLY_NO_PATCH**, with just `pr:7` evidence. The probe disabled
  execute/audit/PATCH explicitly. No production transition command was invoked.

## Policy digest

Previous: `e1ae1754908eb374442f0149fed04a6e8cba8acc1452232d7facc81aef7bc5ed`.
Installed: `67cdf7fd5d6e51402f5eb76703abba69cef74cde64586708b53dc61de4cb63b5`.
Policy evaluation revision: `native-execution-facts-v2`. Both canonical source and
helper hashes remain enforced. No external confirmation needs to copy this digest.

[Sanitized installed verification](CTRL-HOST-003-native-facts-verification.json)
records actual root permissions, source/digest checks and read-only probe results.

## Production readback

Initial read: 179 WPs, 177 BACKLOG / 1 READY / 1 IN_PROGRESS. WP-GOV-001 remains
IN_PROGRESS during the eligibility probe; this change does not advance its state.
Final complete queue readback: **UNCHANGED**, 177 BACKLOG / 1 READY / 1 IN_PROGRESS,
179 WPs; GET only. Before/after snapshot digest:
`f7f26e6fd776018cebd5a9255bfaffb3d0d4a92b85f43c18258ec2ff564b73f5`.
No production PATCH or test mutation occurred.

## Limits

Semantic completeness still needs actual owner/supporting-reviewer judgment;
a green check or existing artifact alone cannot prove acceptance. Unsupported or
ambiguous native evidence fails closed rather than being inferred. Actual future
owner overrides must be authorized by current canonical governance; historical
control-PR exceptions are not product authorizations. Same-UID impersonation and
Plane's lack of transactional compare-and-swap remain the documented accepted
limits. No production test mutation, product work, canonical edit, PR approval or
merge was performed.
