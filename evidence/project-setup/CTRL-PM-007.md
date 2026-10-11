CONTROL ITEM: CTRL-PM-007
GOAL: Deterministic Plane bootstrap dry-run, preserving canonical metadata and exposing unsafe/unresolved mappings without mutation.
FILES CHANGED: tools/projectctl/src/projectctl/{plane_plan.py,cli.py}; tools/projectctl/tests/test_plane_plan.py; tools/projectctl/README.md; this report; CTRL-PM-007-bootstrap-preview.json; CTRL-PM-007-findings.json.
TESTS RUN: python -m pytest tools/projectctl/tests -q; projectctl plane-plan --audit evidence/project-setup/CTRL-PM-006-plane-audit.json; projectctl validate --json; projectctl status --json; fresh GET-only Plane audit compared with CTRL-PM-006 evidence; git diff --check; git status --short; git diff --exit-code -- docs/; credential-content check on intended commit files.
TEST RESULTS: 74 passed in 24.07 seconds. Initial new-test fixture scope error corrected; no assertions weakened. Pure simulated second application produces 231 unchanged static entities, zero creates and zero updates; existing IN_PROGRESS/DONE state is preserved. Offline CLI denies network and writable opens. Diff checks passed; docs unchanged; fresh Plane audit unchanged; secret-content check passed.
VALIDATION RESULT: PASS for canonical offline baseline. Dry-run generation passed with explicit conflicts/ambiguities; ready_for_live_mutation=false. This is completion of the planner, not approval or completion of bootstrap/import.
OBSERVED INVARIANTS: 179 WPs; owners Asrın Dündar 73, Selman Özdemir 17, Batuhan Kaya 32, Yavuz Gümüş 57; 29 areas; 306 requirements (186 FR,120 NFR); 100 nodes; 217 edges (208 HARD,9 SOFT); zero HARD cycles; 174 scheduled/exact five unscheduled; S1-S13; M0-M8. Execution status remains UNAVAILABLE (documentation only).
PLANE READS: Fresh 11-request GET-only audit, unchanged from CTRL-PM-006. Planner itself reads only the explicitly supplied sanitized snapshot.
PLANE MUTATIONS: NONE
GITHUB MUTATIONS: NONE
NETWORK MUTATIONS: NONE
KNOWN LIMITATIONS: Direct workspace GET remains 401; verified project-scope identity only. Static projection idempotency proven in simulation; live relationship idempotency unproven. No apply or sync command. Symbolic structure references must resolve after a fresh audit. Module/cycle/label relationship entries are intended mappings, not executable requests; v1 association contracts must be checked before live application. Calendar dates absent; no dates invented; undated-cycle API acceptance must be checked. Existing item relation metadata requires a fresh relation audit rather than guessing. Missing members remain unassigned, with canonical owner names preserved. No copied local PM-state database.
SPEC CONFLICTS: Canonical AGENTS.md workflow IN_REVIEW conflicts with Plane state 99a0cc57-ec65-4c3d-8db4-694ce31c77fa named IN_REVİEW (U+0130). Planner returns two exact findings: missing IN_REVIEW and noncanonical IN_REVİEW. No rename proposed or executed. 117 multi-cycle WPs cannot deterministically map to one Plane cycle: e.g. WP-VIS-001 is in S3 and S4 in docs/07 §6.S3/§6.S4 (lines 1414/1461), with S3–S4 window in docs/04 and owner roadmap docs/06B; no approved single-cycle selection rule exists. This is an unresolved projection policy, not repaired canonical data. Three project members unavailable: Batuhan Kaya (32 WPs), Selman Özdemir (17), Yavuz Gümüş (57). Exact affected IDs and all findings are in the JSON evidence. Existing 947 canonical warnings preserved: precision missing 179; need-by ambiguous 29; fixture semantics 5; readiness incompatible 2 (DEP-060/194); requirement revision/status gaps 306; NFR metadata gaps 120; stale citations 306.
COMMIT SHA: Resolve containing commit with git log -1 --format=%H -- evidence/project-setup/CTRL-PM-007.md.
NEXT CONTROL ITEM: CTRL-PM-008; HUMAN_APPROVAL_REQUIRED: FIRST_PLANE_MUTATION under master execution specification §9 H3. Do not execute the preview without explicit approval and resolving applicable blockers.

Mutation preview (intent only; every operation and canonical mapping is enumerated in CTRL-PM-007-bootstrap-preview.json):

| Entity | Create | Update | Unchanged |
|---|---:|---:|---:|
| Modules (stable capability IDs; title in description) | 29 | 0 | 0 |
| Cycles S1–S13 (no invented calendar dates) | 13 | 0 | 0 |
| Milestone labels MS:M0–MS:M8 | 9 | 0 | 0 |
| BLOCKED label | 0 | 0 | 1 |
| Canonical WP issues, creation policy BACKLOG | 179 | 0 | 0 |
| Total | 230 | 0 | 1 |

CTRL-PM-008 structural scope is 51 proposed creates. The 179 WP creates are later CTRL-PM-009 scope and cannot be applied as a fully resolved import yet. There are no proposed state renames, state additions, invitations, deletes, requirement items, dependency-node items or blocker links.

Owner mapping: Asrın Dündar -> project member 0b4a5417-2ed5-4ac2-95ff-e74104c5d601 (73 WPs); the other three owners map to null (106 WPs), never another person.

Scheduling: 57 single-cycle mappings resolved; 117 two-cycle windows preserved and flagged; all 174 scheduled WPs remain scheduled in canonical metadata. Exact unscheduled IDs: WP-R2-001, WP-R2-002, WP-R2-003, WP-S-001, WP-X-001. These five have null intended Plane cycles. No duplicate canonical IDs or unmanaged existing work items observed.

Repository canonical documents and local ignored credential file remain unchanged. Setup is incomplete; no CTRL-PM-008–015 work or live mutation has started.
