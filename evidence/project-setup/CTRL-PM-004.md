CONTROL ITEM: CTRL-PM-004
GOAL: Parse canonical 01 requirement definitions and separate 03 trace assertions; check WBS coverage references.
FILES CHANGED: requirement models/parser/validator/tests; loader/catalog/CLI; this report.
TESTS RUN: python -m pytest tools/projectctl/tests -q; projectctl validate --json; git diff --check; git status --short; git diff --exit-code -- docs/.
TEST RESULTS: 44 passed in 12.48 seconds; diff checks passed; docs unchanged.
VALIDATION RESULT: PASS for offline structure, with preserved source-gap/citation warnings.
OBSERVED INVARIANTS: 306 requirements, 186 FR (17 F0/159 F1/10 R1), 120 NFR (52 H0/41 A1/23 S2/4 C3); WBS references resolve; RTM class/owner assertions agree; prior invariants retained.
PLANE READS: NONE
PLANE MUTATIONS: NONE
GITHUB MUTATIONS: NONE
NETWORK MUTATIONS: NONE
KNOWN LIMITATIONS: Missing canonical per-record fields remain null. Planned RTM expectations are not executed evidence. No dataset-domain reinterpretation.
SPEC CONFLICTS: 306 stale citations; 306 per-record revision/status gaps; 120 NFR structured-metadata gaps, all visible diagnostics. Existing dependency findings retained.
COMMIT SHA: Resolve the commit containing this report with git log -1 --format=%H -- evidence/project-setup/CTRL-PM-004.md.
NEXT CONTROL ITEM: CTRL-PM-005
