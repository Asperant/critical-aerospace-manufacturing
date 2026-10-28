# WP-CICD-002 — accountable start readiness assessment

Accountable owner: Yavuz Gümüş (Yavuzgmus). Supporting reviewer: Asrın Dündar
(advisory; CHG-018 requires zero development PR approvals). Assessment basis:
current canonical main `565c517ffd3acc9194259ad752f08d0855d25cdc`.

This is a START/DoR assessment for WP-CICD-002 (F0, M1, readiness node `DN-PLAT-CD`;
requirements FR-PLAT-004, FR-PLAT-005 and NFR-DEP-003). Under CHG-054,
`projectctl startability WP-CICD-002` returns STARTABLE at this revision after CHG-076
resolved DEP-002. It claims no implementation and no acceptance: WP-CICD-002 is F0 and
its integrated acceptance (TEST-PLAT-CD at INTEGRATION, INSP-DEP-HOST) is a later gate.

| Criterion | Result | Assessment and evidence |
|---|---|---|
| DOR-TASK-01 | PASS | Outcome: main-derived, digest-identified images are built once and published to GHCR with SBOM and provenance, a ReleaseManifest and a DeploymentRecord are emitted, and a release is deployed to the Integration host by digest with no manual source patch. Target M1, node DN-PLAT-CD (late against its S2 window): [04](docs/04_Work_Breakdown_Structure.md), [05](docs/05_Dependency_Graph.md). |
| DOR-TASK-02 | PASS | Current wording: FR-PLAT-004 (F1, Yavuz: main-derived accepted artifacts deploy to INTEGRATION without manual source patching), FR-PLAT-005 (F1: every formal deployment produces a ReleaseManifest/DeploymentRecord) and NFR-DEP-003 (H0: zero manual source patches on the target host). Architecture ARCH-PLAT-CICD, ARCH-PLAT-RELEASE: [01](docs/01_Master_Project_Specification.md), [03](docs/03_Requirements_Traceability_Matrix.md). |
| DOR-TASK-03 | PASS | Single accountable owner Yavuz; supporting reviewer Asrın, advisory under CHG-018 with zero development approvals. The release paths are added to CODEOWNERS in the first slice: [CODEOWNERS](.github/CODEOWNERS), [CHG-018](09_change/CHG-018.yaml). |
| DOR-TASK-04 | PASS | Inbound DEP-002 (HARD, START) is READY since CHG-076, bound to the verified facts of DN-PLAT-REPO (protected main, required checks, the tiered CI pipeline); the GHCR image build is this package's own deliverable. DEP-005 (HARD, INTEGRATION) is a later gate and not a START blocker: [05](docs/05_Dependency_Graph.md), [DEP-002 readiness](evidence/WP-CICD-002/DEP-002-START-READINESS.md). |
| DOR-TASK-05 | PASS | Consumed on main: the tiered CI and required checks (WP-CICD-001), the Compose runtime and its smoke (WP-PLAT-001, WP-PLAT-003), the trace and test-strategy gates. Produced here: the image registry, the release workflow, the ReleaseManifest and DeploymentRecord schemas, the deploy command and the host hook: [ci.yml](.github/workflows/ci.yml), [compose](infra/compose/compose.yaml). |
| DOR-TASK-06 | PASS | Testable acceptance: (1) the manifest pins every image by digest and carries 02's identities; (2) the workflow publishes only from main with SBOM, provenance and attestation; (3) deploy refuses a dirty host tree, a non-main commit, a red ci-gate, an absent digest and a tag identity; (4) SUCCEEDED only when every stage passed; (5) a failed stage rolls back; (6) the first publish is deployed on the shared host: [03](docs/03_Requirements_Traceability_Matrix.md). |
| DOR-TASK-07 | PASS | Verification per 03: TEST-PLAT-CD (INTEGRATION) and INSP-DEP-HOST (EVALUATION). The CI-level tests and the shared-host DEV run are produced here; the INTEGRATION acceptance, the INSP-DEP-HOST audit and the NFR-DEP-003 measurement are later gates and are not claimed: [03](docs/03_Requirements_Traceability_Matrix.md), [test strategy](ci/TEST_STRATEGY.md). |
| DOR-TASK-08 | PASS | Review risk class estimate CR-3: a workflow that publishes images and signs provenance (security-sensitive CI/CD). Permissions are narrowed to the build job and everything that publishes is guarded to main. Review stays advisory with zero development approvals: [09](docs/09_Change_Control_Process.md), [CHG-018](09_change/CHG-018.yaml). |
| DOR-TASK-09 | PASS | One implementation-time open decision, OD-CICD-01 (manifest and record serialization), is left to the implementation by 02 and decided as JSON Schema in release/README.md; an ADR follows when the ADR index can admit it. No other architecture question: [02](docs/02_System_Architecture_Specification.md), [04](docs/04_Work_Breakdown_Structure.md). |
| DOR-TASK-10 | PASS | Size band M, slices of 1-2 days: (1) registry, manifest, record and deploy decisions; (2) release workflow, host hook and CI; (3) operator guide and run collector; (4) the shared-host run, trace and evidence: [04](docs/04_Work_Breakdown_Structure.md). |
| DOR-TASK-11 | PASS | No blocker at START. Later items with owners: a self-hosted runner for deployment from GitHub Actions (DN-PLAT-RUNNER, Yavuz), GHCR package visibility, application deployable images (their own work packages), migration execution (WP-CICD-003): [05](docs/05_Dependency_Graph.md). |
| DOR-TASK-12 | N/A | Scope class F0, not R1; no research partition or FINAL data is touched: [04](docs/04_Work_Breakdown_Structure.md). |
| DOR-WP-01 | PASS | Source RequirementIDs FR-PLAT-004, FR-PLAT-005 and NFR-DEP-003 listed with wording current in 01 and 03: [03](docs/03_Requirements_Traceability_Matrix.md), [01](docs/01_Master_Project_Specification.md). |
| DOR-WP-02 | PASS | Target milestone M1 and readiness node DN-PLAT-CD declared: [04](docs/04_Work_Breakdown_Structure.md), [05](docs/05_Dependency_Graph.md). |
| DOR-WP-03 | PASS | Inbound DEP-002 is READY (CHG-076); DEP-005 is a HARD INTEGRATION-stage edge, not START: [05](docs/05_Dependency_Graph.md), [DEP-002 readiness](evidence/WP-CICD-002/DEP-002-START-READINESS.md). |
| DOR-WP-04 | PASS | Precise requirement of DEP-002: main protected with required status checks ci-gate and projectctl (strict, enforced for everyone) and the tiered CI pipeline aggregated by ci-gate: [05](docs/05_Dependency_Graph.md), [DEP-002 readiness](evidence/WP-CICD-002/DEP-002-START-READINESS.md). |
| DOR-WP-05 | PASS | Consumed CI, required checks and Compose runtime exist on main; this item produces the registry, workflow, schemas and deploy command: [ci.yml](.github/workflows/ci.yml), [compose](infra/compose/compose.yaml). |
| DOR-WP-06 | PASS | Verification families TEST-PLAT-CD (INTEGRATION) and INSP-DEP-HOST (EVALUATION), boundary mode REAL per 03 View D: [03](docs/03_Requirements_Traceability_Matrix.md). |
| DOR-WP-07 | PASS | Owner Yavuz and supporting reviewer Asrın named; the release paths are added to CODEOWNERS in the first slice: [CODEOWNERS](.github/CODEOWNERS), [04](docs/04_Work_Breakdown_Structure.md). |
| DOR-WP-08 | N/A | Not R1; no partition or seed policy applies: [04](docs/04_Work_Breakdown_Structure.md). |

## START dependency assessment

| Dependency | Readiness | Producer assessment and precise consumer requirement |
|---|---|---|
| DEP-002 | READY | DN-PLAT-REPO is INTEGRATION_READY for the consumer's START: main protected with required status checks ci-gate and projectctl (strict, enforced for everyone) and the tiered CI pipeline aggregated by ci-gate, verified at current main and recorded by CHG-076: [05](docs/05_Dependency_Graph.md), [DEP-002 readiness](evidence/WP-CICD-002/DEP-002-START-READINESS.md), [required checks](ci/required_checks.json). The immutable GHCR image build is not a precondition: it is this package's deliverable. |
