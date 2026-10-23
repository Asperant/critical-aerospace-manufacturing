# Observability runtime — OTel Collector → OpenObserve (WP-OBS-001)

Every team-owned service sends its logs, metrics and traces as OTLP to the
**OpenTelemetry Collector**; the Collector batches them and forwards them to
**OpenObserve** (single node), where they are searched and correlated
(FR-PLAT-006; 01 Item 47, Item 61 §176–§182). Field names follow the standard in
`packages/observability` (`cap.resource/v1`, `cap.log/v1`).

| File | Purpose |
|---|---|
| `compose.yaml` | the two services: pinned images, localhost-only ports, memory limits, credentials only from the environment |
| `otel-collector.yaml` | OTLP receivers → memory limiter → batch → OpenObserve exporter, for logs, metrics and traces |
| `stack.sh` | `up` / `down` / `reset` / `env` / `status` / `logs`; creates throw-away credentials outside the repository |
| `tests/test_definitions.py` | static checks of the two files (CI t1-unit, no Docker) |
| `tests/test_pipeline_integration.py` | REAL smoke: a log, a span and a counter must become queryable (CI t1-integration) |

## Run it

```bash
infra/observability/stack.sh up        # starts both, waits for /healthz and the Collector health check
eval "$(infra/observability/stack.sh env | sed 's/^/export /')"
uv run --project ci --locked python -m pytest infra/observability/tests -m integration -q
infra/observability/stack.sh down      # keeps data and credentials; `reset` removes both
```

| Endpoint (localhost) | Port | Use |
|---|---|---|
| OpenObserve UI and API | 55080 | `http://127.0.0.1:55080`, user `root@cap.local` |
| OTLP/HTTP | 54318 | services send here (`/v1/logs`, `/v1/metrics`, `/v1/traces`) |
| OTLP/gRPC | 54317 | services send here |
| Collector health | 53133 | `GET /` returns 200 when the pipelines run |

Override any port with `O2_HTTP_PORT`, `OTLP_HTTP_PORT`, `OTLP_GRPC_PORT`,
`OTEL_HEALTH_PORT`. The UI password is in
`~/.local/state/cap-observability/credentials.env` (mode 0600, never committed),
or set `O2_ROOT_PASSWORD` yourself before the first `up`.

## Decisions

- **Collector in front, not direct export.** Services know one endpoint; the
  backend can change, batching and memory limits live in one place, and
  credentials stay out of every service.
- **Pinned releases.** OpenObserve `v1.0.4` (2026-09-24) and Collector contrib
  `0.162.0` (2026-09-29), both at least two weeks old when pinned. Upgrades are
  deliberate PRs, never `latest`.
- **Single-host budget.** OpenObserve is limited to 1 GiB and the Collector to
  256 MiB (02 resource profiles: OpenObserve must not starve PostgreSQL); the
  Collector's `memory_limiter` keeps it below its limit under bursts.
- **No phone-home.** `ZO_TELEMETRY=false`.

## Not in this slice

Composition into the capability profiles and the shared Integration host
(WP-PLAT-001, WP-PLAT-003; DEP-011), service SDK wiring and dashboards (later
WP-OBS-001 slices), retention and alerting (later OBS work packages).
