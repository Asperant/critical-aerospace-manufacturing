# Platform runtime composition — Docker Compose profiles (WP-PLAT-001)

`compose.yaml` is the canonical runtime definition of the platform (FR-PLAT-001,
FR-PLAT-002). Profiles follow 02 "Local Development Environment"; the same
definitions are the basis of the shared Integration environment (WP-PLAT-003).

| Profile | Composition (02) | Status in this repository |
|---|---|---|
| `infra` | PostgreSQL, event backbone, S3-compatible object storage, cache, identity provider | **defined** |
| `core` | infra + manufacturing-core, manufacturing-simulator, digital-twin-service, operations-bff | infra only; services join as their container builds land |
| `vision` | infra + Vision runtime, artifact storage, inspection fixtures | infra only |
| `ai` | infra + Twin/query interfaces, AI Intelligence, knowledge/RAG dependencies | infra only |
| `planning` | infra + Simulator, Twin snapshot source, Scheduler, Automation | infra + Temporal (WP-PLAT-003); application services join as their builds land |
| `platform` | application services + observability + health + operational tooling | infra + Temporal; observability runs from `infra/observability` |
| `full` | full logical topology under local resource limits (not the daily default) | infra + Temporal |
| `e2e` | deterministic test environment: fresh runtime, known schema/scenario/seed | infra + Temporal |

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
