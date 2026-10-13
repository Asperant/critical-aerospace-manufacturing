CONTROL ITEM: CTRL-PM-003
GOAL: Parse dependency registry and YAML mirrors, validate structure and preserve semantic findings.
FILES CHANGED: dependency models/parser/validator/tests; safe YAML reader; loader/catalog/CLI; PyYAML dependency; this report.
TESTS RUN: python -m pytest tools/projectctl/tests -q; projectctl validate --json; git diff --check; git status --short; git diff --exit-code -- docs/.
TEST RESULTS: 39 passed; diff checks passed; docs unchanged.
VALIDATION RESULT: PASS for offline structure, with semantic warnings.
OBSERVED INVARIANTS: 100 nodes, 217 edges, 208 HARD, 9 SOFT, zero HARD cycles; previous WBS/schedule invariants retained.
PLANE READS: NONE
PLANE MUTATIONS: NONE
GITHUB MUTATIONS: NONE
NETWORK MUTATIONS: Local environment package installation only (PyYAML and editable project install).
KNOWN LIMITATIONS: No dependency satisfaction or execution-state evaluation. Semantic findings do not grant readiness or unblock authorization.
SPEC CONFLICTS: Two incompatible readiness declarations (DEP-060/194); 179 null HARD precision fields; five F1/non-CONTRACT declarations; 29 unresolved need-by expressions. All preserved as diagnostics, not repaired.
COMMIT SHA: Resolve the commit containing this report with git log -1 --format=%H -- evidence/project-setup/CTRL-PM-003.md.
NEXT CONTROL ITEM: CTRL-PM-004
