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

- Pure-domain focused tests: 47 passed, 26 integration cases deselected.
- Service Pyright: 0 errors, 0 warnings after resolving row typing/optional-row
  findings; no type-check suppression added.
- Ruff lint/format and diff checks: passed locally.
- Real PostgreSQL persistence tests: pending the pushed revision's CI run.
  No local DB execution or passing remote result is claimed in this revision.

Planned coverage: schema creation/replay; all entity identity/revision round
trips; route visit order independent of visit-ID sorting; repeated classes with
distinct visit IDs; foreign keys; invalid fields; duplicate IDs/positions;
atomic route rollback; runtime DDL/ledger/update/delete denial; cross-schema
write denial; admin/migration credential rejection for runtime use; migration
role-membership and ledger-tampering rejection.

No API/query-contract work, later migration, lifecycle advancement, shared
deployment or full-WP DONE/CONTRACT_READY claim. Full security/architecture,
scenario/benchmark verification and post-merge acceptance remain pending.
