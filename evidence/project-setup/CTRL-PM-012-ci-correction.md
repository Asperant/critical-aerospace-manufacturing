CONTROL ITEM: CTRL-PM-012 (corrective follow-up discovered during CTRL-PM-015)
GOAL: Preserve imported setup specification rendering while satisfying the unchanged real PR whitespace gate.
RESULT: PASS for corrected local source/whitespace acceptance; subsequent real CI recorded in the rehearsal snapshot.
FILES CHANGED: project_control/PROJECT_SETUP_MASTER_EXECUTION_SPEC.md lines3–6; this report; CTRL-PM-012-ci-failure.json.
TESTS RUN: Full projectctl suite; canonical validate; git diff --check main; docs/AGENTS unchanged; literal source comparison proving only four Markdown hard breaks changed; secret/staged-content checks; subsequent real head/PR CI.
TEST RESULTS: 144 tests passed in61.97s; canonical validation PASS; git diff --check main PASS; exact four-line rendering comparison PASS; docs/AGENTS unchanged and secret scan PASS. Actual failed PR run38187728392 had passing tests/validation and failed only git diff --check on four pre-existing imported hard breaks. Check is unchanged; no exclusion or tolerance introduced.
VALIDATION RESULT: PASS after correction; canonical documentation untouched.
OBSERVED INVARIANTS: All existing counts and live Plane audit unchanged; modification has no parser, instruction or requirement semantics effect.
PLANE READS: NONE
PLANE MUTATIONS: NONE
GITHUB MUTATIONS: Authorized corrective checkpoint push and real CI, recorded on completion; no merge or fabricated review.
NETWORK MUTATIONS: GitHub checkpoint only.
KNOWN LIMITATIONS: Independent reviews, human identities and supported protection remain pending. A corrective atomic follow-up is required after discovery in real PR CI; previous commits are preserved, not amended or rewritten. CTRL-PM-015 remains partial and is not committed as complete.
SPEC CONFLICTS: No canonical conflict. Four verbatim imported Markdown hard breaks were trailing spaces; explicit HTML breaks retain rendering while preserving every execution instruction. Change is transparently editorial outside docs/; original failure remains recorded.
COMMIT SHA: Resolve containing corrective commit using git log -1 --format=%H -- evidence/project-setup/CTRL-PM-012-ci-correction.md.
NEXT CONTROL ITEM: Continue final CTRL-PM-015 CI observation; do not merge without genuine review/approval.
