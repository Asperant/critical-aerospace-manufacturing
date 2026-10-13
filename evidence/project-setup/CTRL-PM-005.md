CONTROL ITEM: CTRL-PM-005
GOAL: Unified deterministic offline project view with context and planning-only candidate queries.
FILES CHANGED: unified project model, queries, CLI, loader error handling, tests, tooling README; this report.
TESTS RUN: python -m pytest tools/projectctl/tests -q; projectctl validate --json; projectctl parse; projectctl context WP-CORE-001; projectctl next --owner Batu --cycle S2; projectctl status --json; git diff --check; git status --short; git diff --exit-code -- docs/.
TEST RESULTS: 50 passed in 17.51 seconds; command smoke checks passed; diff checks passed; docs unchanged.
VALIDATION RESULT: PASS for complete offline structural baseline, semantic warnings retained.
OBSERVED INVARIANTS: 179 WPs; owners 73/17/32/57; 29 areas; 306 requirements (186 FR, 120 NFR); 100 nodes; 217 edges (208 HARD, 9 SOFT); zero HARD cycles; 174 scheduled, exact 5 unscheduled; 13 cycles; 9 milestones.
PLANE READS: NONE
PLANE MUTATIONS: NONE
GITHUB MUTATIONS: NONE
NETWORK MUTATIONS: NONE
KNOWN LIMITATIONS: Architecture reference existence against 02 not checked. Multi-cycle planning membership is retained rather than choosing a Plane cycle. Execution state unavailable; next never certifies readiness. check-ready/check-done are deferred to CTRL-PM-013.
SPEC CONFLICTS: Existing dependency/source-gap/citation diagnostics remain visible; none repaired or treated as execution authorization.
COMMIT SHA: Resolve the commit containing this report with git log -1 --format=%H -- evidence/project-setup/CTRL-PM-005.md.
NEXT CONTROL ITEM: CTRL-PM-006; stop if Plane read configuration is absent.
