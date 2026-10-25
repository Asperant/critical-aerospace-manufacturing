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
| scoped artifact access API | — | slice 4 |

## Slices

| Slice | Content |
|---|---|
| 1 | contract and example, conventions, checksum helpers, unit tests TEST-OBJ-001-001 (FIXTURE_ALLOWED, t1-unit), CI step, CODEOWNERS; t1-static restored after #73 (Pyright `ci/tests` path) |
| 2 | signed S3 store client (SigV4), write-once finalization with read-back verification, version in the object key; stubbed-S3 tests TEST-OBJ-001-002 (t1-unit) and REAL SeaweedFS tests TEST-OBJ-001-003 (t1-integration); the first REAL run showed that the infra profile's `-volume.max=8` leaves no volumes for a third bucket (HTTP 500 on the first RC-C write), so the profile now allows 64 sparse volumes |

## What this evidence does not claim yet

Write-once is checked by prefix before upload, not yet by an atomic reservation
(slice 3). The local S3 gateway has no identities yet (slice 4). NFR-DATA-001's 100% measurement is an EVALUATION gate; FR-VIS-001 is
accepted on the integrated Vision path (E2E-01, AV-SCEN-01). DEP-009 (shared
Integration host) is assessed at its gate. The SHA-256 choice awaits its
confirming ADR (see `packages/artifacts/README.md`).
