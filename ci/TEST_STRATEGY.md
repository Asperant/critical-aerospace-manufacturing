# Test strategy, tiers and boundary-mode policy (WP-TEST-001)

This is the human-readable form of `ci/test-strategy.json` (`cap.test-strategy/v1`).
The JSON is authoritative; `ci/scripts/check_test_strategy.py` enforces it on every
CI run (t1-unit, step "Test strategy conformance").

## Tiers: what is tested where

| Tier | What it proves | CI job | Budget | Allowed boundary modes |
|---|---|---|---|---|
| unit | one module or package in isolation; no network, no containers | `t1-unit` | 10 min | FIXTURE_ALLOWED, STUB_ALLOWED, MOCK_ONLY |
| component | one deployable through its own interfaces, external boundaries replaced | `t1-unit` | 10 min | FIXTURE_ALLOWED, STUB_ALLOWED |
| contract | published schemas, examples and API contracts against their consumers | `t1-contract` | 5 min | REAL, FIXTURE_ALLOWED |
| integration | real infrastructure and real processes | `t1-integration` | 20 min | REAL, FIXTURE_ALLOWED (only with named replaced boundaries) |
| scenario | integrated acceptance paths (E2E-*, AV-SCEN-*) across deployables | not yet in CI | 60 min | REAL |
| benchmark | measurements against NFR thresholds on a documented HardwareProfile | on request, never a gate | 60 min | REAL |

`t1-static` (lint, format, typing ratchet) is not a test tier; it gates every change.

## Boundary modes

The four modes are those of 03 §4.5 (01 Item 83): `REAL`, `FIXTURE_ALLOWED`,
`STUB_ALLOWED`, `MOCK_ONLY`. The rules:

- **Lower tiers may replace boundaries; acceptance may not.** A requirement's final
  acceptance evidence uses the mode 03 assigns to it; no requirement is final-
  verifiable with `MOCK_ONLY`.
- **Integration means real infrastructure.** PostgreSQL, NATS JetStream, the
  Collector, OpenObserve and the Compose profiles run as real containers, never in
  memory. An integration run that replaces a boundary (for example a scripted
  identity provider) must say which boundaries in `fixture_boundaries`, so the gap
  is visible.
- **Missing infrastructure fails, never skips.** REAL tests fail with a clear
  message when their services are not up.
- **No retry-until-green.** A flaky test is quarantined with an owner and expiry in
  `ci/flaky_tests.yaml` (NFR-DX-006); re-running a gate is allowed only for a
  recorded infrastructure cause, once.

## Suites

Every test file belongs to a declared suite (most specific path wins); an
undeclared test file fails the check, because a suite no gate runs would escape
every gate. Each suite names its owner, work package, tiers with the CI step that
runs them, boundary modes, 03 verification families and TestIDs. Suites whose
family allocation belongs to another owner say so in `family_note`; WP-TEST-001
does not assign other owners' families.

## TestIDs

Concrete verification assets are named `TEST-<AREA>-<NNN>-<SSS>`: `AREA-NNN` is the
producing work package `WP-<AREA>-<NNN>`, `SSS` a sequence within it, for example
`TEST-PLAT-001-002`. Each asset names the 03 planned family it realises (for
example TEST-PLAT-COMPOSE) and is listed in the producing package's 03 §19 table.
The earlier `TEST-CICD-001`…`003` are recorded as legacy and keep their names.

## Adding tests

1. Put the test under an existing suite path, or add a suite to
   `ci/test-strategy.json` with its tier, CI step, boundary mode and families.
2. Make sure a CI step in the tier's job runs the path.
3. Run `uv run --project ci --locked python ci/scripts/check_test_strategy.py`.
