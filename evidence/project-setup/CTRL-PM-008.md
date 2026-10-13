CONTROL ITEM: CTRL-PM-008
GOAL: Complete the explicitly approved structural bootstrap with serialized request pacing, bounded retry/reconciliation and preserved partial-attempt history.
RESULT: PASS for CTRL-PM-008. Overall setup remains INCOMPLETE; CTRL-PM-009 is not started or approved.
FILES CHANGED: tools/projectctl/README.md; src/projectctl/{plane.py,plane_transport.py,plane_bootstrap.py}; tests/{conftest.py,test_plane_transport.py,test_plane_bootstrap.py}; all CTRL-PM-008 evidence listed below. Canonical docs and AGENTS.md unchanged.
TESTS RUN: Complete projectctl suite before resumed application; focused transport/bootstrap suite; complete suite after application; projectctl validate --json before/after; fresh complete Plane preflight and post-apply audits; structural bootstrap planner over fresh inventory; git diff --check (including staged files); git status --short; git diff --exit-code -- docs/ AGENTS.md; ignored-local-config and credential-content checks.
TEST RESULTS: Full suite 104 passed in 41.37s before resume and 104 passed in 41.11s after application; focused suite 30 passed in 17.76s. No real Plane network calls in tests. Fresh live acceptance and structural idempotency passed. Diff/hygiene/secret checks passed.
VALIDATION RESULT: PASS; execution_status remains UNAVAILABLE (documentation only).
OBSERVED INVARIANTS: 179 WPs; owners Asrın 73,Selman 17,Batuhan 32,Yavuz 57; 29 areas; 306 requirements (186 FR,120 NFR); 100 dependency nodes; 217 edges (208 HARD,9 SOFT); zero HARD cycles; 174 scheduled/exact five unscheduled; S1–S13; M0–M8. Canonical parsers, models, validators and planning semantics unchanged.
PLANE READS: API v1 only, X-API-Key authentication. Fresh complete inventory before resume and before each mutation family; exact inventory before/after creates; full workflow/BLOCKED comparison; fresh final audit. Application helper used 146 GETs and 43 POSTs (189 serialized requests, zero 429s). Preflight and final audits added 24 GETs. Workspace direct endpoint remains 401; workspace identity checked through project scope. Installed Plane source inspected read-only for future import-contract analysis.
PLANE MUTATIONS: Attempt 1: one verified state PATCH and eight verified module POSTs; one additional module POST rejected with 429. Attempt 2: exactly 43 verified POST creates (21 modules,13 undated cycles,9 milestone labels), no repeated state PATCH or repeated module creates. Total successful approved mutations across attempts: 52. Total mutation HTTP attempts: 53, including the historical rejected POST. No issue/member/relationship/date/delete writes.
GITHUB MUTATIONS: NONE
NETWORK MUTATIONS: Only the above approved Plane mutations. No package installation or push.
KNOWN LIMITATIONS: Pacing/serialization is process-wide; other clients can consume Plane's shared API-key budget, so server wait headers remain authoritative. Missing members and 117 unresolved native cycle choices remain explicit future-import blockers. Live issue/association idempotency and HTML metadata round-trip are not proven by structural idempotency. Direct workspace details unavailable. Architecture-reference existence against docs/02 is still outside current offline validation coverage.
SPEC CONFLICTS: Approved IN_REVİEW typo correction is complete. No structural conflicts remain. All 947 canonical warnings remain visible; none repaired or weakened. Canonical multi-cycle windows remain unmodified; policy proposal is unapproved read-only analysis.
COMMIT SHA: Resolve the atomic containing commit with git log -1 --format=%H -- evidence/project-setup/CTRL-PM-008.md.
NEXT CONTROL ITEM: CTRL-PM-009 is withheld. HUMAN_APPROVAL_REQUIRED: WP_IMPORT_POLICY, explicitly required by the user's bounded CTRL-PM-008 resume instruction.

Attempts and evidence:

- Attempt 1 stopped immediately on HTTP 429 for WP-GOV after one state PATCH and eight module creates. Original report preserved as CTRL-PM-008-attempt-1.md; original CTRL-PM-008-before.json, CTRL-PM-008-application.json and CTRL-PM-008-partial-audit.json remain unchanged. No rollback occurred.
- Attempt 2 added centralized pacing/retries and re-read the complete live inventory before applying anything. The eight prior module IDs and corrected state ID matched; BLOCKED matched; no cycles, milestone labels or work items existed. Desired-vs-observed projection found exactly 43 missing structures. Evidence: CTRL-PM-008-attempt-2-before.json, CTRL-PM-008-attempt-2-application.json and CTRL-PM-008-after.json. Every returned Plane entity ID, request method/path/body/status and safe timing/header telemetry is recorded without credentials.
- Independent final read-only acceptance: CTRL-PM-008-post-audit.json. The structural planner output is CTRL-PM-008-structural-dry-run.json.
- Read-only future-policy analysis: CTRL-PM-008-wp-mapping-analysis.json contains the exact 57 single-cycle,117 multi-cycle and five unscheduled WP lists and original windows; CTRL-PM-008-wp-import-policy.md contains the unapproved policy and exact proposed mutation budget.

Before/after counts:

| Resource | Before attempt 1 | Before attempt 2 | Final |
|---|---:|---:|---:|
| Workflow states | 9 | 9 | 9 |
| Desired modules | 0 | 8 | 29 |
| Desired cycles | 0 | 0 | 13 |
| Milestone labels | 0 | 0 | 9 |
| BLOCKED labels | 1 | 1 | 1 |
| Work items / imported canonical WPs | 0 | 0 | 0 |

Workflow acceptance: IN_REVIEW exists exactly once, IN_REVİEW absent; ID 99a0cc57-ec65-4c3d-8db4-694ce31c77fa preserved. Attempt 1 verified group started,sequence 70000.0,color #f59e0b,slug in_review and all other semantic fields; only API-managed updated_at/updated_by bookkeeping excluded. Attempt 2 full raw workflow before/after is exactly equal. BLOCKED full raw before/after is exactly equal. Module IDs from attempt 1 are preserved.

Structural acceptance: exactly 29 desired module names, exactly S1–S13 with null dates, exactly MS:M0–MS:M8 plus BLOCKED, no duplicates or unexpected structures, zero work items. Fresh live structural dry-run: creates 0,required updates 0,conflicts 0,unchanged 52. This proves CTRL-PM-008 live idempotency; it does not certify future WP import readiness.

Rate-limit handling: all reads/writes use one PlaneStream request path with a process-wide lock and minimum 1.25 seconds between request starts (default below 60/minute). Optional non-secret PLANE_REQUEST_INTERVAL_SECONDS may increase the interval; local secret file was not edited. GET/idempotent approved name-PATCH requests retry at most five times on 429. Retry-After seconds/HTTP dates take precedence, then X-RateLimit-Reset, then bounded exponential backoff 2–30s. Remaining=0 defers subsequent requests. POSTs do not blindly retry: after required wait, fresh inventory reconciles one exact intended entity, permits bounded retry if absent, and stops on duplicates/conflicts. Tests prove time waits, exhaustion, ambiguous success, no duplicate replay and no overlapping requests. No rate limit configuration was weakened.

Missing members: Selman Özdemir (17 WPs),Batuhan Kaya (32),Yavuz Gümüş (57). Asrın Dündar maps only to his own 73 WPs. No invitations, assignments or owner substitutions occurred. Final project GET confirms default_assignee=null; recheck before any future import.

Proposed future policy: preserve each full canonical planning window; distinguish native coordination cycle as a separately human-approved per-WP operational choice. Map 57 single-cycle WPs directly; require 117 explicit native-cycle choices within their canonical windows before a full import. Keep WP-R2-001,WP-R2-002,WP-R2-003,WP-S-001,WP-X-001 unscheduled. Do not guess first/last cycle or duplicate issues. Recommended full-import budget after approvals: 179 issue POSTs +179 single-WP module-association POSTs +174 single-WP cycle-association POSTs =532 intended successful writes; labels/verified assignees/BACKLOG included in issue creation. This proposal is not executable until mappings and live API contracts are resolved. No CTRL-PM-009 code was implemented.

Security and Git: ignored local credentials remained unchanged; API key not printed/logged/staged/committed. Credential-content checks passed. Generated egg-info and caches remain ignored. No canonical docs changes or deletions. Only this completed control item is committed atomically on setup/project-management-bootstrap; no push.
