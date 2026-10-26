# WP-CORE-003 — accountable start readiness assessment

Accountable owner: Asrın Dündar (Asperant). Supporting reviewer: Batuhan Kaya
(advisory; CHG-018 requires zero development PR approvals). Assessment basis:
current canonical main `913a90a464bb17f195eeaaee4920458daaa92c22`.

This is a START/DoR assessment for the first owner-executable contract-first
slice only. It does not claim that `DN-CORE-CMDCON` is `CONTRACT_READY`, that
`DN-CORE-CMDEXEC` is `INTEGRATION_READY`, or that the complete WP is done.

## Canonical scope and slice

Scope: FR-CORE-004, FR-CORE-005, FR-CORE-006 and FR-CORE-016; M2/S3–S4;
readiness node `DN-CORE-CMDEXEC`.

The first owner-executable slice is the producer slice for
`DN-CORE-CMDCON`: versioned hold/release/dispatch/maintenance-request command
schemas, stable command/version identity, compatibility/example fixtures and
producer/consumer contract tests. Later idempotency, revision/freshness and
durable `CommandOutcome` execution behaviour remains in the subsequent
capability slice.

## START dependency interpretation

`DEP-027` and `DEP-028` are both canonical `INTEGRATION`-stage HARD edges.
They are not START blockers for this first producer slice. No START-stage
contract or dependency is consumed by the slice, so no predecessor readiness
or F1 fallback is asserted. The later capability must still satisfy:

- DEP-027: `CONTRACT_READY` with the precise command-contract evidence defined
  in `docs/05_Dependency_Graph.md`;
- DEP-028: `INTEGRATION_READY` with the legal/illegal transition evidence
  defined in `docs/05_Dependency_Graph.md`.

## DoR assessment

| Criterion | Result | Current-main evidence / limitation |
|---|---|---|
| DOR-TASK-01 | PASS | Outcome, M2/S3–S4 target and `DN-CORE-CMDEXEC` are canonical in `docs/04_Work_Breakdown_Structure.md`. |
| DOR-TASK-02 | PASS | FR-CORE-004/005/006/016 are linked in WBS and RTM; wording is unchanged. |
| DOR-TASK-03 | PASS | Asrın Dündar is the single owner and Batuhan Kaya is the supporting reviewer in the canonical WBS/CODEOWNERS routing. |
| DOR-TASK-04 | N/A for START slice | No inbound HARD edge has `blocking_stage: START`; DEP-027/028 are explicitly INTEGRATION. No fallback or predecessor readiness is claimed. |
| DOR-TASK-05 | PASS for producer slice | The slice produces `DN-CORE-CMDCON`; it does not consume a START-stage contract. Contract publication/readiness remains future evidence. |
| DOR-TASK-06 | PASS | Slice deliverables and testable acceptance obligations are enumerated in the WBS major tasks/deliverables. |
| DOR-TASK-07 | PASS | TEST-CORE-CONTRACT, TEST-EVT-SCHEMA and the producer/consumer contract-test obligation are named in the WBS/RTM. |
| DOR-TASK-08 | PASS | Scope class is F1; risk hook is AUTO-R01 and the authority/schema change risk is reassessed per CHG-018/CR-3 practice. |
| DOR-TASK-09 | PASS | Core authority, command contract and versioning boundaries are specified in `docs/02_System_Architecture_Specification.md`; CHG-042 resolves the prior WP-level circular gate. |
| DOR-TASK-10 | PASS | The contract-first slice is explicitly separated from later persistence/idempotency capability work in the WBS. |
| DOR-TASK-11 | PASS | No START blocker is known; later INTEGRATION dependencies are declared and are not silently cleared. |
| DOR-TASK-12 | N/A | This is F1 product work, not R1 research. |

## WP-level mapping

| Criterion | Result | Evidence |
|---|---|---|
| DOR-WP-01 | PASS | Current requirements are listed in the WBS/RTM. |
| DOR-WP-02 | PASS | M2/S3–S4 and `DN-CORE-CMDEXEC` are canonical planning targets. |
| DOR-WP-03 | PASS | No START-stage inbound HARD dependency; DEP-027/028 remain later-stage gates. |
| DOR-WP-04 | N/A for START slice | No predecessor artifact is consumed at START; later precise requirements are retained in DEP-027/028. |
| DOR-WP-05 | PASS for producer slice | The slice produces the command contract; no contract readiness is fabricated. |
| DOR-WP-06 | PASS | Verification families and boundary obligations are named in WBS/RTM. |
| DOR-WP-07 | PASS | Owner/reviewer and routing are canonical. |
| DOR-WP-08 | N/A | F1, not R1 research. |

## Evidence boundary and readiness result

This artifact is an accountable assessment of canonical DoR applicability; it
is not implementation or contract-readiness evidence. `check-ready` remains
fail-closed until its trusted execution-evidence input exists, so no READY
transition is authorized by this document alone.
