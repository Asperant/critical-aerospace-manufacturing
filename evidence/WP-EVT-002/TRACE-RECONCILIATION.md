# WP-EVT-002 — scoped implementation and evidence reconciliation

Accountable owner: Asrın Dündar (Asperant), authorized development session.
Assessment date: 2026-10-25. Branch: wp/WP-EVT-002-typed-envelope.
Assessed implementation head: `ea8f6043b23588b496eda593e8c306b0b5c3c357`.
Reconciliation revision: the commit containing this file. This is trace/evidence
work only, not new runtime implementation, requirement acceptance or WP DONE.

Owner-executable implementation work remaining: NO

This assessment applies to the current published contracts and available bindings.
Owner-executable envelope/library/schema/fixture/WorldID-guard work is implemented;
this change reconciles its references. The WP's unimplemented propagation/runtime
obligations remain in scope. They require actual producer/consumer/transport inputs,
not invented adapters or subjects. No lifecycle, blocker/deferred-slot operation,
PR, merge, policy deployment or readiness certification is requested by this file.

## Exact implementation and historical execution bindings

| Slice | Source commit | Implementation / concrete test asset | Existing evidence and actual focused result |
|---|---|---|---|
| Typed envelope, ID roles, UTC/simulation time | `fb552ba17acf62a009046794b5a87f7f9b2f8139` | `packages/contracts/src/cap_contracts/envelope.py`: `new_event_id`, `EventEnvelope`, `EntityReference`, `SimulationTime`; exports in `packages/contracts/src/cap_contracts/__init__.py`; `ci/tests/test_event_envelope.py` (TEST-EVT-002-001) | `evidence/WP-EVT-002/SLICE1.md`; RUN-EVT-002-SLICE1-LOCAL-001; **103 passed in 0.51s** |
| Metadata schema and synthetic canonical fixtures | `82d108ce844dc501c7ee876def836b6dcd624abf` | `packages/contracts/schemas/event-envelope.v1.schema.json`; `packages/contracts/fixtures/event-envelope.utc.json`; `packages/contracts/fixtures/event-envelope.simulation.json`; `ci/tests/test_event_envelope.py` | `evidence/WP-EVT-002/SCHEMA-SLICE.md`; RUN-EVT-002-SCHEMA-LOCAL-001; **156 passed in 0.61s** |
| Consumer-side exact WorldID guard | `ea8f6043b23588b496eda593e8c306b0b5c3c357` | `packages/contracts/src/cap_contracts/envelope.py`: `validate_world_scope`; package export; `ci/tests/test_event_envelope.py` | `evidence/WP-EVT-002/WORLD-SCOPE-SLICE.md`; RUN-EVT-002-WORLD-SCOPE-LOCAL-001; **181 passed in 0.63s**, including 25 new scope cases |

Each recorded command was the repository-pinned `uv run --project ci --locked
pytest -c ci/pyproject.toml ci/tests/test_event_envelope.py -q`. These are historical
executions, not rerun in this reconciliation. Counts overlap as the suite grew;
they are not independent totals. The engineering run labels are not sealed
EvidenceIDs. Per-slice static checks, corrected initial failures and limitations
remain in the original evidence documents and are not overwritten.

## Requirement dispositions

| Requirement | Implemented / exercised portion | Exact focused assets | Unresolved acceptance |
|---|---|---|---|
| FR-EVT-002 | UUID4 generation for a new fact, explicit durable identity field and preserved EventID across metadata replay/round-trip | `test_generated_event_id_and_replay_identity`, `test_valid_round_trip`, `test_missing_required_metadata_rejected`, `test_published_fixtures_schema_model_round_trip` in `ci/tests/test_event_envelope.py`; all three slice records above | FIXTURE_ALLOWED/EV-L2/CI remains the canonical boundary. Source-bound CI supports this portion; no sealed accepted evidence or full requirement acceptance is asserted. Actual durable producer adoption remains outside this static proof. |
| FR-EVT-003 | Distinct CorrelationID/CausationID/TraceID fields and root-null semantics; preservation through metadata serialization | `test_causal_and_trace_ids_preserved`, `test_generated_event_id_and_replay_identity`, `test_published_fixtures_schema_model_round_trip`; Slice 1/schema evidence above | Propagation middleware, TEST-OBS-TRACEPROP, actual HTTP/NATS/Temporal boundaries, downstream adoption and AV-SCEN-01 are **NOT_YET_EXECUTED** for this WP. REAL/EV-L3/CI + INTEGRATION acceptance remains pending. |
| FR-EVT-004 | Required WorldID and exact, non-mutating expected-world guard; fail-closed missing/malformed input and mismatch, with redacted errors | `test_missing_required_metadata_rejected`, `test_world_scope_match_preserves_exact_envelope`, `test_world_scope_mismatch_is_exact_deterministic_and_redacted`, `test_world_scope_missing_expected_world_rejected`, `test_world_scope_malformed_expected_world_rejected`, `test_world_scope_malformed_envelope_world_rejected_before_guard`, `test_world_scope_missing_envelope_world_rejected_before_guard`; World-scope evidence above | Runtime tagging/admission and real consumer enforcement, AV-SCEN-09/10, REAL/EV-L3/CI + INTEGRATION acceptance remain pending. A pure guard is not integrated cross-world mutation/isolation proof. |
| NFR-DATA-008 | Explicit UTC observation versus tagged UTC/simulation occurrence; finite simulation seconds/run ID, calendar/clock validation and canonical fixture round-trip | `test_explicit_utc_and_simulation_time_meanings`, `test_non_utc_direct_timestamps_rejected`, `test_invalid_simulation_time_rejected`, `test_ambiguous_occurrence_rejected`, `test_utc_schema_and_model_reject_invalid_calendar_and_clock`, `test_utc_schema_and_model_accept_boundary_dates`, `test_simulation_numbers_remain_seconds_without_utc_conversion`; Slice 1/schema evidence above | No further static/fixture implementation identified. Formal **persisted real-time evidence** and its zero-ambiguity measurement at REAL/EV-L2/CI remain pending; `observed` remains null. No persisted-evidence acceptance is inferred from serialization. |

Only these four RTM entries and WP-EVT-002's WBS implementation/evidence references
change. Requirement wording, owners, architecture allocation, verification families,
scenario IDs, acceptance modes/targets, measurement/threshold and DoR/DoD remain
unchanged. REALIZED_BY references are explicitly partial where middleware is absent;
those portions retain TBD_BY_IMPLEMENTATION. Coverage/planning/evidence advance
only to EVIDENCE_PENDING. EVIDENCED_BY stays empty: no immutable EvidenceBundle is
invented. The WBS historical planning status is not treated as live Plane state.

## Read-only implementation-head CI observation

At exact implementation SHA `ea8f6043b23588b496eda593e8c306b0b5c3c357`, GitHub's
check-runs API reported all six checks completed with SUCCESS:

- `t1-static`, `t1-unit`, `t1-contract`, `t1-integration` and `ci-gate`:
  https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/40198179499
- `projectctl`:
  https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/40198179458

This session only read those existing results; it launched no tests or CI runs.
Existing `.github/workflows/ci.yml` runs `ci/tests` in its CI tooling step, which
discovers the envelope suite, and `ci/scripts/check_contracts.py` discovers tracked
`*.schema.json`. No additional CI wiring is required for these artifacts. Generic
CI integration success is not envelope adoption or the missing propagation/time
scenario evidence. This observation applies to the implementation SHA only; future
reconciliation-head CI and merge/post-merge results are not asserted in advance.

## Exact remaining runtime and acceptance dependencies

- **HTTP:** `services/operations-bff/src/operations_bff/api.py` has per-request
  server-generated correlation and a conditional overview path. `OverviewQuery`
  carries WorldID/correlation/as_of, but `composition.py` has no real backend
  reader adapter and leaves overview disabled by default. Core's `query_v1.py`
  is transport independent. Real request/response and trusted-context bindings
  must exist before cross-service propagation can be implemented or accepted.
- **NATS:** EVT-001's StreamDefinition/catalog/permissions are static primitives;
  the sole real registered Core exemplar is a synchronous query. EVT-003 supplies
  generic `JetStreamConsumer.bind`/identify/admit hooks, not a production publisher,
  subject/durable binding or adopted application consumer. Actual producer/outbox,
  publication bindings and real broker/runtime integration must be supplied.
- **Temporal:** no real workflow/activity context/interceptor implementation was
  identified in the scoped source. Actual workflow/activity inputs and propagation
  hooks must exist; a synthetic workflow would not satisfy this obligation.
- **Evidence and operation:** TEST-OBS-TRACEPROP, real HTTP/NATS/Temporal
  propagation, downstream consumer adoption, persisted formal UTC/simulation-time
  evidence, AV-SCEN-01/09/10, applicable runtime observability/correlation/health
  and operator runbook acceptance remain pending. The shared package documentation
  and redacted errors do not stand in for runtime operational acceptance.

DEP-021 remains this WP's only inbound canonical START edge, already accepted
narrowly for its metadata task; no new gate is invented. DN-CORE-OUTBOX and
DN-RT-NATS integration inputs correspond to DEP-024/025 on DN-EVT-SPINE, not new
EVT-002 START edges. Full DN-EVT-CONTRACTS readiness remains unproven. This memo
does not by itself satisfy CHG-024's exact own-edge parking proof or release a
slot. The WP stays incomplete; no VALIDATING, DONE or deferred-wait claim is made.

Schema/Python input-language limitations remain as documented in SCHEMA-SLICE.md
and the package README; this trace edit neither changes nor hides them.

## Reconciliation validation

Only canonical trace/catalog validation, scoped reference/change checks and diff
hygiene were run for this documentation-only change:

- `projectctl validate --json`: **PASS**; 634 source diagnostics remain WARNINGs,
  not readiness or acceptance evidence.
- `projectctl catalog-lint --base ea8f6043b23588b496eda593e8c306b0b5c3c357 --json`:
  **PASS**, zero issues; readiness and evidence remain **NOT_CERTIFIED**.
- Scoped source/reference validation: **PASS**. Only the four named RTM records
  changed; all their other canonical fields are identical. Only WP-EVT-002's
  repository-reference/expected-evidence fields changed in WBS. Ten referenced
  document/artifact paths and every named concrete test resolve; eleven historical
  source-commit/artifact bindings were verified with `git cat-file -e`.
- `git diff --check`: **PASS**.

No product test, broad suite, service/infrastructure run or lifecycle write was run.
