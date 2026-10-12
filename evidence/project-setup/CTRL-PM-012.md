CONTROL ITEM: CTRL-PM-012
GOAL: Establish real projectctl CI and canonical engineering PR conventions.
RESULT: PASS for repository workflow setup; supported-plan branch protection is unavailable, explicitly reported.
FILES CHANGED: .github/pull_request_template.md; .github/workflows/projectctl.yml; project_control/ENGINEERING_WORKFLOW.md; this report.
TESTS RUN: Complete projectctl suite; projectctl validate --json; compileall; fresh Plane GET-only discovery; git diff --check; git diff --exit-code -- docs/ AGENTS.md; git status --short; ignored-local-secret and staged-path checks; workflow YAML inspection.
TEST RESULTS: 129 passed in 59.16s (preflight 129 passed in 59.93s); syntax and hygiene passed. GitHub execution will be recorded separately after authorized checkpoint push.
VALIDATION RESULT: PASS, existing 947 warnings preserved; execution status UNAVAILABLE (documentation only).
OBSERVED INVARIANTS: 306 requirements (186 FR/120 NFR); 179 WPs; owners 73/17/32/57; 29 areas; 100 nodes/217 edges/208 HARD/9 SOFT/0 HARD cycles; 174 scheduled/exact five unscheduled; 13 cycles/9 milestones. Fresh Plane discovery: 179 items/29 modules/13 cycles/9 states/10 labels/one project member.
PLANE READS: Fresh explicit v1 discovery, GET only; no imports or transitions.
PLANE MUTATIONS: NONE
GITHUB MUTATIONS: Local PR template and CI configuration; checkpoint push authorized by master §10, execution observed in later evidence. Read repository permissions, Actions availability and main protection. No protection mutation: private repository plan returns HTTP 403, despite admin permission.
NETWORK MUTATIONS: No live mutation before this commit; subsequent checkpoint push recorded separately.
KNOWN LIMITATIONS: Current GitHub plan lacks private-repository branch protection. Required checks and independent reviews remain mandatory; human must enable supported protection. CODEOWNERS routing awaits verified teammate GitHub usernames. No product tests fabricated. CI and final PR execution remain to be observed in rehearsal.
SPEC CONFLICTS: Existing findings unchanged; none newly blocking this control. Partial CTRL-PM-011 files intentionally excluded from this completed item's commit.
COMMIT SHA: Resolve containing commit using git log -1 --format=%H -- evidence/project-setup/CTRL-PM-012.md.
NEXT CONTROL ITEM: CTRL-PM-013.
