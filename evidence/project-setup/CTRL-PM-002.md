CONTROL ITEM: CTRL-PM-002
GOAL: Parse and cross-check cycle, milestone and owner-roadmap planning data.
FILES CHANGED: schedule models/parser/validator/tests; CLI, loader, catalog; supplied execution spec copied unchanged to intended project_control path; this report.
TESTS RUN: python -m pytest tools/projectctl/tests -q; projectctl validate --json; git diff --check; git status --short; git diff --exit-code -- docs/.
TEST RESULTS: 34 passed; diff checks passed; docs unchanged.
VALIDATION RESULT: PASS.
OBSERVED INVARIANTS: 179 WPs, owners 73/17/32/57, 29 areas, 13 cycles, 9 milestones, 174 scheduled, exact 5 unscheduled.
PLANE READS: NONE
PLANE MUTATIONS: NONE
GITHUB MUTATIONS: NONE
NETWORK MUTATIONS: NONE
KNOWN LIMITATIONS: Calendar dates absent; multi-cycle windows remain multi-cycle planning memberships; execution status unavailable. Original user-supplied root specification remains untracked and untouched.
SPEC CONFLICTS: NONE affecting this item.
COMMIT SHA: Resolve the commit containing this report with git log -1 --format=%H -- evidence/project-setup/CTRL-PM-002.md.
NEXT CONTROL ITEM: CTRL-PM-003
