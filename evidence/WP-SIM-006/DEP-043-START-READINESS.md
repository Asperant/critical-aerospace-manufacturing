# DEP-043 START readiness assessment (owner-adopted, CHG-077)

Status: **adopted by the owner as the edge-specific kernel assessment for DEP-043; bound to the planning-owner
disposition below. Not a product, integration or acceptance record, and not DN-SIM-DISPIF readiness.**
Prepared by Claude Code for Batuhan Kaya (owner of DN-SIM-KERNEL and DN-SIM-DISPIF) under supervisor runs
`e3f47591-16a6-4256-92c5-dcd17ca1cf7c` (plan SHA-256 `be43972b…20ec8`) and `e03bdf75-2ab3-4b0e-9587-b996d8d6442d`.
The content below the next section is the assessment as proposed in commit `495f7ebd`; only the status, the
two limit statements it affected and the closing section were updated for the adoption.

## Owner adoption and planning-owner disposition

- **Owner adoption (Batuhan).** Native supervised-conversation statement, received after the CI and review of
  pull request 199 were verified (original wording, Turkish): "WP-SIM-006/DEP-043-START-READINESS.md içindeki
  kernel kanıtlarını ve belirtilen sınırlarını, DEP-043 için owner değerlendirmem olarak kabul ediyorum."
  Meaning: the kernel evidence in this file and its stated limits are the owner's assessment for DEP-043. It
  does not accept any WP-SIM-006 product deliverable, integration evidence or DONE. The statement has no
  timestamp or public URL, and none is invented; a durable public record (for example a pull request comment)
  needs an authorized operator publication and is still open.
- **Planning-owner disposition (Asrın).** Pull request 199 review
  https://github.com/Asperant/critical-aerospace-manufacturing/pull/199#pullrequestreview-5689282669
  (state APPROVED, commit `495f7ebd06502ab2d0066f18735a26bbed6b6348`, GitHub login Asperant). Its text accepts
  the correction: the existing kernel APIs and test evidence are the START condition and the dispatch interface
  is a WP-SIM-006 deliverable. The GitHub API (`users/Asperant`, read 2026-10-28) returns type User with the profile name
  Asrın Dündar, so the review is by the planning owner's own GitHub user. The review state is not an approval quota.
- **Effect.** With both, the DEP-043 `status` is READY in `docs/05` (CHG-077). That is dependency metadata for
  the kernel START fact. It is not Plane READY and does not implement WP-SIM-006.

## Edge and question

DEP-043: DN-SIM-KERNEL → DN-SIM-DISPIF, CAPABILITY, HARD, START, COMPONENT_READY, need-by S2, no fallback.
The former unblock text, "baseline dispatch interface callable", is a WP-SIM-006 deliverable ("dispatch
decision contract + baseline policy implementation"), so it cannot exist before WP-SIM-006 starts.
Question: do the facts DN-SIM-KERNEL can provide, as stated in the corrected predicate, hold today?

## Identities

| Item | Value |
|---|---|
| Canonical main | `11a9cc211126c6dc49407d5b7822fc0f3a217d9b` (read 2026-10-28; CI run 40754084480 on this SHA: success, step "Simulator kernel unit/property tests and typing (WP-SIM-001)" success) |
| `services/manufacturing-simulator` tree | `0e93c717b875a61c54b0c78834b9028067ab6f95` |
| Blobs | `kernel.py` `fff7339…`, `events.py` `3eb78c1…`, `clock.py` `5e44008…`, `rng.py` `8c5666c…`, `__init__.py` `bb3982a…` |
| Last change to the tree | `35d3970` (WP-SIM-001 kernel); no later commit touches it |
| Historical run | run-7, `evidence/WP-SIM-001/runs/run-7-identity-2026-10-25/`, source `60c0359bb2f7423f7e5505728f8f841776abf568` (clean tree, 2026-10-25T14:44:45Z) |

## Applicability of run-7 to current main

- `git rev-parse 60c0359:services/manufacturing-simulator` equals the current tree id above, and
  `git diff 60c0359 HEAD -- services/manufacturing-simulator` is empty. The commit itself is not an
  ancestor of main (squash merge), so the equality is by tree, not by commit.
- `evidence/WP-SIM-001/replay_comparison.py` is byte-identical to the run-7 `replay_script_sha256`
  (`7888112e…20a48`). numpy 2.4.6, hypothesis 6.168.1 and pytest 8.3.3 are pinned identically in
  `ci/uv.lock`; the lock file hash differs (`914da9c1…` then, `5caecd37…` now) because later work added
  the scheduler, Alembic, SQLAlchemy, Mako and MarkupSafe packages (97 added lines, none removed).
- Result: the simulator source under test is unchanged, so no kernel test or replay rerun was needed and
  none was made. Run-7 output is reused as is: `suite-output.txt` `ed587fdf…bd12` (202 passed),
  `replay-comparison.json` `e3291575…baec` (six seeds, in-process and fresh processes, four hash seeds,
  traces equal), `identity.json` `f15691fe…915a7`. Its unavailable identities (governed Release,
  Environment, Hardware) stay unavailable; nothing was filled from today's environment.

## Predicate against the inspected APIs

| Predicate clause | Inspected API (current main) | Supporting tests |
|---|---|---|
| event scheduling | `Kernel.schedule(EventSpec)`, `ExecutionContext.schedule`, `EventSpec(time, kind, payload, event_id)`, `ScheduledEvent.sequence` | `test_scheduling_in_the_past_is_rejected_without_mutation`, `test_scheduling_an_unknown_kind_is_rejected_without_mutation` |
| handler execution | `Kernel(world, handlers)`, `register_handler(kind, EventHandler)`, `step()`, `run(until, max_events)`, immutable `ExecutionRecord` via `records()` | `test_run_executes_in_reference_order_with_a_monotonic_clock`, `test_handler_failure_fails_the_run_with_event_context`, `test_a_failed_run_cannot_be_resumed_extended_or_retried` |
| stable (time, sequence) order | `FutureEventQueue` | `test_equal_time_events_are_fifo`, `test_pops_match_independent_sorted_reference` |
| monotonic simulated clock | `SimulationClock.advance_to`, `ExecutionContext.now` | `test_clock_starts_at_zero_and_only_moves_forward` |
| named seeded RNG | `RandomnessManager.stream(name)`, `ExecutionContext.stream` | `test_same_seed_gives_same_draws_in_every_stream`, `test_lookup_order_does_not_change_any_stream` |
| deterministic replay | `tests/test_determinism.py`, `replay_worker.py` | `test_same_seed_replays_to_an_equal_trace_and_state`, `test_fresh_processes_with_any_hash_seed_replay_identically` |
| explicit rejection / failure | `UnknownEventKindError`, `PastSchedulingError`, `InvalidTimeError`, `HandlerExecutionError`, `RunFailedError` | the kernel tests above |

Names were read from the source and test files at the identities above; the 2026-10-25 run executed them.

## Limits

- Payloads are frozen scalar pairs. The kernel does not interpret a payload as a validated operational
  dispatch decision, and a generic handler callback is not an external dispatch interface. The
  DispatchDecision wire contract, deterministic standalone baseline, operational publication, Oracle
  isolation and Simulator–Core acceptance remain WP-SIM-006 deliverables, so DN-SIM-DISPIF is not
  CONTRACT_READY and WP-SIM-006 DoD is untouched.
- Run-7 is a local toy-kernel run on the shared development host, not CI, INTEGRATION or EVALUATION. The
  main CI run above only shows the same suite passing on main. The kernel is not an installed or deployed
  service.
- Before this assessment, DN-SIM-KERNEL had no recorded edge-specific COMPONENT_READY binding for DEP-043. SIM-001's own
  `DOD-ASSESSMENT-2026-10-25.md` is a WP assessment, not that binding, and SIM-001's integrated
  acceptance remains open (its lifecycle state is not asserted here). This file is the binding, adopted by the owner as described above.
- DEP-037 (DN-SIM-OPSEM) and DEP-038 (DN-CORE-CONTRACTS, Asrın) are not assessed here; DEP-039 is a
  MILESTONE_EXIT edge. WP-SIM-003 stays blocked by DEP-037 and DEP-038.

## Status of the accountable conclusion

1. Planning-owner disposition: recorded (review above).
2. Owner attribution of this assessment: recorded as a native conversation statement; a durable public record
   is still open and needs an authorized operator publication.
3. The DEP-043 `status` is READY in `docs/05` under CHG-077. Remaining, each a separate step: current-head CI on
   the head that carries this adoption, merge, the supported policy refresh, and one
   `projectctl startability WP-SIM-006` run against the refreshed source. A local run on this worktree is not
   deployed startability.
