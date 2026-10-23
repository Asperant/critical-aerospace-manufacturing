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
| D2 | this commit | dashboards and importer, evidence, trace (03/04) |

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

## Limitations and follow-ups

- **NFR-OBS-001/002 are coverage measures over the nine mandatory
  deployables.** Only `manufacturing-core` exists today; its adoption of
  `configure()` and `health_report()` is PENDING with an owned exemption in
  `coverage.json` (owner agreement needed, Asrın). The other eight are
  NOT_PRESENT and adopt the helpers when they are created; CI prints the
  current figure on every run. `observed` stays `null` in 03.
- **INTEGRATION host:** the stack runs on a developer or shared host and in CI;
  composition into the capability profiles and the shared Integration host is
  WP-PLAT-001 / WP-PLAT-003 (DEP-011, DEP-109).
- **Trace propagation across services** (HTTP, NATS, Temporal) is WP-OBS-002.
- No sealed EvidenceID, accepted measurement or VERIFIED state is claimed.
