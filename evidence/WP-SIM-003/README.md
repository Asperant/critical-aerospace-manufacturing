# WP-SIM-003 verification evidence (offline operational model)

Local development evidence, 2026-10-28, branch `wp/WP-SIM-003-operational-semantics` from main
`9bc4be3f68887cce9af61cb7a33f490c948d6106`. This is **not** a sealed EvidenceBundle, a CI result, a
`VERIFIED` record or an acceptance record.

## What was built and what it proves

| Deliverable (04) | Realization |
|---|---|
| routing and queue model | `operations/facility.py`: re-entrant routes with distinct visit identity, per-visit dispatchable queues; `OperationalFacility` is the `FacilityPort` behind the SIM-006 dispatch gate |
| equipment availability, failure, repair | scheduled, stochastic (seeded `failure` stream) and usage-based failure; a failure pauses the lot on the same machine and it resumes after DOWN, MAINTENANCE, optional QUALIFICATION; material is never moved |
| maintenance | planned windows start when the machine is idle, are skipped when it is down, and restore health |
| rework | an injected, approved directive is executed (never created); scrapped and completed material, work in progress and the count limit are refused; a defect is only an operational fact |
| scenario-driven disruption injection | failures, windows, holds, scrap and directives are configured, seeded and part of the replay input digest |
| legality | execution and lot edges equal Core's published tables (checked by reading Core's source, no import); lot state validates against Core's published schema |

Tests (`TEST-SIM-KERNEL`) use small test facilities (2 mills, 1 inspection station, a route that revisits the
MILL class). They prove the operational mechanics, not realism and not the Core integration.

## Runs

`runs/run-1-committed/` (2026-10-28T22:51:28Z to 22:51:46Z): source `c54406e1854126978ed8cbb008753b58da3fb409`
(tree `ae12f031cf033b54ed7dc809cf0f6dfa9be8304b`), clean tree, empty manifest, Python 3.11.16, numpy 2.4.6,
uv 0.12.13, lock digest `5caecd37…`. Seven commands, all exit 0: operational-model tests 56 passed; full
simulator suite 550 passed (the 494 earlier tests unchanged); collector tests 6 passed; Ruff check and
format clean; Pyright 0 errors; architecture boundary check PASS. Simulator tree
`67a03d3bb03b86321505a5767b74f66f03f50a55`. Files: `identity.json` `86ccbd2e…`, `results.json` `0af86379…`;
stdout and stderr are the exact bytes with hashes in `results.json`.

Mutation sanity (not committed): nine faults injected into the facility one at a time (dispatch on a machine in
maintenance, READY to PROCESSING legal, rework limit ignored, no degradation effect, lost remaining time after a
failure, deferred maintenance never starting, lots never completing, scrapped lots reworkable, constant failure
gap); the first run left three alive, three tests were added, and all nine are then caught.

## Limits

- Test facilities only; the model has no calibrated process times, no real routes, tools or reliability data.
  Duration and defect effects of health are simulation assumptions, not machining physics.
- Core transition legality for failures is not extended: Core has no abort edge, so a failed process pauses and
  resumes on the same machine. Abort or re-route needs a Core-owned transition (DEP-039, milestone exit).
- Lot-level only: serialized-component histories, holds as Core records and rework segments are not mapped to
  Core records; that is DEP-039/DEP-040 integration work. The Simulator creates no rework directive.
- No `AV-SCEN-02`, `E2E-01`, `BENCH-SIMVAL-001`, `BENCH-RQ2-001` or `BENCH-E2E-001` run; no snapshot/fork (SIM-004),
  Oracle plane (SIM-005) or event-spine publication.
- No governed Release, Environment or Hardware identity. Not CI, INTEGRATION or EVALUATION evidence; DoD items
  05, 06, 09 and 12 remain open.
