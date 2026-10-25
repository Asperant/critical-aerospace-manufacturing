# cap-artifacts — ArtifactReference contract and storage conventions (WP-OBJ-001)

Every large artifact (inspection images, masks, model weights, simulation
snapshots, evidence bundles) is addressed by an immutable **ArtifactReference**;
its bytes live in SeaweedFS through the S3 API. Events and APIs carry the
reference, never the bytes, a bucket/key as identity, or a signed URL
(02 Large Artifact Policy, "Object ≠ Artifact", ARCH-INV-028; ADR-0005).

Requirements: FR-VIS-001 (artifact half of the Vision inference path),
NFR-DATA-001 (verified checksum/content identity for critical immutable artifacts).

## Contract

| Contract | Schema | Example |
|---|---|---|
| `cap.artifact-ref/v1` — ArtifactReference (IC-SHARED-001) | `src/cap_artifacts/schemas/artifact-reference.schema.json` | `artifact-reference.json` |

The schema and its example are validated by the CI contract tier
(`ci/scripts/check_contracts.py`). `cap_artifacts.validate()` applies the same
structural rules plus the ones a schema cannot express (below); the unit tests
check every structural negative case against both, so they cannot drift.

Fields follow the 02 minimum metadata: `artifact_id` and `version`,
`artifact_type` (domain kind, e.g. `inspection_image`) and `artifact_class`
(02 classes), `format_version`, `content_type`, `size_bytes`, `checksum`,
`logical_owner`, `producer`, `created_at`, world/run/branch `context`,
`classification`, `retention_class`, `storage`, `lifecycle_status`, `provenance`.

## Storage conventions

| Rule | Value |
|---|---|
| Bucket by recovery class | RC-B → `cap-artifacts-rc-b` (critical, backup mandatory) · RC-C → `cap-artifacts-rc-c` (rebuildable) · RC-D → `cap-artifacts-rc-d` (ephemeral). RC-A is canonical mutable state, never an artifact. |
| Object key | `v1/<artifact_type>/<first two hex of artifact_id>/<artifact_id>/<object_id>` — identities only, never a lot, component or other business identity |
| One upload, one object | every upload gets a new `object_id`; a finalized object is never overwritten |
| Class/retention | `TEMPORARY_STAGING` is always RC-D; `VERSIONED_RELEASE` is always RC-B |
| Lifecycle | `RESERVED → UPLOADING → VALIDATING → AVAILABLE`, failures `FAILED`, `QUARANTINED`, `ABORTED`; disposal `RETIRED/DELETE_ELIGIBLE → PENDING_DELETE → DELETED`. Consumers use only `AVAILABLE`. |

## Content identity

SHA-256 over the exact bytes, with the byte count. `verify_bytes()` fails closed:
a size or digest mismatch raises `IntegrityError` and the bytes are not handed out.
The algorithm is named in every reference (`checksum.algorithm`), so a later
change is an additive schema version.

> **Open item.** 02 and ADR-0005 leave the hash algorithm to be confirmed by an
> ADR at implementation time. SHA-256 is the natural default named there; the
> confirming ADR is proposed within this work package and coordinated with the
> ADR index owner (WP-DOC-002) before the package closes.

## Slices

| Slice | Content | State |
|---|---|---|
| 1 | contract, conventions, checksum helpers, unit tests (TEST-OBJ-001-001) | this change |
| 2 | S3 store client: put/get/head with verification and no-overwrite, REAL SeaweedFS tests | next |
| 3 | relational metadata and cross-store consistency | planned |
| 4 | scoped short-lived access and least-privilege storage identities | planned |
| 5 | trace, evidence, Integration host smoke (DEP-009) | planned |
