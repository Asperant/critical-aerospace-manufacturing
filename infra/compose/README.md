# Platform runtime composition — Docker Compose profiles (WP-PLAT-001)

`compose.yaml` is the canonical runtime definition of the platform (FR-PLAT-001,
FR-PLAT-002). Profiles follow 02 "Local Development Environment"; the same
definitions are the basis of the shared Integration environment (WP-PLAT-003).

| Profile | Composition (02) | Status in this repository |
|---|---|---|
| `infra` | PostgreSQL, event backbone, S3-compatible object storage, cache, identity provider | **defined** |
| `core` | infra + manufacturing-core, manufacturing-simulator, digital-twin-service, operations-bff | infra only; services join as their container builds land |
| `vision` | infra + Vision runtime, artifact storage, inspection fixtures | infra + MLflow (WP-PLAT-003) |
| `ai` | infra + Twin/query interfaces, AI Intelligence, knowledge/RAG dependencies | infra + Qdrant + MLflow (WP-PLAT-003) |
| `planning` | infra + Simulator, Twin snapshot source, Scheduler, Automation | infra + Temporal (WP-PLAT-003); application services join as their builds land |
| `platform` | application services + observability + health + operational tooling | infra + Temporal + Qdrant + MLflow; observability runs from `infra/observability` |
| `full` | full logical topology under local resource limits (not the daily default) | infra + Temporal + Qdrant + MLflow |
| `e2e` | deterministic test environment: fresh runtime, known schema/scenario/seed | infra + Temporal + Qdrant + MLflow |

## infra layer

| Service | Image (exact pin) | Host port (localhost) | Memory limit | Health check |
|---|---|---|---|---|
| PostgreSQL | `postgres:18.6-alpine` | 25432 | 1 GiB | `pg_isready` |
| NATS JetStream | `nats:2.10.22-alpine` | 24222 (monitor 28222) | 256 MiB | `/healthz?js-enabled-only=true` |
| Valkey | `valkey/valkey:8.0.1-alpine` | 26379 | 256 MiB | `PING` |
| SeaweedFS (S3) | `chrislusf/seaweedfs:3.80` | 28333 (master 29333) | 512 MiB | master `/cluster/status` and an HTTP answer from the S3 gateway |
| Keycloak | `quay.io/keycloak/keycloak:26.0.5` | 28080 | 1 GiB | management `/health/ready` |

Total infra limit: 3 GiB of the ~16 GiB single host (02 resource profiles:
limits are mandatory so that OpenObserve/Qdrant cannot starve PostgreSQL).
Host ports stay below 32768, outside the Linux ephemeral port range
(32768–60999): a fixed host port inside that range can be taken by an outgoing
client connection, and Docker then fails to bind it (seen on a CI runner in run
40099708897). A static test enforces this.

## Workflow engine (WP-PLAT-003)

Temporal runs self-hosted on the same PostgreSQL (02: PostgreSQL persistence, no
Cassandra) in the `planning`, `platform`, `full` and `e2e` profiles.

| Service | Image (exact pin) | Host port (localhost) | Memory limit | Health / role |
|---|---|---|---|---|
| `temporal-schema` | `temporalio/admin-tools:1.32.1` | — | 256 MiB | one-shot: creates `temporal` and `temporal_visibility` and applies the versioned schemas; idempotent |
| `temporal` | `temporalio/server:1.32.1` | 27233 (gRPC), 27243 (HTTP API) | 768 MiB | frontend `/api/v1/system-info`; starts only after the schema job succeeded |
| `temporal-namespace` | `temporalio/admin-tools:1.32.1` | — | 128 MiB | registers the platform namespace (`CAP_TEMPORAL_NAMESPACE`, default `cap`) and stays up as its probe: healthy only while it is registered |

Workflow definitions, task queues and further namespaces belong to their owners
(Temporal semantics: Batuhan; runtime: Yavuz, 02). Temporal currently connects as
the platform PostgreSQL user; a dedicated least-privilege role is a known limitation.
`stack.sh env` adds `CAP_TEMPORAL_ADDRESS`, `CAP_TEMPORAL_HTTP_URL` and `CAP_TEMPORAL_NAMESPACE`.

## Retrieval and experiment tracking (WP-PLAT-003)

| Service | Image (exact pin) | Host port (localhost) | Memory limit | Health / role |
|---|---|---|---|---|
| `qdrant` | `qdrant/qdrant:v1.19.2` | 26333 (HTTP), 26334 (gRPC) | 512 MiB | `/readyz`; every API request needs the per-host key `CAP_QDRANT_API_KEY`; rebuildable RAG projection, never a canonical store (02) |
| `mlflow-init` | `cap-platform/mlflow:3.16.1-cap1` (built from `mlflow/Dockerfile`) | — | 256 MiB | one-shot: creates the `mlflow` database and the `cap-mlflow-artifacts` bucket; the only holder of the S3 admin identity |
| `mlflow` | same image | 25000 | 768 MiB | `/health`; metadata in PostgreSQL, artifacts in SeaweedFS served through the server with the bucket-scoped `cap-mlflow` identity; tracking support, never the model-governance authority (02) |

The MLflow image is the upstream `ghcr.io/mlflow/mlflow:v3.16.1` plus exactly two pinned
wheels (PostgreSQL driver, S3 client), running as a non-root user. Server-side job
execution is disabled: it is not tracking support and its consumer pool exhausted
the memory limit. `stack.sh` restarts a running SeaweedFS when the S3 identities
change, because the gateway reads them only at start. `stack.sh env` adds
`CAP_QDRANT_URL`, `CAP_QDRANT_API_KEY` and `CAP_MLFLOW_URL`.

## Platform realm (WP-PLAT-003)

Keycloak starts with `--import-realm` and creates the `cap-platform` realm from the
`keycloak-platform-realm` config in `compose.yaml` when it does not exist yet (an
existing realm is never overwritten). The realm holds one confidential
service-account client, `cap-platform-smoke`, that proves the identity provider
issues real tokens (05 DEP-010); its secret is a placeholder resolved by Keycloak
from `keycloak.env`, generated per host by `stack.sh`. Roles, users, the BFF/UI OIDC
clients and TLS belong to WP-SEC-001. `stack.sh env` adds `CAP_KEYCLOAK_REALM`,
`CAP_KEYCLOAK_SMOKE_CLIENT_ID` and `CAP_KEYCLOAK_SMOKE_CLIENT_SECRET`.

## Runtime readiness checklist (WP-PLAT-003, E2E-01 gate)

`readiness.json` lists every runtime edge out of DN-PLAT-INTEG in 05 (DEP-005,
DEP-007…015) with 05's own consumer node, strength, stage, required readiness,
need-by and precise requirement, plus the services that realize it and the REAL
checks that prove it. A static test fails when the list and 05 disagree, when an
edge is missing, or when a named service or check does not exist.

```bash
infra/compose/stack.sh readiness   # OK/WAIT per edge; exit 1 when a HARD edge is not healthy
```

DEP-011 is served by the observability stack (`infra/observability`, WP-OBS-001), so
it shows WAIT until that stack runs too. Health is read from Docker's project labels,
not through a Compose file (the observability file needs credentials just to render);
its two services have no Docker health check, so they are probed on the HTTP surfaces
`infra/observability/stack.sh` itself waits for. The list is a checklist and a live health
view; a readiness claim rests on the recorded run on the shared host.

## Startup order and recovery (WP-PLAT-003, 02 Sequence I)

`compose up` follows 02 Sequence I: identity (Keycloak) → data stores (PostgreSQL,
SeaweedFS, Valkey, Qdrant, the Temporal and MLflow stores) → event backbone (NATS),
with application services after them as they land. A service waits only for the
health or completion of a service in its own or an earlier layer, never with a bare
start order, and the wait graph has no cycle (static tests). Nothing waits without a
real runtime need: PostgreSQL does not wait for Keycloak's slow first boot.

After a host reboot Docker restarts containers itself, all at once and without
`depends_on`. Recovery then rests on health checks plus `restart: unless-stopped`:
a service that started before its store (Temporal before PostgreSQL) exits and is
restarted until the store answers. Setup jobs do not run on reboot; they are
idempotent and rerun with the next `stack.sh up`. `stack.sh up` waits up to 11
minutes, because Keycloak's first `start-dev` boot builds Quarkus (205 s measured
on the shared host).

## Run it

```bash
infra/compose/stack.sh up infra        # pulls pinned images, waits until every service is healthy,
                                       # prints startup-to-healthy seconds
eval "$(infra/compose/stack.sh env | sed 's/^/export /')"
uv run --project ci --locked python -m pytest infra/compose/tests -m integration -q
infra/compose/stack.sh config core     # render a profile without starting anything
infra/compose/stack.sh down            # keeps data and credentials; `reset` removes both
```

Credentials (PostgreSQL user `cap`, Keycloak admin `cap-admin`) are generated
once per machine by `stack.sh` in `~/.local/state/cap-platform/` (mode 0600,
never committed; override with `CAP_PLATFORM_STATE_DIR`): `credentials.env` for
the script, `postgres.env`, `keycloak.env` and `s3.json` read by Compose. Because Compose
reads them itself, plain `docker compose` and `mfgctl` work after the first
`stack.sh up`; only `stack.sh env` prints them.

## Through mfgctl

`infra/mfgctl/capabilities.json` is the registry instance of the
`mfgctl.capabilities/v1` contract (DEP-003), so the developer CLI drives the
same definitions:

```bash
uv run --project ci --locked mfgctl profile list
uv run --project ci --locked mfgctl up infra        # docker compose ... --profile infra up --wait
uv run --project ci --locked mfgctl smoke platform-infra
uv run --project ci --locked mfgctl down infra
```

## Decisions

- **One definition, many profiles.** Infrastructure services carry every
  profile, so any profile starts on top of the same `infra` layer (02).
- **Pinned releases.** Exact tags, upgraded only by deliberate PRs.
- **Development modes, stated.** Keycloak runs `start-dev` (file-backed realm
  data); it is localhost-only. Production-like identity storage in PostgreSQL
  belongs to the identity work package.
- **S3 identities (WP-OBJ-001).** `s3.json` defines three SeaweedFS identities with
  generated secrets: `cap-artifacts-admin` (creates buckets), `cap-artifacts-writer`
  (read, list, write the artifact buckets) and `cap-artifacts-reader` (read only;
  signs short-lived read capabilities). With identities defined, anonymous S3
  access is denied. `stack.sh env` prints them as `CAP_S3_ACCESS_KEY`/`CAP_S3_SECRET_KEY`
  (writer), `CAP_S3_ADMIN_*` and `CAP_S3_READER_*`; buckets are created with
  `python -m cap_artifacts ensure-buckets`. Existing credential files are completed,
  never regenerated.
- **Health is the contract.** `stack.sh up` returns only when every service's
  health check passes (`docker compose up --wait`).

## Not in this slice

Container builds and composition of the application deployables (agreed with
their owner), the startup-to-healthy measurement record and the Integration
composition (with WP-PLAT-003).
