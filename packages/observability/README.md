# cap-observability — telemetry field standard (WP-OBS-001)

Shared observability support for every team-owned service (02 monorepo layout:
`packages/observability`; a sanctioned shared surface under ARCH-INV-025). Slice A
publishes the **field standard**: what identity every process carries and what a
structured log line looks like, so that logs, metrics and traces from different
owners can be correlated in OpenObserve (FR-PLAT-006, NFR-OBS-002).

Sources: 01 Item 47 §11–§40 (ObservabilityContext, correlation identities,
structured logging, payload governance), Item 43 §4–§7 (EnvironmentClass,
EnvironmentID, RuntimeProfile).

## Contracts

| Contract | Schema | Example |
|---|---|---|
| `cap.resource/v1` — resource attributes | `src/cap_observability/schemas/resource.schema.json` | `resource.json` |
| `cap.log/v1` — structured log record | `src/cap_observability/schemas/log-record.schema.json` | `log-record.json` |

Both schemas and examples are validated by the CI contract tier
(`ci/scripts/check_contracts.py`); the rules below are tested in CI t1-unit.

## Resource attributes (`cap.resource/v1`)

Attached once per process to all logs, metrics and traces. OpenTelemetry
semantic-convention names where one exists; `cap.*` for project identities.

| Attribute | Required | Meaning |
|---|---|---|
| `service.name` | yes | ServiceName, kebab-case: one of the nine deployables or a platform component |
| `service.version` | yes | version of the running code |
| `service.instance.id` | no | replica or process identity |
| `deployment.environment.name` | yes | EnvironmentID, for example `local-yavuz`, `integration-main` |
| `cap.environment.class` | yes | `LOCAL`, `INTEGRATION`, `EVALUATION`, `DEMO` or `CI_EPHEMERAL` |
| `cap.runtime.profile` | no | `infra`, `core`, `vision`, `ai`, `planning`, `platform`, `full`, `e2e` — never an environment class |
| `cap.release.id` | for EVALUATION and DEMO | ReleaseID; evaluation runs are pinned to an exact release |
| `cap.deployment.id` | no | DeploymentRecord identity |

## Log record (`cap.log/v1`)

One JSON object per line. Field names are the canonical names of Item 47 §29.
Only relevant context is carried (§13); unknown top-level fields are rejected so
that every owner emits the same shape.

| Field | Required | Rule |
|---|---|---|
| `timestamp` | yes | UTC RFC 3339 with `Z` |
| `severity` | yes | `DEBUG`, `INFO`, `WARN`, `ERROR`, `FATAL` |
| `service` | yes | same as `service.name` |
| `service_version` | no | same as `service.version` |
| `environment` | yes | EnvironmentID, same as `deployment.environment.name` |
| `environment_class` | no | same as `cap.environment.class` |
| `release` | no | ReleaseID |
| `event_name` | yes | stable `domain.event` name in lower snake case, e.g. `scheduler.validation_failed` (§30) |
| `message` | yes | human text, at most 2048 characters; facts also go in fields (§31) |
| `trace_id` | no | 32 lower-case hex, not all zero (W3C) |
| `span_id` | no | 16 lower-case hex, not all zero; requires `trace_id` |
| `correlation_id` | no | broader business-flow identity (§17) |
| `causation_id` | no | direct causal predecessor (§18) |
| `request_id` | no | ingress request identity (§16) |
| `error_code` | for ERROR and FATAL | stable code, `UPPER_SNAKE` (§32–§33) |
| `error_type` | no | error class or category |
| `world_id` | no | simulation world (PRIMARY, WHAT_IF, REPLAY, COUNTERFACTUAL instance) |
| `simulation_run_id` | no | run identity |
| `workflow_instance_id` | no | run identity |
| `agent_run_id` | no | run identity |
| `scheduling_run_id` | no | run identity |
| `data_pipeline_run_id` | no | run identity |
| `evaluation_run_id` | no | run identity |
| `deployment_id` | no | DeploymentRecord identity |
| `entity_refs` | no | at most 10 `{type, id}` references, never full rows (§34–§35) |
| `attributes` | no | at most 16 scalar diagnostics, strings at most 256 characters, no nesting |

Identifiers (`correlation_id`, run IDs, `entity_refs[].id`) match
`[A-Za-z0-9_.:-]{1,128}`, the rule manufacturing-core already enforces for
correlation IDs. The three correlation identities stay separate (§19): an
EventID is not a TraceID, and a replay may carry a new trace (§22–§23).

## Rules a schema cannot express

`check_log_record` adds these to the schema check (Item 47 §34–§36):

- **No secrets, ever.** Attribute keys that name a secret (password, token, API
  key, authorization, credential, connection string, private key, cookie, session
  ID) and values that look like one (GitHub or AWS keys, private key blocks,
  bearer tokens, credentials in URLs, `password=` assignments) are violations.
- **No payloads.** A record above 8 KiB is a violation: log an artifact or entity
  reference instead of image bytes, model artifacts, schedule blobs or rows.

## Use

**In a service** (slice C) — one call at start-up, ordinary `logging` afterwards:

```python
import logging
from cap_observability.telemetry import configure

telemetry = configure("manufacturing-core", "0.1.0")
log = logging.getLogger(__name__)
log.info(
    "order query finished",
    extra={"event_name": "core.query_completed", "correlation_id": cid,
           "attributes": {"duration_ms": 12.5}},
)
telemetry.shutdown()  # on exit: flushes everything still queued
```

| Environment variable | Meaning |
|---|---|
| `CAP_ENVIRONMENT` | EnvironmentID; defaults to `local-<user>` only for LOCAL |
| `CAP_ENVIRONMENT_CLASS` | `LOCAL` (default), `INTEGRATION`, `EVALUATION`, `DEMO`, `CI_EPHEMERAL` |
| `CAP_RELEASE_ID` | required for EVALUATION and DEMO |
| `CAP_DEPLOYMENT_ID`, `CAP_RUNTIME_PROFILE`, `CAP_SERVICE_INSTANCE_ID` | optional identities |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Collector base URL, e.g. `http://127.0.0.1:54318`; unset means stdout only |

Every record is written to stdout as one `cap.log/v1` line. With an endpoint,
the same records go to the Collector (`OtlpLogHandler`, bounded queue, never
blocks or raises) and OpenTelemetry tracing and metrics are exported there too;
log lines inside a span carry its `trace_id` and `span_id`. Records are made to
conform rather than rejected: invalid context is dropped, secrets are redacted,
oversize payloads are shed, and ERROR/FATAL without a code get
`UNCLASSIFIED_ERROR` so that the gap is visible and searchable.

Logs use the project's own small OTLP shipper because OpenTelemetry's Python log
SDK is still experimental and its `LoggingHandler` is deprecated (1.45); traces
and metrics use the stable OpenTelemetry SDK (`otel` extra).

**Checking files:**

```bash
# check JSON Lines log files (exit 0 conform, 1 violations, 2 usage/unreadable)
uv run --project ci --locked python -m cap_observability check-logs service.log.jsonl
```

```python
from cap_observability import check_log_record, check_resource
assert check_log_record(record) == []
```

Validation needs the `validate` extra (jsonschema); emitting never does.

## Adoption

Services adopt `configure` with their owners. manufacturing-core is the first
candidate; its existing structured health record is changed only together with
its owner.

## Tests

```bash
uv run --project ci --locked python -m pytest packages/observability/tests -q -p pytest_quarantine
uv run --project ci --locked pyright --project packages/observability/pyrightconfig.json
```
