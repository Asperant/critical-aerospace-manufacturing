# WP-SIM-006 verification evidence (offline dispatch interface slice)

Local development evidence, 2026-10-28, branch `wp/WP-SIM-006-dispatch-interface` from main
`db5640a28bbd73390b1002e3c0ae7f4a87b0d7d1`. This is **not** a sealed EvidenceBundle, a CI
result, a `VERIFIED` record or an acceptance record.

## What was built and what it proves

| Deliverable (04) | Realization |
|---|---|
| dispatch decision contract | `services/manufacturing-simulator/contracts/v1/` and `packages/contracts/registry/simulator.*.v1.json` (decision-request, dispatch-intake, dispatch-outcome); schema/decoder parity test |
| baseline policy implementation | `baseline.py`: FIFO, EDD, static priority, total-order tie-breaks, standalone only |
| intake and Simulator-side validation | `dispatch.py` `DispatchGate`: revalidates on arrival and on execution, idempotent by `dispatch_id`, executes only as a kernel event, accepts a Core `LotDispatchAuthorized` fact only through `authorize()` |
| operational state/events without Oracle fields | `exposure.py`, `isolation.py`: positive allow-list, recursive evaluator-field rejection |

Tests (`TEST-SIM-DECISIONIF`, partly `TEST-SIM-ISOLATION`) use a **test-only facility** behind
`FacilityPort`. They prove the interface, not the operational model of WP-SIM-003.

## Runs

| Directory | Source | Outcome |
|---|---|---|
| `runs/run-1-failed-pyright-env/` | `4503fecc0a0b0974df9791c0036a74a4d12afe40`, clean | 7 of 8 commands exit 0; `pyright` exit 1 (31 missing-import errors): started without the locked environment on `PATH`, so Pyright resolved another interpreter. A harness mistake, not a code defect; kept unchanged |
| `runs/run-2-committed/` | `f05ed063a…` (tree `e05df5f2d2c78f37f0f6d350d5b005df718e95c3`), clean, empty manifest | 8 commands, all exit 0 (final) |

`run-2-committed` (2026-10-28T21:58:14Z to 21:58:30Z, Python 3.11.16, numpy 2.4.6, lock digest
`5caecd37…`): decision-interface tests 137 passed; full simulator suite 495 passed (the 358
earlier tests unchanged); collector tests 6 passed; Ruff check and format clean; Pyright 0
errors; `check_contracts.py` PASS; registry and producer-authority tests 133 passed. Simulator
tree `35fe6fd8885f95e7c1beb1b597d9234f69b45819`. Files: `identity.json` `e6b0063a…`,
`results.json` `2ba772f0…`. stdout and stderr are the exact bytes with hashes in
`results.json`. `uv` was not on `PATH`, so `identity.json` holds `uv: null`; a later manual check
printed `uv 0.12.13`.

## Limits

- Fixture evidence on a test-only facility; no lots, routes, queues, failures, maintenance or
  rework model exists yet (WP-SIM-003, blocked by DEP-038).
- No real Core integration or DEP-041 acceptance. Core's `LotDispatchAuthorized` is consumed as a
  schema-checked payload only; nothing is sent to Core.
- Scheduler IC-SCH-005 (DispatchDecision) is not defined here; the intake contract is the
  Simulator's side of the interface and DEP-088 gates the Scheduler plugging in.
- Operational events are typed local records, not published on the event spine.
- `AV-SCEN-01/02/11` and `BENCH-RQ2-001` are not executed; there is no Oracle plane yet (WP-SIM-005).
- No governed Release, Environment or Hardware identity (`identity.json` lists them as unavailable).
- Not CI, INTEGRATION or EVALUATION evidence; DoD items 05, 06 and 12 remain open.
