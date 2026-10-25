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
| Object key | `v1/<artifact_type>/<first two hex of artifact_id>/<artifact_id>/v<version>/<object_id>` — identities only, never a lot, component or other business identity |
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

## Store (slice 2)

```python
from cap_artifacts import ArtifactStore, S3Client, StoreConfig

store = ArtifactStore(S3Client(StoreConfig.from_env()))  # CAP_S3_ENDPOINT from stack.sh env
store.ensure_buckets()
ref = store.store(png_bytes, artifact_type="inspection_image", artifact_class="OPERATIONAL_EVIDENCE",
                  retention_class="RC-B", content_type="image/png", format_version="png/1",
                  logical_owner="vision-service", producer={"service": "manufacturing-simulator",
                  "version": "0.1.0"}, classification="INTERNAL")
data = store.read(ref)  # only AVAILABLE references, only verified bytes
```

| Behaviour | How |
|---|---|
| Finalization protocol | RESERVED → UPLOADING (PUT to a fresh object) → VALIDATING (read back, verify size and SHA-256) → AVAILABLE; a mismatch deletes the object and raises |
| Write once | a version whose prefix already holds an object is refused (`OverwriteError`); new bytes need a new version |
| Read | `require_consumable()` then GET then verify; tampered bytes raise `IntegrityError`, missing bytes `MissingObjectError` — never silent |
| Object metadata | `x-amz-meta-cap-sha256` carries the digest, so bytes can be checked without the reference (orphan sweep, slice 3) |
| Signing | AWS Signature V4 (`sigv4.py`), checked against the three published AWS S3 examples |

Without a registry the version-prefix check and the upload are not one atomic
step; with the registry (slice 3, below) the version is reserved first. Uploads are
single-request; multipart upload for large datasets and snapshots comes with
the access path. The local `infra` profile runs the S3 gateway without
identities; storage identities and least privilege are slice 4.

## Registry (slice 3)

`cap_artifacts.registry` keeps one row per artifact version in PostgreSQL
(`migrations/0001_registry.sql`, schema `artifact`), the metadata half of
"Object ≠ Artifact". Pass it to the store: `ArtifactStore(client, registry=Registry.connect(dsn))`.

| Rule | Where it is enforced |
|---|---|
| A version is written once, even when writers race | primary key `(artifact_id, version)`; the losing writer gets `DuplicateVersionError` before any upload |
| Identity and content never change | trigger: artifact, storage and checksum columns and the reference (except its status) are immutable |
| Only 02 lifecycle transitions | trigger against `artifact.lifecycle_transition`; the store also updates compare-and-set on the old status |
| The registry decides what can be read | `read()` takes the status from the registry, so a QUARANTINED version is refused even if the caller holds an AVAILABLE copy |
| No deletes by the runtime | runtime role gets SELECT/INSERT/UPDATE only; DELETED is a tombstone status |
| Migration | Core pattern: separate migration owner and runtime role, advisory lock, checksummed ledger, verified replay (`migrate(dsn, runtime_role)`) |

`check_consistency(registry, client.iter_keys)` is a read-only sweep (02
"bidirectional integrity checks"): versions that should have bytes but do not,
objects in the artifact buckets that no version claims, and reservations stuck
in flight for more than an hour. It reports; it never deletes.

## Slices

| Slice | Content | State |
|---|---|---|
| 1 | contract, conventions, checksum helpers, unit tests (TEST-OBJ-001-001) | done |
| 2 | signed S3 store client: write once, verify on write and read, REAL SeaweedFS tests (TEST-OBJ-001-002/003) | done |
| 3 | PostgreSQL registry: atomic write-once, lifecycle in the database, consistency sweep (TEST-OBJ-001-004/005) | this change |
| 4 | scoped short-lived access and least-privilege storage identities | planned |
| 5 | trace, evidence, Integration host smoke (DEP-009) | planned |
