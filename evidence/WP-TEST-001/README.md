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

## First conformance result

At the slice revision the check covers every test file of the repository
(79 files in 17 suites, 0 violations): all suites run in the CI job of their tier,
every integration run is REAL except the browser acceptance, which names its two
replaced boundaries (scripted identity provider, fixture Core and Twin readers).
