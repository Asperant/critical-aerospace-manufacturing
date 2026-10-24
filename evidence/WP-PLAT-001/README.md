# WP-PLAT-001 — Compose profiles and mandatory runtime composition: evidence

Owner: Yavuz Gümüş · supporting reviewer: Asrın (advisory, CHG-018) · F0 · M1/S2 ·
readiness node DN-PLAT-COMPOSE · requirements FR-PLAT-001, FR-PLAT-002,
NFR-DEP-001, NFR-DEP-002, NFR-DEP-006.

DoR: owner assessment on issue #51 with DEP-003 producer readiness at
SKELETON_READY (READY verified 2026-10-24).

## Slices

| Slice | Content |
|---|---|
| 1 (`0c878e6`) | `infra/compose/compose.yaml` infra layer (PostgreSQL, NATS JetStream, Valkey, SeaweedFS, Keycloak) in all eight 02 profiles, `stack.sh`, static and REAL tests, CI steps, CODEOWNERS. Shared host: images pulled, all five healthy in 147 s on first start, 13 REAL tests passed |
| 2 (`013711c`, fix `6a50bfc`) | `infra/mfgctl/capabilities.json` (mfgctl.capabilities/v1 instance, DEP-003): eight profiles, `platform-infra` smoke through `stack.sh smoke`; credentials moved to Compose env files outside the repository so `mfgctl up` works without exported variables |

| 3 | `collect_run.py` (RUN-PLAT-001-DEV-001), trace (03 §19.5, 04 card) |

## Verification

| Asset | Family | Boundary mode | Where it runs |
|---|---|---|---|
| `infra/compose/tests/test_definitions.py` (TEST-PLAT-001-001) | TEST-PLAT-COMPOSE | static | CI t1-unit |
| `infra/compose/tests/test_runtime_integration.py` (TEST-PLAT-001-002) | TEST-PLAT-COMPOSE | REAL containers | CI t1-integration; `mfgctl smoke platform-infra` |
| RUN-PLAT-001-DEV-001 (BENCH-PLAT-001-001) | BENCH-DEP-STARTUP instrumentation | REAL | shared host (DEV) |

## Development run RUN-PLAT-001-DEV-001

Produced by `collect_run.py` on the shared host at the revision recorded in
`RUN-PLAT-001-DEV-001/record.json`: `stack.sh reset`, a fresh start of the
`infra` profile with images local, `mfgctl smoke platform-infra`, actual memory
use (`memory.txt`), `mfgctl status`, `down`, and a restart with existing data.
`record.json` holds both startup-to-healthy times against the 600 s NFR-DEP-002
threshold. Credentials, host paths and the host name are placeholders. It is a
DEV observation of the infra profile, not the full Integration profile on the
EVALUATION HardwareProfile, so `observed` stays null in 03.

## Readiness produced

DEP-006 (DN-PLAT-COMPOSE to DN-RT-PG, HARD START, SKELETON_READY, "local
PostgreSQL profile up") is the consumer gate of WP-CORE-007. After merge the
producer readiness is stated with the merge revision: PostgreSQL 18 in the
`infra` profile, started by `stack.sh up infra` or `mfgctl up infra`, healthy
by `pg_isready`, reachable on localhost with generated credentials.

## Profile set

02 defines the minimum profiles `infra, core, vision, ai, planning, platform,
full, e2e`; the 04 card lists `core, vision, ai, automation, full`. The 02 set
is implemented: automation belongs to `planning` in 02, and Integration is an
environment class, not a runtime profile (02, Item 43 §7).

## Findings

- **SeaweedFS health (slice 2 CI, run 40095981274).** The health check covered
  only the master; on the fast CI runner the container was reported healthy
  before the S3 gateway accepted connections, and the REAL test caught it
  (`Connection reset by peer`). The health check now also requires an HTTP
  answer from the S3 gateway; the test was not relaxed.

## Limitations and follow-ups

- **Application deployables.** manufacturing-core is a library plus a migration
  runner without a service process; operations-bff needs an identity-provider
  client, an edge/TLS entry point and real Core/Twin query APIs; the Command
  Center is served only by its test harness. Each joins its profiles when it is
  a runnable service; composing them now would decide other work packages'
  design. FR-PLAT-001's full composition and the Integration profile
  (WP-PLAT-003, DEP-004) stay open.
- **Observability in the `platform` profile.** The Collector and OpenObserve
  still start from `infra/observability/stack.sh`; joining them to `platform`
  needs their credentials moved to Compose env files first.
- **Development modes.** Keycloak `start-dev` and SeaweedFS S3 without
  identities, both localhost-only (see `infra/compose/README.md`).
- No sealed EvidenceID, accepted measurement or VERIFIED state is claimed.
