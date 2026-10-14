# WP-GOV-001 implementation evidence

Local development evidence, 2026-10-15, on
`wp/WP-GOV-001-requirement-catalog`. This is not a sealed EvidenceBundle,
remote CI result, independent approval or final acceptance record.

## Authorization and scope

`projectctl context WP-GOV-001` was run before implementation. The initial
working tree was clean and already on the correct WP branch. The user explicitly
confirmed that Plane assigns this WP to Asrın as IN_PROGRESS, that a human DoR
assessment was recorded when it became READY, and that implementation is
approved. This is user-attested execution context, not an API readback. No Plane
credentials were provided or used, and no Plane state was changed.

`projectctl check-ready WP-GOV-001` returned UNKNOWN because its adapter does
not ingest trusted execution evidence. UNKNOWN was not converted to PASS;
the user-confirmed recorded manual assessment is the starting authorization.

The canonical scope is the 306-entry catalog, JSON Schema, ID/non-reuse/owner/
class lint, CI integration and generated inventory counts used by 03. Authority
surface: ARCH-PLAT-CICD. Source requirements: FR-GOV-001/002/003/008 and
NFR-GOV-001/002/003/007. Ordinary implementation preserves approved semantics
(09 scope exemption; C1 derived implementation detail, C0 trace projection);
no new requirement or ChangeRequest approval is asserted. Suggested review
risk class: CR-2, with supporting reviewer Yavuz, subject to reviewer assessment.

## Readiness and completion obligations

| Criterion | Assessment and concrete references |
|---|---|
| DOR-WP-01/02 | Eight requirements read from 01/03; M0/S1 and DN-PLAT-REPO declared by the canonical context |
| DOR-WP-03/04 | Context has no incoming dependency edges; no predecessor artifact is assumed ready |
| DOR-WP-05 | Repository tooling produces the catalog schema; no service contract is consumed |
| DOR-WP-06 | TEST-GOV-CATALOG, permanent-ID slice of TEST-GOV-TRACELINT, NFR-class slice of INSP-GOV-NFR; expected environment CI, actual local development execution recorded below |
| DOR-WP-07 | Asrın owner / Yavuz supporting reviewer; verified Yavuz username from TEAM_WORKFLOW used for scoped CODEOWNERS routing; independent review is still pending |
| DOR-WP-08 | Not applicable: F1 tooling WP, not R1 |
| DOD-WP-01 | requirements/catalog.json, catalog.schema.json, coverage_counts.json; requirement_catalog.py; existing CI job includes lint |
| DOD-WP-02 | Eight records in 03 have concrete REALIZED_BY/VERIFIED_BY/EXECUTED_AS references and EVIDENCE_PENDING; 04 WP repository reference updated |
| DOD-WP-03 | Local test/check outputs are recorded; remote required CI and independent review remain pending |
| DOD-WP-04 | Malformed/duplicate/missing IDs and JSON keys; missing/multiple/unknown owners; invalid classes; source/schema/count/RTM drift; missing inputs; removed IDs; tombstone changes; RETIRED/SUPERSEDED resurrection; invalid Git baseline |
| DOD-WP-06 | Runtime-only criterion does not apply to this offline tool |
| DOD-WP-07 | requirements/README.md documents inspection, regeneration, failure/exit behavior and historical-ID handling |
| DOD-WP-12 | Lint uses actual 306 canonical records; negative fixtures exercise rejection only and are not milestone/final evidence |

## Executions and trace mapping

`RUN-GOV-001-LOCAL-002.test-result.json` records the final full-suite command,
UTC start/end and exit code; its `.pytest.txt` sibling preserves stdout/stderr.
`development-attempts.json` also preserves the pre-change baseline, initial
catalog checks and the two failed development tests with their correction.
No failing production check was suppressed or weakened.

- TEST-GOV-001: `test_gov_001_*` in test_requirement_catalog.py plus offline,
  read-only catalog command checks in test_cli.py; TEST-GOV-CATALOG family.
- TEST-GOV-002: `test_gov_002_*`; only the permanent-ID slice of
  TEST-GOV-TRACELINT, not the general trace registry owned by WP-GOV-002.
- TEST-GOV-003: `test_gov_003_*`; NFR-class inspection slice of INSP-GOV-NFR,
  not measurement-definition completion.

The first full run (RUN-GOV-001-LOCAL-001) passed 244 tests. Final self-review
added rejection coverage for a completely empty catalog or an omitted whole
requirement kind and fixed count rendering to report those failures clearly.
The second full run includes that change; the first run is retained.

`catalog-lint-final.json` records final canonical inventory validation with HEAD as
the history baseline. This is the first catalog introduction; the actual Git
baseline has no catalog. Isolated Git tests exercise a populated baseline.
`canonical-validation-final.json` records final offline canonical validation and
warning counts. `static-checks-final.json` records in-memory syntax compilation and
`git diff --check`. The run manifest binds source and artifact SHA-256 values
and records software/environment context. No ReleaseManifest, accepted
EnvironmentManifest, HardwareProfile or WorkloadProfile identity is fabricated.

## Remaining gates and limitations

All 306 per-record Revision/Status fields stay null where unspecified in 01.
NFR measurement metadata remains owner-confirmation work (GAP-RTM-004/005).
This implementation is deliberately fixed to the approved 186 FR / 120 NFR
baseline; a future approved catalog rebaseline must update that expectation.
Retirement decision-file existence is checked; human review still verifies
approval. The ledger is initially empty and does not certify pre-catalog history.
Generated schema drift after a Pydantic upgrade must be regenerated and reviewed.

The existing projectctl CI job now fails on catalog lint failures. No live
branch-protection setting was changed: ENGINEERING_WORKFLOW.md documents the
private-repository plan limitation. CI has not been claimed green remotely.
No spec/architecture conflict was found; known canonical source gaps remain
explicit. No manufacturing state, runtime infrastructure, external contracts,
research protocol or unrelated WP was changed.

Next: open the scoped PR, run the existing required CI, obtain supporting review,
merge through the governed workflow, then rerun catalog lint, tests and canonical
validation on the merged main commit and attach that post-merge evidence before
completion. Current WP status is not changed or marked DONE by these files.
