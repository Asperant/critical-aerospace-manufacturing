# WP-CORE-001 — persistence slice prerequisite check

Accountable developer: Asrın Dündar (Asperant).
Assessment revision: the commit containing this record.
Result: BLOCKED for this slice; no persistence implementation or verification
is claimed. WP execution state remains IN_PROGRESS as requested.

## Exact inputs inspected

- `projectctl context WP-CORE-001`: no inbound dependency edges; this does
  not certify runtime availability or migration/role artifacts.
- `projectctl context WP-CORE-007`: migration runner/repository layout,
  per-service role/grant definitions and migration status wiring are its
  explicit deliverables. These are not silently implemented under CORE-001.
- `docs/02_System_Architecture_Specification.md`: logical schema separation
  at line 1544, real PostgreSQL/empty-database migration verification at
  line 1636, separate migration/runtime identities and no service superuser
  at line 4914.
- `ci/scripts/integration_services.sh` and
  `ci/integration/test_runtime_services.py`: existing throw-away PostgreSQL
  16.4 admin smoke fixture; no Core migration/runtime role contract.
- `git ls-files '*migration*' '*alembic*' '*compose*' '*.sql' '*CORE-007*'`:
  no tracked migration runner/configuration, SQL, Compose or CORE-007 artifact.
- Fresh `cap-plane-queue`: CORE-001 IN_PROGRESS, unblocked, health HEALTHY;
  CORE-007 candidate WAITING_DEP with missing DEP-006 / DN-PLAT-COMPOSE
  SKELETON_READY artifact and accountable evidence. This candidate diagnostic
  is not a newly invented HARD START edge for CORE-001, nor a requirement
  that the entire producer WP reach DONE.

## Actual local runtime access checks

- `command -v docker psql`: Docker exists at `/usr/bin/docker`; psql absent.
- `/usr/bin/pg_isready` and `/usr/lib/postgresql`: absent.
- `docker ps --filter ancestor=postgres:16.4-alpine --format '{{.Names}} {{.Status}} {{.Ports}}'`:
  denied access to `/var/run/docker.sock`.
- The same filtered read through `sudo -n /usr/bin/docker ps ...`:
  `sudo: interactive authentication is required`.

These failures do not establish that no PostgreSQL server exists. They establish
that this session cannot inspect/start the approved container fixture through
the available Docker access, and no approved Core database connection/role
surface was supplied by the inspected artifacts. No credentials were read,
copied or invented; no shared database was touched.

## Resolution needed

Publish the concrete migration layout/runner and scoped migration/runtime role
interface through the CORE-007/platform workflow, and provide an accessible
disposable real PostgreSQL test runtime. Actual artifacts/access are needed,
not a producer-WP DONE label. Owner routing: Asrın for CORE-007 artifacts;
Yavuz for platform runtime/access coordination.

Then implement the first Core-owned migration and minimal repository mapping,
and execute schema/identity/revision/route-order/visit-identity/referential
integrity/round-trip tests. All slice-2 tests are NOT_EXECUTED; migrations,
repositories and database evidence are NOT_PRODUCED. No API/query contract,
later migration or lifecycle advancement occurred.
