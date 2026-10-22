# WP-CORE-001 — accountable start readiness assessment

Accountable owner: Asrın Dündar (Asperant), recorded through the owner's authorized development workflow. Supporting reviewer: Batuhan Kaya (Ejlonn), advisory; CHG-018 requires zero development PR approvals. This is a START/DoR assessment only. Immutable assessment revision is the containing merged Git commit; the owner-attributed GitHub evidence comment binds the actual current main SHA after merge.

## Scope and initial workstream slice

Canonical scope: FR-CORE-001, FR-CORE-002, FR-CORE-013; M1/S2; DN-CORE-CONTRACTS. Core is the semantic authority for orders, lots, serialized components, routes/operations and equipment references, with distinct operation-class and repeated visit identity. No inbound edge exists in the canonical dependency graph. No external contract/runtime readiness is being certified.

Large WP is a workstream, not a claim of a three-day whole-WP delivery. Internal slices (each planned as a coherent 0.5–3 focused-day item; re-slice if discovery exceeds that):

1. **Start slice**: implement only pure canonical domain values/entities, identity/revision validation and route operation-class versus visit representation, plus focused tests under `services/manufacturing-core/`. No DB connection, migration, service endpoint or runtime integration in this slice.
2. Core-owned schema/migration representation and persistence tests after actual required runtime/role prerequisites are available. Coordinate platform migration runner/role wiring with WP-CORE-007; no platform ownership transfer.
3. Versioned Core query contract v1, example fixtures and compatibility/contract tests; publish real consumer artifacts before declaring CONTRACT_READY.
4. Component/integration/security and integrated scenario verification covering the full canonical WP DoD before any DONE assessment.

## Start-slice acceptance (planned, NOT executed)

- Model canonical order/lot/serialized component/equipment/route references with explicit identity and revision; reject malformed or missing identity/revision according to the canonical source, without silently inventing domain policy.
- Represent a repeated operation-class visit using distinct visit identity and preserve route ordering; focused tests cover a reentrant route and identity/revision round trip.
- Tests cover valid and invalid identity/revision inputs, reference consistency and the operation-class/visit distinction. Pure-domain tests require no live DB or other service.
- Core remains the sole canonical model authority; Simulator/Twin do not become independent authoritative copies. No cross-schema access or service credential is introduced by the first slice.
- Map actual cases to TEST-CORE-DOMAIN / TEST-CORE-GENEALOGY and boundary cases to TEST-ARCH-BOUNDARY; record real command outputs at the implementation revision. No test is reported passed by this preparation document.

The complete WP still requires domain modules, core schema migrations, query contract v1 plus fixtures, contract tests and applicable AV-SCEN-01/02, BENCH-E2E-001, E2E-01, TEST-AUTH-NEG and TEST-SEC-SVCID evidence. All implementation, migrations, schemas, APIs, tests, published contracts and DoD remain NOT_YET_EXECUTED / NOT_ACCEPTED here. Initial planning does not grant future dependency readiness or milestone acceptance.

## Architecture and known blockers

Follow docs/02 Core business/transactional authority and canonical data invariants; no new architecture decision is proposed. Implementation design details stay inside those boundaries. If a fundamental contradiction arises, stop that slice for the normal ADR/change-control path. No known external blocker applies to the pure initial slice. Database/runtime/role availability must be checked before the later persistence slice; this document does not declare them ready. Reassess actual authority/migration risk on each implementation PR.

## Canonical DoR assessment

| Criterion | Result | Assessment and evidence |
|---|---|---|
| DOR-TASK-01 | PASS | Owner Asrın Dündar; outcome, M1/S2, DN-CORE-CONTRACTS and the initial slice are declared below. repo:docs/04_Work_Breakdown_Structure.md repo:docs/03_Requirements_Traceability_Matrix.md |
| DOR-TASK-02 | PASS | FR-CORE-001, FR-CORE-002, FR-CORE-013 retain current canonical wording and trace; preparation adds no requirement. repo:docs/04_Work_Breakdown_Structure.md repo:docs/03_Requirements_Traceability_Matrix.md repo:requirements/catalog.json |
| DOR-TASK-03 | PASS | Single owner Asrın Dündar / Asperant; supporting reviewer Batuhan Kaya / Ejlonn, advisory under CHG-018. Explicit product and evidence routing added. repo:.github/CODEOWNERS |
| DOR-TASK-04 | PASS | Canonical WP context has zero incoming dependency edges, including HARD START. No predecessor requirement or fallback is assumed satisfied. repo:docs/05_Dependency_Graph.md |
| DOR-TASK-05 | PASS | This WP produces the Core query contract v1 and fixtures; the initial pure domain-model slice consumes no other service contract. No contract publication/readiness claimed. repo:docs/04_Work_Breakdown_Structure.md repo:docs/03_Requirements_Traceability_Matrix.md |
| DOR-TASK-06 | PASS | Testable start-slice acceptance cases and complete-WP remaining obligations are explicitly separated below. repo:evidence/WP-CORE-001/READY.md |
| DOR-TASK-07 | PASS | TEST-CORE-DOMAIN and TEST-CORE-GENEALOGY for the first pure-domain slice; TEST-ARCH-BOUNDARY for ownership; later integration/auth/scenario families remain pending. repo:docs/03_Requirements_Traceability_Matrix.md |
| DOR-TASK-08 | PASS | Preparation C0 / CR-1: documentation and advisory routing only. Product work conservatively CR-3 for authority/schema integrity; actual PR risk reassessed per CHG-018, zero development approvals. repo:09_change/CHG-018.yaml |
| DOR-TASK-09 | PASS | Initial slice follows existing canonical Core semantic authority and immutable identity/revision plus reentrant route/visit boundaries. No authority/technology decision is changed; a contradictory discovery stops the affected slice for ADR/change control. repo:docs/02_System_Architecture_Specification.md |
| DOR-TASK-10 | PASS | Large WP explicitly treated as a workstream with four coherent internal slices; first slice bounded to pure domain identity/revision/route-visit model and its tests, with no API/database migration/runtime work. repo:evidence/WP-CORE-001/READY.md |
| DOR-TASK-11 | PASS | No known START blocker for the pure domain slice; runtime database/grants readiness is required before later database integration and is not fabricated by this assessment. repo:evidence/WP-CORE-001/READY.md |
| DOR-TASK-12 | N/A | F0 product work, not R1 research; no dataset partition or FINAL access is required for readiness. repo:docs/04_Work_Breakdown_Structure.md repo:docs/03_Requirements_Traceability_Matrix.md |
| DOR-WP-01 | PASS | Current source requirements are listed and traced without wording changes. repo:docs/04_Work_Breakdown_Structure.md repo:docs/03_Requirements_Traceability_Matrix.md |
| DOR-WP-02 | PASS | M1 / S2 and DN-CORE-CONTRACTS are canonical planning targets, not wall-clock gates. repo:docs/04_Work_Breakdown_Structure.md repo:docs/03_Requirements_Traceability_Matrix.md |
| DOR-WP-03 | PASS | Zero inbound canonical edges; no HARD predecessor readiness assertion needed. repo:docs/05_Dependency_Graph.md |
| DOR-WP-04 | PASS | No predecessor artifacts consumed at START; producer contract obligations and exact identity/revision/visit expectations are specified for this workstream. repo:evidence/WP-CORE-001/READY.md |
| DOR-WP-05 | PASS | Core is the producer of the v1 query contract and fixtures. Producing them remains future implementation, not a readiness prerequisite already completed. repo:docs/04_Work_Breakdown_Structure.md repo:docs/03_Requirements_Traceability_Matrix.md |
| DOR-WP-06 | PASS | Named canonical test families and pure/integration boundary phases specified below. repo:docs/03_Requirements_Traceability_Matrix.md |
| DOR-WP-07 | PASS | Owner Asrın; supporting reviewer Batuhan. Exact product and evidence paths routed to Ejlonn; advisory only. repo:.github/CODEOWNERS |
| DOR-WP-08 | N/A | F0, not R1; partition/seed protocol research criterion is inapplicable. repo:docs/04_Work_Breakdown_Structure.md repo:docs/03_Requirements_Traceability_Matrix.md |
