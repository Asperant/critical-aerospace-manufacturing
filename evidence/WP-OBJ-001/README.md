# WP-OBJ-001 — Artifact service: ArtifactRef contract and object storage integration: evidence

Owner: Yavuz Gümüş · supporting reviewer: Selman (advisory, CHG-018) · F1 · M2/S3–S4 ·
readiness node DN-RT-OBJ · requirements FR-VIS-001, NFR-DATA-001.
DoR assessment on issue #62.

## Deliverables (04 card)

| Deliverable | Where | State |
|---|---|---|
| ArtifactRef contract | `packages/artifacts/src/cap_artifacts/schemas/artifact-reference.schema.json` (`cap.artifact-ref/v1`, IC-SHARED-001) | slice 1 |
| SeaweedFS buckets/prefix conventions | `packages/artifacts/README.md`, `cap_artifacts.conventions`, `ArtifactStore.ensure_buckets` | slices 1–2 |
| checksum/content-identity verification | `cap_artifacts.integrity`, `ArtifactReference.verify_bytes`, `ArtifactStore.store/read` | slices 1–2 |
| scoped artifact access API | `cap_artifacts.access.AccessIssuer` (pre-signed, single-object, ≤ 15 min read capabilities; authorization callback for the BFF), S3 identities in `infra/compose/stack.sh` | slice 4 (library and identities; BFF wiring with its owner) |

## Slices

| Slice | Content |
|---|---|
| 1 | contract and example, conventions, checksum helpers, unit tests TEST-OBJ-001-001 (FIXTURE_ALLOWED, t1-unit), CI step, CODEOWNERS; t1-static restored after #73 (Pyright `ci/tests` path) |
| 2 | signed S3 store client (SigV4), write-once finalization with read-back verification, version in the object key; stubbed-S3 tests TEST-OBJ-001-002 (t1-unit) and REAL SeaweedFS tests TEST-OBJ-001-003 (t1-integration); the first REAL run showed that the infra profile's `-volume.max=8` leaves no volumes for a third bucket (HTTP 500 on the first RC-C write), so the profile now allows 64 sparse volumes |
| 3 | PostgreSQL registry (`artifact` schema, Core migration pattern): atomic write-once by primary key, immutable identity/content and 02 lifecycle enforced by trigger, registry status governs reads, read-only consistency sweep; tests TEST-OBJ-001-004 (in-memory registry, t1-unit) and TEST-OBJ-001-005 (REAL PostgreSQL and SeaweedFS: replay ledger, no runtime DELETE/DDL, four concurrent writers → one success, missing bytes and orphans reported) |
| 4 | least-privilege S3 identities in the infra profile (admin/writer/reader, anonymous denied; existing credentials completed, never regenerated), read capabilities pre-signed by the reader, `python -m cap_artifacts ensure-buckets` and `consistency`; tests TEST-OBJ-001-006 (t1-unit) and TEST-OBJ-001-007 (REAL SeaweedFS: anonymous and wrong-identity requests refused, capability reads only its object, cannot write, tampered or expired capability refused) |

| 5 | trace (03 delta and §19.9, NFR-DATA-001 edges), 04 repository reference, RUN-OBJ-001-DEV-001 |

## RUN-OBJ-001-DEV-001

`collect_run.py` records a run on the shared host against the infra profile with
its S3 identities (boundary mode REAL): profile start, bucket creation with the
admin identity, the REAL store, registry and access tests (TEST-OBJ-001-003, -005,
-007; disposable database and roles), an anonymous listing probe (expects 403),
the consistency command without a registry DSN (expects a configuration error,
never a guessed DSN) and profile stop. Results are in
`RUN-OBJ-001-DEV-001/record.json` with the raw outputs next to it; credentials,
host paths and the host name are redacted.

## What this evidence does not claim yet

Upload capabilities and multipart upload are not implemented; the BFF does not
yet call `AccessIssuer`. NFR-DATA-001's 100% measurement is an EVALUATION gate; FR-VIS-001 is
accepted on the integrated Vision path (E2E-01, AV-SCEN-01). DEP-009 (shared
Integration host) is assessed at its gate. The SHA-256 choice awaits its
confirming ADR (see `packages/artifacts/README.md`).
