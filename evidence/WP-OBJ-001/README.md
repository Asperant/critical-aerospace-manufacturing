# WP-OBJ-001 — Artifact service: ArtifactRef contract and object storage integration: evidence

Owner: Yavuz Gümüş · supporting reviewer: Selman (advisory, CHG-018) · F1 · M2/S3–S4 ·
readiness node DN-RT-OBJ · requirements FR-VIS-001, NFR-DATA-001.
DoR assessment on issue #62.

## Deliverables (04 card)

| Deliverable | Where | State |
|---|---|---|
| ArtifactRef contract | `packages/artifacts/src/cap_artifacts/schemas/artifact-reference.schema.json` (`cap.artifact-ref/v1`, IC-SHARED-001) | slice 1 |
| SeaweedFS buckets/prefix conventions | `packages/artifacts/README.md`, `cap_artifacts.conventions` | slice 1 (convention); buckets created in slice 2 |
| checksum/content-identity verification | `cap_artifacts.integrity`, `ArtifactReference.verify_bytes` | slice 1 (helpers); on store read/write in slice 2 |
| scoped artifact access API | — | slice 4 |

## Slices

| Slice | Content |
|---|---|
| 1 | contract and example, conventions, checksum helpers, unit tests TEST-OBJ-001-001 (FIXTURE_ALLOWED, t1-unit), CI step, CODEOWNERS |

## What this evidence does not claim yet

No bytes are stored in SeaweedFS by this slice; the REAL store tests arrive in
slice 2. NFR-DATA-001's 100% measurement is an EVALUATION gate; FR-VIS-001 is
accepted on the integrated Vision path (E2E-01, AV-SCEN-01). DEP-009 (shared
Integration host) is assessed at its gate. The SHA-256 choice awaits its
confirming ADR (see `packages/artifacts/README.md`).
