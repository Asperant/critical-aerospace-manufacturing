CONTROL ITEM: CTRL-PM-013
GOAL: Read-only fail-closed DoR/DoD commands without a second execution database.
RESULT: PASS for this bounded support increment.
FILES CHANGED: tools/projectctl/src/projectctl/gates.py and cli.py; tests/test_gates.py; tooling README; this report.
TESTS RUN: Full projectctl suite including 11 new gate tests; projectctl validate --json; check-ready/check-done WP-AI-007; git diff --check; docs/AGENTS unchanged; ignored-secret and staged-content checks. Fresh v1 Plane discovery from CTRL-PM-012 reused within this run; commands themselves are offline.
TEST RESULTS: 140 passed in 62.38s. Both real command checks return UNKNOWN and exit 1. Negative paths cover unknown/malformed identities, invalid baseline, unavailable governance, denied network/writes and deterministic output. Baseline validation PASS.
VALIDATION RESULT: PASS; 947 prior warnings unchanged, execution status remains UNAVAILABLE (documentation only).
OBSERVED INVARIANTS: All canonical baseline counts retained: 306/186/120 requirements, 179 WPs, owners 73/17/32/57, 29 areas, 100 nodes, 217 edges (208 HARD/9 SOFT), zero HARD cycles, 174 scheduled/exact five unscheduled, 13 cycles/9 milestones.
PLANE READS: No additional reads needed for offline commands; preceding same-run read-only discovery passed.
PLANE MUTATIONS: NONE
GITHUB MUTATIONS: NONE within this control item. Prior checkpoint push launched actual CI; recorded in final rehearsal evidence.
NETWORK MUTATIONS: NONE
KNOWN LIMITATIONS: No trusted execution-evidence adapter is implemented. Current valid WPs always return UNKNOWN; PASS is reserved and cannot be fabricated from planning prose. Invalid canonical identity/baseline yields FAIL. Source-bound WP DoR/DoD references and docs/08 hash are emitted, with all applicable level/scope supplements still required. No transition support or automatic READY/DONE. Human confirmations and actual dependency/contract readiness, CI/reviews, post-merge validation, trace and accepted identity-bound evidence remain necessary.
SPEC CONFLICTS: Existing source warnings preserved; no new conflicts or governance changes.
COMMIT SHA: Resolve containing commit using git log -1 --format=%H -- evidence/project-setup/CTRL-PM-013.md.
NEXT CONTROL ITEM: CTRL-PM-014; partial CTRL-PM-011 remains pending human identities.
