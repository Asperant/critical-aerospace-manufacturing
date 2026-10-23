# WP-OBS-001 — Telemetry pipeline (OTel → Collector → OpenObserve): evidence

Owner: Yavuz Gümüş · supporting reviewer: Asrın · F1 · M1/S2 · readiness node
DN-RT-OBS · requirements FR-PLAT-006, NFR-OBS-001, NFR-OBS-002.

DoR: owner assessment on the Plane work item (READY verified 2026-10-23);
implementation start on the same item (IN_PROGRESS verified 2026-10-23).

## Deliverables (04 card)

| Deliverable | Where |
|---|---|
| structured log field standard | `packages/observability/src/cap_observability/schemas/` (`cap.resource/v1`, `cap.log/v1`, `cap.health/v1`), checks in `standard.py`, field tables in `packages/observability/README.md` |
| Collector pipeline configuration | `infra/observability/otel-collector.yaml` (OTLP → memory limiter → batch → OpenObserve, logs/metrics/traces) |
| OpenObserve deployment and dashboards | `infra/observability/compose.yaml`, `stack.sh`, `dashboards/telemetry-pipeline.json`, `dashboards.py` |
| OTel SDK wiring per service | `cap_observability.telemetry.configure()` (JSON stdout logs + OTLP logs, traces, metrics) and `cap_observability.health.health_report()`; per-deployable adoption tracked in `infra/observability/coverage.json` |

## Slices

| Slice | Commit | Content |
|---|---|---|
| A | `982188a` | resource and log schemas, `check-logs`, CI unit step, CODEOWNERS |
| B | `97736ed`, `a93b8aa` | Collector + OpenObserve stack, REAL integration smoke in CI |
| C | `e0723a1` | service helper `configure()`, OTLP log handler, trace correlation |
| D1 | `daa1808` | health surface contract, deployable coverage check |
| D2 | `b1605d2` | dashboards and importer, evidence, trace (03/04) |
| run | after `b1605d2` | RUN-OBS-001-DEV-001 recorded |
| pull fix | `48e6b7e` | image pulls with retries and a Docker Hub fallback (CI hit the public.ecr.aws anonymous quota) |
| main merge | before PR | main `1e54f9c` merged; `operations-bff` and `command-center-web` declared in coverage |

All of the above were squash-merged to main as `46b4305` by PR #40.

## Verification

| Asset | Family | Boundary mode | Where it runs |
|---|---|---|---|
| `packages/observability/tests/` (TEST-OBS-001-001, -003 in 03 §19.4) | TEST-OBS-LOGS, TEST-OBS-HEALTH | FIXTURE_ALLOWED (no network) | CI t1-unit |
| `python -m cap_observability check-coverage` (TEST-OBS-001-004) | TEST-OBS-HEALTH, TEST-OBS-LOGS | repository inspection | CI t1-unit |
| `infra/observability/tests/test_definitions.py` | TEST-OBS-TELEMETRY (static) | — | CI t1-unit |
| `infra/observability/tests/test_pipeline_integration.py` (TEST-OBS-001-002) | TEST-OBS-TELEMETRY | REAL Collector + OpenObserve | CI t1-integration |
| RUN-OBS-001-DEV-001 | all of the above | REAL | shared host (DEV) |

Negative paths covered: missing or invalid fields, secrets in keys and values,
oversized records, ERROR without `error_code`, span id without trace id,
invalid resource classes, a not-live service reported as ready, a claimed health
status that contradicts its checks, unreachable Collector (bounded queue, drops
counted, the service keeps running), coverage claimed for a deployable that does
not use the helpers, expired or unbounded exemptions, dashboards with a wrong
column name.

## Development run RUN-OBS-001-DEV-001

Produced by `collect_run.py` on the shared host at the revision recorded in
`RUN-OBS-001-DEV-001/record.json`. Credentials, host paths and the host name
are replaced with placeholders. Files: `record.json` (steps, exit codes),
logs of `stack.sh up`, unit tests, `check-coverage`, dashboard import, the REAL
integration tests, `status` and `down`, plus `sample-logs.jsonl` (records
emitted by `configure()`, including a redacted secret and an error with
`error_code`) and its `check-logs` result.

Read it as a development observation on the shared host, not as acceptance
evidence on the INTEGRATION environment.

## Merge and post-merge validation

| Fact | Value |
|---|---|
| Implementation PR | #40, squash-merged 2026-10-23T21:08:43Z, work branch deleted |
| Merge revision | `46b430586f4a6b4a1e4a497c3b41909d9c6fb38e` (parent `1e54f9c`, the main revision the branch was tested against) |
| PR head CI | push run 40021503686 and pull_request run 40022851765: all T1 jobs and `ci-gate` succeeded |
| Plane | IN_REVIEW verified for PR #40 |

**Workflow sequence deviation.** PR #40 was merged before the MERGE_READY
transition was recorded, so the guarded helper could no longer record
MERGE_READY (it requires an open PR) or MERGED (it requires MERGE_READY) for
PR #40. The MERGE_READY conditions held at the merge: head CI green, the PR
mergeable and not behind main (main was still `1e54f9c`), and the PR
description had passed the helper's own `pr_governance` check before the PR was
opened. No state was changed by hand: the remaining transitions are recorded
through this follow-up PR (`wp/WP-OBS-001-post-merge`), which carries this
record, and the post-merge validation runs on main at its merge revision.
Lesson applied: an irreversible step (merge) is taken only after the preceding
transition has returned VERIFIED.

## Limitations and follow-ups

- **NFR-OBS-001/002 are coverage measures over the nine mandatory
  deployables.** Three exist today: `manufacturing-core`, and
  `operations-bff` and `command-center-web` from WP-UI-001 (which bring their
  own access log and `/healthz`). Their adoption of the standard is PENDING
  with owned exemptions in `coverage.json` (owner agreement needed, Asrın). The
  other six are NOT_PRESENT and adopt the helpers when they are created; CI
  prints the current figure on every run. `observed` stays `null` in 03.
  RUN-OBS-001-DEV-001 was recorded before main was merged and shows 1/9.
- **INTEGRATION host:** the stack runs on a developer or shared host and in CI;
  composition into the capability profiles and the shared Integration host is
  WP-PLAT-001 / WP-PLAT-003 (DEP-011, DEP-109).
- **Trace propagation across services** (HTTP, NATS, Temporal) is WP-OBS-002.
- No sealed EvidenceID, accepted measurement or VERIFIED state is claimed.
