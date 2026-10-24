# WP-TEST-001 — Test strategy, tiers and boundary-mode policy: evidence

Owner: Yavuz Gümüş · supporting reviewer: Asrın (advisory, CHG-018) · F1 · M1/S2 ·
readiness node DN-PLAT-REPO · requirement NFR-DX-006.

## Deliverables (04 card)

| Deliverable | Where |
|---|---|
| test tier definition and CI mapping | `ci/test-strategy.json` (tiers, CI job per tier, every suite with the CI step that runs it), `ci/TEST_STRATEGY.md` |
| boundary-mode policy (REAL / FIXTURE_ALLOWED / STUB_ALLOWED) | allowed modes per tier, `fixture_boundaries` for integration runs that replace a boundary |
| test naming and TestID allocation convention | `TEST-<AREA>-<NNN>-<SSS>` with legacy list; TestIDs and families per suite |
| tiers wired into CI gates | `ci/scripts/check_test_strategy.py` in t1-unit ("Test strategy conformance (WP-TEST-001)"); schema validated by t1-contract |

## Slices

| Slice | Content |
|---|---|
| 1 | strategy, schema, conformance check with negative tests (TEST-TEST-001-001), CI step, CODEOWNERS |
| 2 | trace (03 §19.6, NFR-DX-006 edges), 04 repository reference, RUN-TEST-001-DEV-001 |

## First conformance result

At the slice revision the check covers every test file of the repository
(80 files in 17 suites, 0 violations): all suites run in the CI job of their tier,
every integration run is REAL except the browser acceptance, which names its two
replaced boundaries (scripted identity provider, fixture Core and Twin readers).

## RUN-TEST-001-DEV-001

`collect_run.py` records a run on the shared host against the actual
repository, CI workflow, 03 and 04 (boundary mode REAL):

| Step | Expected | What it shows |
|---|---|---|
| conformance | exit 0 | every test file belongs to a declared suite; 0 violations |
| repeat | exit 0, identical output | the gate is deterministic: no retry-until-green (NFR-DX-006) |
| negative | exit 0 | the negative and positive cases of TEST-TEST-001-001 pass |
| probe | exit 1 | a test file outside every suite is rejected and named; the probe file is removed afterwards |

Results are in `RUN-TEST-001-DEV-001/record.json` with the raw outputs next to it.

## What this evidence does not claim

NFR-DX-006 is measured at the final release and benchmark gates (zero known
unresolved, unquarantined flaky tests); that measurement belongs to WP-TEST-008.
This package makes the strategy and its gate exist and run; `observed` stays null
and the evidence state is EVIDENCE_PENDING. Suites owned by other work packages
are recorded as they are; family and TestID allocation for them is done by the
owning package (`family_note`), not changed silently here.
