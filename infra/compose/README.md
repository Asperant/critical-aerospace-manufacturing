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
| `planning` | infra + Simulator, Twin snapshot source, Scheduler, Automation | infra only |
| `platform` | application services + observability + health + operational tooling | infra only; observability runs from `infra/observability` |
| `full` | full logical topology under local resource limits (not the daily default) | infra only |
| `e2e` | deterministic test environment: fresh runtime, known schema/scenario/seed | infra only |

## infra layer

| Service | Image (exact pin) | Host port (localhost) | Memory limit | Health check |
|---|---|---|---|---|
| PostgreSQL | `postgres:18.6-alpine` | 56432 | 1 GiB | `pg_isready` |
| NATS JetStream | `nats:2.10.22-alpine` | 56222 (monitor 56822) | 256 MiB | `/healthz?js-enabled-only=true` |
| Valkey | `valkey/valkey:8.0.1-alpine` | 56379 | 256 MiB | `PING` |
| SeaweedFS (S3) | `chrislusf/seaweedfs:3.80` | 56333 (master 56933) | 512 MiB | master `/cluster/status` |
| Keycloak | `quay.io/keycloak/keycloak:26.0.5` | 56080 | 1 GiB | management `/health/ready` |

Total infra limit: 3 GiB of the ~16 GiB single host (02 resource profiles:
limits are mandatory so that OpenObserve/Qdrant cannot starve PostgreSQL).
Ports differ from the CI integration services (55xxx) and the observability
stack (53xxx–55080), so all three can run side by side.

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
per machine in `~/.local/state/cap-platform/credentials.env` (mode 0600, never
committed) and printed only by `env`.

## Decisions

- **One definition, many profiles.** Infrastructure services carry every
  profile, so any profile starts on top of the same `infra` layer (02).
- **Pinned releases.** Exact tags, upgraded only by deliberate PRs.
- **Development modes, stated.** Keycloak runs `start-dev` (file-backed realm
  data) and SeaweedFS's S3 gateway has no identities yet; both are localhost-only.
  Production-like identity storage in PostgreSQL and S3 identities belong to the
  identity and artifact-store work packages.
- **Health is the contract.** `stack.sh up` returns only when every service's
  health check passes (`docker compose up --wait`).

## Not in this slice

Container builds and composition of the application deployables (slice 2),
`infra/mfgctl/capabilities.json` for `mfgctl profile/up/smoke` (slice 3),
startup-to-healthy measurement record (slice 4) and the Integration composition
(slice 5, with WP-PLAT-003).
