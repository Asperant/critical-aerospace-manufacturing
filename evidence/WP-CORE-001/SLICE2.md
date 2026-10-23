# WP-CORE-001 — initial persistence slice

Accountable owner: Asrın Dündar (Asperant). This record supersedes the inference
in SLICE2-PREREQUISITES.md that missing shared migration tooling prevents any
service-owned implementation. That earlier record remains as historical evidence
of the checks and access failures actually observed.

## Prerequisite classification

- WBS CORE-001 explicitly includes authoring migrations and per-service DB
  roles/grants; its canonical context has no inbound dependency edges.
- Architecture lines 1542/1544 and 4914 require PostgreSQL 18, Core-owned
  schema/migrations and separate nonadministrative runtime/migration identities.
  Item 61 at specification line 119250 explicitly selects PostgreSQL 18.
- CORE-007 owns shared migration tooling/layout choice, platform role wiring
  and CD/status surfaces. DEP-006 and DEP-007 constrain DN-RT-PG; no new
  HARD START edge from them to CORE-001 is invented. No producer DONE is needed.
- A local packaged SQL migration and explicit connection/role interface fit
  CORE-001 without selecting a shared framework or taking over CORE-007.
- Docker remains inaccessible locally. Existing CI provides disposable real
  PostgreSQL; its image override selects canonical 18 for the integration job
  rather than silently treating its old 16.4 default as the canonical target.

## Implemented scope

One initial migration: `core` schema; equipment, manufacturing_route,
route_visit, production_order, lot, serialized_component and a private
schema_migration ledger. Opaque identities/revisions, route-scoped unique visit
IDs, unique nonnegative visit positions, foreign keys and nonblank checks.
Operation classes can repeat. Runtime cannot update/delete identities or perform
DDL. The internal repository maps existing domain models and reconstructs visit
order explicitly. A failed visit insert rolls back the entire route insertion.

Operator-provided restricted roles and DSNs; no production credentials or
platform provisioning. Checksum-verified single-migration replay rejects drift;
runtime has only domain SELECT/INSERT plus schema USAGE. Tests use generated
transient identities only in an isolated fixture-created database. See the
service README for the concrete interface and its deployment limitations.

## Verification at implementation revision

Implementation SHA: `0b0412e0b507cee6ea384bb8731621244d8a2b2f`.

- Pure-domain focused tests: 47 passed, 26 integration cases deselected.
- Service Pyright: 0 errors, 0 warnings after resolving row typing/optional-row
  findings; no type-check suppression added.
- Ruff lint/format and diff checks: passed locally.
- Real PostgreSQL persistence tests: **26 passed, 0 failed** in 0.75 seconds
  in [CI run 39948962189, integration job 120398444962](https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/39948962189/job/120398444962).
  The completed job log confirms `CI_POSTGRES_IMAGE=postgres:18-alpine`,
  successful image startup, 2 existing infrastructure smoke tests passed,
  26 Core persistence tests passed, and successful fixture/service cleanup.
  Migration ran as the restricted migration login; repository tests ran as
  the distinct restricted runtime login. No local DB execution is claimed.
- The same implementation revision's `t1-static` and `t1-contract` jobs passed.
  Full pipeline completion is not claimed by this record; focused persistence
  verification is bound to the implementation SHA above, not to a later
  evidence-only commit.

Executed coverage: schema creation/replay; all entity identity/revision round
trips; route visit order independent of visit-ID sorting; repeated classes with
distinct visit IDs; foreign keys; invalid fields; duplicate IDs/positions;
atomic route rollback; runtime DDL/ledger/update/delete denial; cross-schema
write denial; admin/migration credential rejection for runtime use; migration
role-membership and ledger-tampering rejection.

No API/query-contract work, later migration, lifecycle advancement, shared
deployment or full-WP DONE/CONTRACT_READY claim. Full security/architecture,
scenario/benchmark verification and post-merge acceptance remain pending.
