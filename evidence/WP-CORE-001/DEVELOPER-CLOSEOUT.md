# WP-CORE-001 — developer-side closeout

Owner: Asrın Dündar (Asperant). Branch: `wp/WP-CORE-001-domain-model`.
PR: https://github.com/Asperant/critical-aerospace-manufacturing/pull/24

Domain, PostgreSQL migration/role separation, repository, typed v1 query and
fixtures remain as evidenced by SLICE1.md through SLICE3.md. This closeout adds
the Core-owned DOD-WP-06 internal health surface and structured correlation,
outcome and duration logging without transport, authority or contract changes.
Local service suite: 85 passed; 31 real-PostgreSQL cases deselected. Ruff
lint/format, Pyright (0 errors/0 warnings) and diff hygiene passed. New real
health/role/correlation cases await the current-head PostgreSQL 18 CI result.

## Acceptance classification

E2E-01 is a later CK-E2E01/MILESTONE_EXIT checkpoint (producer WP-TEST-006,
Batuhan); AV-SCEN-01/02 are later integration scenario evidence (producer
WP-TEST-003, Asrın, DN-SIM-COREINT). They are not inbound CORE-001 START gates.
The F0 supplement requires participation in a real integrated acceptance path;
it does not independently require all three named scenarios before local
implementation/review/merge can proceed. This refines the overly broad wording
in FINAL-ACCEPTANCE-GAPS.md while preserving its actual evidence limitation.

DOD-WP-05/F0 final acceptance still requires attributable real integrated and
post-merge infrastructure/consumer evidence. Development fixtures do not satisfy
that obligation. Proposed post-merge waiting reason:
`WAITING_DOWNSTREAM_INTEGRATED_ACCEPTANCE_EVIDENCE`.
Target projection is VALIDATING plus orthogonal BLOCKED, never DONE.

## Remaining operational facts, not completion claims

Installed resolver `ACTIVE` includes VALIDATING unconditionally. It presently
does not exempt an evidenced external acceptance wait from automatic-release
WIP. A release exemption changes existing CHG-019/CHG-021 policy and needs its
own scoped change record/branch, focused guards, merged source and privileged
installed policy/helper refresh. No such correction is mixed into the Core PR.
No automatic next READY, deployment, or final acceptance is claimed here.

PR trace declares FR-CORE-001/002 REALIZED_BY the domain/migration/query artifacts
and FR-CORE-013 by restricted Core role/schema ownership; VERIFIED_BY actual
focused suites at their recorded source revisions. Final requirement VERIFIED
coverage is withheld. No evidence source, canonical requirement or DoD is
rewritten to match an unverified implementation outcome.
