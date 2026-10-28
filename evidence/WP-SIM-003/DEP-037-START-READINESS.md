# DEP-037 START readiness assessment (owner-adopted, CHG-079)

Status: **adopted by the owner as the edge-specific kernel assessment for DEP-037.** It is not a product,
integration or acceptance record and not DN-SIM-OPSEM readiness. Prepared by Claude Code for Batuhan Kaya (owner of
DN-SIM-KERNEL and DN-SIM-OPSEM) under the operator-approved plan `DEP037_PLAN.md` (SHA-256 `15105d57…644aa`).
The assessment below is as proposed; only this status, the adoption section and the closing section were updated.

## Owner adoption

Native supervised-conversation statement by Batuhan Kaya, received after the proposed assessment and its
limits were presented (original wording, kept verbatim including its spelling): "I adopt the kernel assesment."
Meaning: the kernel and replay evidence in this file and its stated limits are the owner's assessment for DEP-037.
It does not accept any WP-SIM-003 product deliverable, integration evidence or DONE. The statement has no timestamp
or public URL and none is invented; a durable public record (for example a pull request comment) needs an
authorized publication and is still open. No planning-owner disposition is claimed: a binding of an unchanged
predicate does not need one (CHG-066 and CHG-074 pattern), and none was requested or received.

## Edge and question

DEP-037: DN-SIM-KERNEL → DN-SIM-OPSEM, CAPABILITY, HARD, START, COMPONENT_READY, need-by S2, no fallback.
Unblock text (unchanged): "kernel tests + deterministic replay green". Question: do the kernel and replay
facts that WP-SIM-003 consumes hold on current main? This is a binding of an unchanged, non-circular predicate.

## Identities

| Item | Value |
|---|---|
| Canonical main | `db5640a28bbd73390b1002e3c0ae7f4a87b0d7d1` (read 2026-10-28) |
| `services/manufacturing-simulator` tree | `5556add458d14549ea7d94b77974cbd969e1bd73` |
| Source blobs | `kernel.py` `fff7339…`, `events.py` `3eb78c1…`, `clock.py` `5e44008…`, `rng.py` `8c5666c…`, `replay.py` `78823a5…`, `serialization.py` `a20c9ae…`, `__init__.py` `d17cec6…` |
| Evidence run | WP-SIM-002 run-4, `evidence/WP-SIM-002/runs/run-4-committed/`; tested source `5263ff886b7cd195a090e9eafc7ea5896100eadd`, tree `a86d9661…`, clean, Python 3.11.16, numpy 2.4.6, lock `430cd33d…` |
| Run files | `identity.json` `3af7c33b…`, `results.json` `79f81acc…` (seven commands, all exit 0: determinism regression 156 passed, simulator suite 358 passed, collector tests, Ruff, Pyright, replay matrix) |
| Main CI | run 40769603991 at the main revision: steps "Simulator kernel unit/property tests and typing (WP-SIM-001)" and "Simulator replay and hash determinism regression (WP-SIM-002)" succeeded |

## Applicability

The simulator tree on main equals the source tree of run-4's tested commit (`git rev-parse <commit>:services/manufacturing-simulator`
gives `5556add4…` for `5263ff88`, `4b5c986` and `ac05b0d` and for main), so run-4 applies unchanged and nothing was rerun
for this proposal. SIM-001 run-7 belongs to the older tree `0e93c717…` (before replay was added) and is historical only.

## Predicate against the inspected APIs

| Clause the consumer relies on | API on main | Supporting tests (names read from the files) |
|---|---|---|
| event scheduling and handler dispatch | `Kernel`, `register_handler`, `schedule(EventSpec)`, `step`, `run` | `test_run_executes_in_reference_order_with_a_monotonic_clock`, `test_handler_failure_fails_the_run_with_event_context` |
| clock | `ExecutionContext.now`, `SimulationClock` | `test_clock_starts_at_zero_and_only_moves_forward` |
| named RNG for failure, repair, processing and the other streams | `StreamName`, `STREAM_IDS`, `ExecutionContext.stream` | `test_required_and_architecture_streams_are_registered`, `test_lookup_order_does_not_change_any_stream` |
| immutable execution records | `ExecutionRecord`, `Kernel.records()` | `test_records_carry_simulation_provenance_and_correlation` |
| deterministic replay and digests | `ReplaySpec`, `replay`, `compare`, `check_determinism`, `event_sequence_digest`, `final_state_digest`, `FORMAT_VERSION` = `sim-replay-hash/1` | `test_the_same_scenario_state_and_seed_match_with_equal_digests`, `test_every_supported_seed_matches_its_own_replay`, `test_golden_vectors_match_hand_written_bytes_and_hashes` |

## Limits

- Kernel and replay behaviour is evidenced by those tests, not by this record. Toy handlers only; the replay
  digest does not cover RNG stream positions; `sim-replay-hash/1` is simulator-local; replay is proven for the
  locked NumPy 2.4.6 only; `source_id` and `handler_bundle_id` are caller-declared.
- Local run and main CI unit evidence, not INTEGRATION or EVALUATION. No governed Release, Environment or Hardware
  identity. BENCH-SIMVAL-001 and REPRO-NONOWNER-001 are not executed.
- Nothing here implements routing, queues, failure, repair, maintenance, rework or Core transition legality.
  Those are WP-SIM-003 deliverables. DEP-038 (Asrın, CONTRACT_READY, reentrant lifecycle and hold/rework
  contract) was bound separately by CHG-078 (CTRL-HOST-050) and DEP-039 (MILESTONE_EXIT) is a later gate; neither is assessed here.

## Status

1. Owner adoption: recorded above (native statement; public record open).
2. The DEP-037 `status` is READY in `docs/05` under CHG-079, the kernel START fact only.
3. Remaining, each a separate step: current-head CI on the head that carries this, merge, the supported policy
   refresh and one `projectctl startability WP-SIM-003` run (expected: STARTABLE once the CHG-078 binding of DEP-038 is refreshed too). A local run on a
   worktree is not deployed startability.
