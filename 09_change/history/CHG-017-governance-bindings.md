# Preserved intermediate CHG-017 policy bindings

Historical only. Superseded by CHG-018. Original intermediate text follows.

# docs/01_Master_Project_Specification.md

## Final owner-approved development review policy — 15 October 2026

Policy ID: `DEV-REVIEW-2026-10-15`; migration: `CHG-017`; companion: `09_change/development_review_policy.json`. This final project-owner decision supersedes the 14 October2026 normal-risk one-approval policy for development/GitHub PR governance only.

| Policy ID | Risk | Required independent approvals |
|---|---|---|
| DEV-REVIEW-2026-10-15 | NORMAL_RISK | 0 |
| DEV-REVIEW-2026-10-15 | HIGH_RISK | 2 |

Normal risk includes CR-0/CR-1/CR-2, ordinary implementation, docs/tooling and normal research implementation (including CR-4 without a real high-risk trigger). Human review, review requests and comments are optional and are not merge gates. No self-approval is recorded or fabricated; the author may merge after actual applicable gates pass.

High risk requires two distinct qualified independent current-head approvals covering the actual critical impact: authentication/authorization; protected-action authority; destructive schema/data migration; secrets/security-sensitive infrastructure; major authority-boundary change; explicitly high-risk safety/protected-execution semantics. Author, commit/co-authors and pairing participants do not supply independent approvals. Neither green CI, timeout nor owner override substitutes for either approval. Unassessed/conflicting high-risk impact fails closed; filenames or C0–C3 labels alone do not determine risk.

MERGE_READY requires a real canonical WP PR, non-draft/current head, required CI green, mergeability and safety against current main, scope/DoR-PR/applicable pre-merge PR DoD satisfied, and no unresolved blocking CHANGES_REQUESTED or invariant violation. A new commit, a label, reviewer absence or an owner override cannot silently clear a blocking finding. A reviewer must clear the finding with attributable resolution; ambiguous dismissal alone is insufficient. Approval count zero never means failed CI, missing evidence or an unresolved finding may be bypassed. Post-merge DoD remains post-merge.

All development review matrices/owner/consumer/research routing statements are expertise guidance for normal-risk PRs, not additional approval quotas. Independent semantic acceptance/final-protocol/freeze obligations remain at their actual acceptance gates; they do not impose a blanket GitHub approval on ordinary research implementation. Product runtime HITL, protected-action approval/binding, manufacturing authority and verification obligations are unchanged. Merged != Done; Implemented != Tested; Tested != Verified; Demoed != Accepted. Historical reviews remain bound to their real revisions; no new approval or product completion is inferred.


# docs/08_Definition_of_Ready_and_Done.md

## Final owner-approved development review policy — 15 October 2026

Policy ID: `DEV-REVIEW-2026-10-15`; migration: `CHG-017`; companion: `09_change/development_review_policy.json`. This final project-owner decision supersedes the 14 October2026 normal-risk one-approval policy for development/GitHub PR governance only.

| Policy ID | Risk | Required independent approvals |
|---|---|---|
| DEV-REVIEW-2026-10-15 | NORMAL_RISK | 0 |
| DEV-REVIEW-2026-10-15 | HIGH_RISK | 2 |

Normal risk includes CR-0/CR-1/CR-2, ordinary implementation, docs/tooling and normal research implementation (including CR-4 without a real high-risk trigger). Human review, review requests and comments are optional and are not merge gates. No self-approval is recorded or fabricated; the author may merge after actual applicable gates pass.

High risk requires two distinct qualified independent current-head approvals covering the actual critical impact: authentication/authorization; protected-action authority; destructive schema/data migration; secrets/security-sensitive infrastructure; major authority-boundary change; explicitly high-risk safety/protected-execution semantics. Author, commit/co-authors and pairing participants do not supply independent approvals. Neither green CI, timeout nor owner override substitutes for either approval. Unassessed/conflicting high-risk impact fails closed; filenames or C0–C3 labels alone do not determine risk.

MERGE_READY requires a real canonical WP PR, non-draft/current head, required CI green, mergeability and safety against current main, scope/DoR-PR/applicable pre-merge PR DoD satisfied, and no unresolved blocking CHANGES_REQUESTED or invariant violation. A new commit, a label, reviewer absence or an owner override cannot silently clear a blocking finding. A reviewer must clear the finding with attributable resolution; ambiguous dismissal alone is insufficient. Approval count zero never means failed CI, missing evidence or an unresolved finding may be bypassed. Post-merge DoD remains post-merge.

All development review matrices/owner/consumer/research routing statements are expertise guidance for normal-risk PRs, not additional approval quotas. Independent semantic acceptance/final-protocol/freeze obligations remain at their actual acceptance gates; they do not impose a blanket GitHub approval on ordinary research implementation. Product runtime HITL, protected-action approval/binding, manufacturing authority and verification obligations are unchanged. Merged != Done; Implemented != Tested; Tested != Verified; Demoed != Accepted. Historical reviews remain bound to their real revisions; no new approval or product completion is inferred.


# docs/09_Change_Control_Process.md

## Final owner-approved development review policy — 15 October 2026

Policy ID: `DEV-REVIEW-2026-10-15`; migration: `CHG-017`; companion: `09_change/development_review_policy.json`. This final project-owner decision supersedes the 14 October2026 normal-risk one-approval policy for development/GitHub PR governance only.

| Policy ID | Risk | Required independent approvals |
|---|---|---|
| DEV-REVIEW-2026-10-15 | NORMAL_RISK | 0 |
| DEV-REVIEW-2026-10-15 | HIGH_RISK | 2 |

Normal risk includes CR-0/CR-1/CR-2, ordinary implementation, docs/tooling and normal research implementation (including CR-4 without a real high-risk trigger). Human review, review requests and comments are optional and are not merge gates. No self-approval is recorded or fabricated; the author may merge after actual applicable gates pass.

High risk requires two distinct qualified independent current-head approvals covering the actual critical impact: authentication/authorization; protected-action authority; destructive schema/data migration; secrets/security-sensitive infrastructure; major authority-boundary change; explicitly high-risk safety/protected-execution semantics. Author, commit/co-authors and pairing participants do not supply independent approvals. Neither green CI, timeout nor owner override substitutes for either approval. Unassessed/conflicting high-risk impact fails closed; filenames or C0–C3 labels alone do not determine risk.

MERGE_READY requires a real canonical WP PR, non-draft/current head, required CI green, mergeability and safety against current main, scope/DoR-PR/applicable pre-merge PR DoD satisfied, and no unresolved blocking CHANGES_REQUESTED or invariant violation. A new commit, a label, reviewer absence or an owner override cannot silently clear a blocking finding. A reviewer must clear the finding with attributable resolution; ambiguous dismissal alone is insufficient. Approval count zero never means failed CI, missing evidence or an unresolved finding may be bypassed. Post-merge DoD remains post-merge.

All development review matrices/owner/consumer/research routing statements are expertise guidance for normal-risk PRs, not additional approval quotas. Independent semantic acceptance/final-protocol/freeze obligations remain at their actual acceptance gates; they do not impose a blanket GitHub approval on ordinary research implementation. Product runtime HITL, protected-action approval/binding, manufacturing authority and verification obligations are unchanged. Merged != Done; Implemented != Tested; Tested != Verified; Demoed != Accepted. Historical reviews remain bound to their real revisions; no new approval or product completion is inferred.
