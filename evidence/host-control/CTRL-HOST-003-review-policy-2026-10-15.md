# CTRL-HOST-003 / CHG-017 — Final development review policy

Authority: explicit final project-owner decision, 15 October2026.
Policy ID: DEV-REVIEW-2026-10-15. Scope: development/GitHub PR governance only.
Work is confined to the reference control clone and existing host helper/policy.
No active developer workspace, product implementation or production Plane mutation.
No commit, push, review, merge or GitHub repository-settings change in this pass.

## Active policy and canonical reconciliation

Normal-risk approval count is **0**: CR-0/CR-1/CR-2, ordinary implementation,
docs/tooling and normal research implementation. Review/request/comment remains
optional. Actual high risk requires **2 qualified independent current-head
approvals**, covering auth/authorization, protected-action authority, destructive
schema/data migration, secrets/security infrastructure, major authority boundaries
or explicitly high-risk safety/protected execution semantics. CI, timeout and
owner override cannot replace either approval. Self/pair approval is not counted.

Canonical docs/01 Item63/64 and REVIEW-INV-07, docs/08 DoR-PR/PR DoD/workflow,
docs/09 risk matrix/lifecycle/companion, AGENTS, PR template/CODEOWNERS routing,
engineering/team runbooks, red-team binding and migration changelog are aligned.
CHG-017 records the decision; CHG-001…016 reference the active policy while keeping
their original decisions/reviews and historical 14 October migration data intact.
The former one-approval policy is explicitly historical/superseded, not erased.

The static companion `09_change/development_review_policy.json` is validated by
projectctl for exact authority/scope, 0/2 counts, all six high-risk triggers,
anti-override guards and the policy table bindings in docs/01, docs/08 and docs/09.
A claimed missing/conflicting companion is an ERROR. The host builder consumes
that same validated policy and hashes it into the installed root manifest; no
second management database or separate confirmation protocol is introduced.

All requirement/WP/owner/planning/trace semantic data remains identical. The
canonical semantic SHA-256 before and after is:
`c18ba1bd9fb1c6d950609b039d62ff16ea0b2270cd5ebf55dc6b3e4cae8508a9`.
Existing master requirement line citations were preserved; zero stale citations.

## Helper behavior

Normal-risk IN_REVIEW → MERGE_READY does not require approvals. It still checks
canonical WP/owner/assignee/PR identity, actual non-draft current head, native PR
scope/requirements/DoR-PR/applicable pre-merge DoD declarations and immutable
artifacts, actual required CI, mergeability/no lag behind main and no blocking
review. Missing declarations/artifacts or conflicting high-risk impact fails
closed. Review requests are optional at normal risk, not a prerequisite hidden
in IN_REVIEW. High risk retains actual two-review independence, qualification,
expertise and revision binding. No general owner-override bypass is accepted.

CHANGES_REQUESTED is not erased by a new commit, a comment or reviewer absence.
A reviewer clears the finding by an attributable substantive resolution; ambiguous
DISMISSED history alone fails closed. Optional normal-risk approval is never
fabricated. Qualitative final WP DoD, scientific/freeze acceptance, post-merge
validation and product HITL/protected-action approval remain separate real gates.
Native author declarations are accountable assertions, not automatic proof of
semantic completeness. Merged != Done; Tested != Verified; Demoed != Accepted.

Credential root 0600 / directory 0700, exact sudo grants, fixed API endpoints,
state/BLOCKED-only payloads, fresh before/after GET, audit and queue bytes remain.
No SSH/session/profile identity layer or unrelated infrastructure is added.

## Executed tests and validation

- Complete projectctl suite: **220 PASS in 65.70s**, including 15 policy tests.
- Final transition suite: **59 PASS**, entirely offline fixtures/mocks.
- Existing queue suite: **13 PASS**, unchanged behavior.
- `projectctl validate --json`: **PASS**. 306 requirements (186 FR, 120 NFR),
  179 unique WPs; ownership 73/17/32/57; 29 capabilities; 13 cycles; nine
  milestones; 100 dependency nodes / 217 edges (208 HARD, nine SOFT), zero HARD
  cycles; 174 scheduled and the exact five unscheduled WPs retained.
- Static offline execution status remains UNAVAILABLE (documentation only).
- Changed YAML files parse successfully; registry contains 17 unique CHG IDs.
- `git diff --check`: PASS.
- Root installation and dedicated/full sudoers syntax checks: PASS.
- Installed helper/source/policy, credential permissions, unchanged audit/queue
  and actual-key source/output/audit leakage checks: PASS.

An initial GET-only live eligibility check rejected the native multiline
"Known limitations" declaration as missing. No mutation occurred. The parser was
corrected to read multiline native fields; a regression test was added and the
final helper/policy rebuilt, reinstalled and successfully evaluated. The failed
check is not represented as a passing production transition.

## Installed policy and PR #7

Previous deployed digest:
`67cdf7fd5d6e51402f5eb76703abba69cef74cde64586708b53dc61de4cb63b5`.
Final installed digest:
`06c5553369a65240fd38260836dd034f4ec464509d2907809a0daf3f30d4453b`.

PR #7 head `eb559a31c37a71759689a318313e495a377bad3c` was fresh-read through
GitHub: canonical WP-GOV-001 PR, open, non-draft, no submitted reviews, current
projectctl checks successful, clean/mergeable and no lag behind main. Reviewed
file scope is offline requirement catalog/lint, corresponding trace/evidence and
read-only CI integration; it introduces no auth/protected-action/secrets authority
change. Its existing PR body and actual artifacts supply the pre-merge declarations.

Installed-helper GET-only evaluation of actual IN_REVIEW → MERGE_READY returned
**ELIGIBLE_READ_ONLY_NO_PATCH**, required approvals normal=0 / high=2. The probe
explicitly disabled execute/PATCH/audit mutation paths. This records eligibility
at the observed revision, not a transition or merge authorization for a later head.

## Production readback

Initial and final: **177 BACKLOG / 1 READY / 1 IN_REVIEW**, 179 WPs.
WP-GOV-001 stays IN_REVIEW; no test mutation, auto-merge or automatic DONE.
Complete before/after digest is unchanged:
`443396c691212871de4e2bd3d51e61052a7b6da38811cb329dc89118aaf4d6cb`.
Final read completed at `2026-10-15T01:42:04.726237+00:00`; Plane reads were GET only.

[Sanitized verification](CTRL-HOST-003-review-policy-verification.json) records
installed checks, both policy digests, live eligibility and final readback.
