# Evidence — WP-SIM-002 (determinism, replay and event-hash equivalence)

Requirements FR-SIM-008 and NFR-REP-001 (H0). The code is in
`services/manufacturing-simulator/` (`serialization.py`, `replay.py`; usage and limits
in its README). This directory holds the local verification runs and what they do not
establish.

## Run of record

`runs/run-3-uncommitted/` — one local run of `capture_run.py` on the **uncommitted**
tree, started 2026-10-27T22:10:17Z (UTC), all seven commands exit 0:

| Command | Result |
|---|---|
| determinism tests (`test_serialization.py`, `test_replay.py`, `test_replay_validation.py`) | 156 passed |
| full simulator suite (the 202 SIM-001 tests are unchanged) | 358 passed |
| collector tests (`evidence/WP-SIM-002/tests`) | 6 passed |
| `ruff check` / `ruff format --check` on the package and 3 evidence scripts | clean / 27 files formatted |
| `pyright --project services/manufacturing-simulator/pyrightconfig.json` | 0 errors |
| `replay_matrix.py` (below) | `ok: true` |

`replay-matrix.stdout` (one JSON line) reports these counts **separately**; they are never
merged into one pass rate. Development seeds 1, 7, 20261028, 424242; `PYTHONHASHSEED` 0,
1, 424242, random; two handler-mapping construction orders; fresh processes, each bounded by
a timeout.

- **Accepted equality:** 32 of 32 fresh-process replays are `MATCH` (complete runs).
- **Partial, not accepted:** 4 of 4 fresh-process replays that stopped at their event
  budget (25 events) are `PARTIAL_MATCH`; 0 are accepted. An equal prefix of an incomplete
  run is never reported as `MATCH`.
- **Behaviour differences that must not match:** 10 real alternative executions (payload or
  state values and types that Python `==` treats as equal, same-time insertion order, a
  different pending queue of the same depth, extra stream draws, one extra last event):
  **0 false `MATCH`**, and every outcome is the expected typed mismatch.
- **Structural corruptions that must be rejected:** 33 impossible results built in memory
  and 17 as JSON with recomputed digests (so a digest cannot certify them), including an
  astronomically large `next_sequence` and a hole whose count still matches; all 50 raise
  `CanonicalizationError`, 0 accepted. A subprocess test repeats the huge-counter cases under
  an address-space cap (existing + 64 MiB).
- **Refused before execution:** a spec declaring a NumPy or RNG identity that this process
  does not run is refused with `IncompatibleRuntimeError` and the handler factory is called
  0 times (2 of 2).
- **Injected nondeterminism:** a handler depending on the Python hash seed gives
  `EVENT_MISMATCH` across hash seeds 0 and 1 and `MATCH` for two runs with the same hash seed
  (no false alarm). A handler sharing a global counter is detected in-process by the tests.

The run keeps the exact stdout and stderr bytes per command (`<id>.stdout`, `<id>.stderr`,
marked binary in `runs/.gitattributes`) with byte counts and SHA-256 in `results.json`;
`display_result_line` there is derived for reading only. `identity.json` has source, tool,
lock, workload and host identity, with host load at start and at finish.

- **Source state:** `tree_clean` is false. Commit was not authorized, so `identity.json`
  lists base commit `3242d1f` and the SHA-256 of each of the 22 changed or untracked files
  outside `runs/` and this README (the replay code, tests, scripts, CI wiring, `docs/` and
  `traceability/` included). A run on committed source will be a new run, never a
  replacement of this one.
- **Not available, so not claimed:** a governed ReleaseManifest, EnvironmentManifest image
  digest or HardwareProfile; the host facts are local labels. Their canonical producer is
  WP-PLAT-005 (docs/04), not started, so DOD-WP-11 stays open here. `source_id` and
  `handler_bundle_id` are caller-declared labels, not attested.
- Scratch mutation runs (not committed): 70 injected defects in the serialization and replay
  code, 68 caught. The 2 survivors are equivalent: redundant per-value decode checks that the
  whole-document canonical re-encoding also enforces.

## Earlier runs kept as history

Both are unchanged byte for byte, each describes only the source it ran on, and neither
may be cited as evidence of the final behaviour.

- `runs/run-1-uncommitted/`: the source Codex's first review found defective. Its tests then
  accepted a result with an unsupported format or impossible clock as `MATCH` against itself,
  accepted reversed events with a recomputed digest, labelled a run with a declared NumPy/RNG
  identity it did not check, and reported two equal budget-limited runs as `MATCH`.
- `runs/run-2-uncommitted/`: the source after those fixes, whose result validator built
  `set(range(next_sequence))`. A tiny malformed result or JSON with a huge `next_sequence`
  therefore made it allocate without bound before rejecting, instead of raising the named
  `CanonicalizationError` (Codex's R4). Run-3 is on the corrected validator, which proves the
  same invariant from the actual sequence IDs in time proportional to the input.

## What this is not

- Not BENCH-SIMVAL-001 (simulation validation and realism; other producers WP-SIM-003,
  WP-SIM-007, WP-SIM-009) and not REPRO-NONOWNER-001 (a real non-owner reproduction of the
  selected final environment and scenario; producers include WP-BENCH-001/003/004,
  WP-RES-001, WP-SIM-009). Neither has run, and neither agent can impersonate a non-owner.
  FR-SIM-008 and NFR-REP-001 therefore stay `EVIDENCE_PENDING`: the local asset ran, final
  evidence is absent, no `EvidenceID` exists and `observed` is null.
- Not a proof for arbitrary handlers, threads, other NumPy versions or other hardware. The
  hash covers the kernel-local projection (events, clock, local state, pending queue), not
  RNG stream positions, and is not a snapshot or restore format.
- Not a canonical ScenarioDefinition or cross-service hash standard (the format is local,
  `sim-replay-hash/1`).
- Observability: no process, endpoint or log sink was added (the fresh-process worker is
  test code), so this change stays inside the platform owner's confirmed exemption for the
  in-memory kernel library (PR #75, `coverage.json`, expires 2026-11-20). It is not renewed,
  extended or copied; a simulator service runtime would need a new decision.
