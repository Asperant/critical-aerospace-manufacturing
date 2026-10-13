CONTROL ITEM: CTRL-PM-006
GOAL: Explicit, GET-only Plane API v1 discovery with safe local configuration and identity verification.
FILES CHANGED: tools/projectctl/{pyproject.toml,README.md,src/projectctl/cli.py,src/projectctl/plane.py,tests/test_plane.py}; this report and CTRL-PM-006-plane-audit.json.
TESTS RUN: python -m pytest tools/projectctl/tests -q; projectctl plane-audit; projectctl validate --json; git diff --check; git status --short; git diff --exit-code -- docs/.
TEST RESULTS: 67 passed in 17.70 seconds. Mock transport proves GET-only v1, no redirects/version fallback, pagination completeness, identity checks and redacted errors. Live discovery succeeded. Diff checks passed; docs unchanged.
VALIDATION RESULT: PASS for canonical offline baseline. Discovery passed; Plane conformity is not asserted.
OBSERVED INVARIANTS: 179 WPs; owners 73/17/32/57; 29 areas; 306 requirements (186 FR,120 NFR); 100 nodes; 217 edges (208 HARD,9 SOFT); zero HARD cycles; 174 scheduled/exact five unscheduled; 13 cycles; nine milestones. Execution status remains UNAVAILABLE (documentation only).
PLANE READS: GET-only preflight and 11 adapter discovery requests. Authenticated user verified; configured project Graduation Project / CAP, beb6dbea-4931-4ce9-b761-a4957c4b33be. Workspace critical-aerospace-manufacturing, 8df81c6e-d0f9-43af-ab75-7c5f01c6b9bb verified through scoped project listing. Observed nine states, one BLOCKED label, zero modules/cycles/work items, one workspace member and one project member (Asrın).
PLANE MUTATIONS: NONE
GITHUB MUTATIONS: NONE
NETWORK MUTATIONS: Local environment package installation only (httpx and dependencies, editable project install).
KNOWN LIMITATIONS: Direct workspace GET returns 401; direct workspace details unavailable, identity verified through project scope. No live execution data inferred. Audit is a sanitized dated-by-commit evidence snapshot; re-read before any future mutation. API v2 intentionally unsupported.
SPEC CONFLICTS: Plane state IN_REVİEW (U+0130) differs from canonical IN_REVIEW (U+0049); exact-name reconciliation is deferred to dry-run. Missing three team members. Existing canonical warnings unchanged.
COMMIT SHA: Resolve containing commit with git log -1 --format=%H -- evidence/project-setup/CTRL-PM-006.md.
NEXT CONTROL ITEM: CTRL-PM-007 (dry-run only).
