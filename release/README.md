# Release pipeline (WP-CICD-002)

How a main-derived, immutable artifact reaches the Integration host without a manual
source patch (FR-PLAT-004, FR-PLAT-005, NFR-DEP-003; 02, CD and Release Manifest).

```
protected main -> release workflow (build once, digest, SBOM, provenance, attestation)
               -> ReleaseManifest -> cap_release deploy (preflight, migrate, rollout, health,
                                     smoke) -> DeploymentRecord
```

## Parts

| Part | Where | Role |
|---|---|---|
| Image registry | `release/images.json` | the deployable images the pipeline builds; a Dockerfile it does not list fails `registry-check` |
| Build and publish | `.github/workflows/release.yml` | builds each image once on the main revision, publishes to GHCR by digest, attaches SBOM and provenance attestations, signs the provenance, builds the ReleaseManifest. Pull requests that touch release paths only dry-run the build |
| ReleaseManifest | `tools/release/.../schemas/release-manifest.schema.json` (`cap.release-manifest/v1`) | 02's thirteen identities; images pinned by digest, a tag is never an identity; no secret plaintext |
| DeploymentRecord | `.../deployment-record.schema.json` (`cap.deployment-record/v1`) | what one deployment did; `SUCCEEDED` only when every stage passed |
| Deploy | `python -m cap_release deploy` | runs on the target host; pulls digests, never builds |
| Host hook | `infra/compose/stack.sh` (`CAP_COMPOSE_OVERRIDE`) | applies the digest-pinned override; no build runs when it is set |

## Deploying a release

On the Integration host, in a clean checkout of the release commit:

```bash
gh run download <release run id> -n release-manifest-<commit> -D /tmp/rel
PYTHONPATH=tools/release/src python -m cap_release deploy --manifest /tmp/rel/release-manifest.json
```

`deploy` refuses, and records the refusal, unless all of these hold:

- the manifest is valid (digest-pinned references, no secret plaintext, 02's identities present);
- the host checkout equals the release commit and its source tree has **zero** changes (NFR-DEP-003);
- the release commit is on `main` and `ci-gate` is `success` at it (checked through the GitHub API);
- every image digest exists in the registry (CD does not trust tags).

Then it runs, in order: migrate (skipped while the release binds no schema target),
rollout (a generated Compose override with `image: <repo>@<digest>` and `build` removed),
health (every service of the platform project healthy) and smoke (the REAL checks of
`stack.sh smoke`). A failed rollout, health or smoke stage rolls back to the last
SUCCEEDED release when there is one. Records and manifests are kept in
`${CAP_RELEASE_STATE_DIR:-~/.local/state/cap-release}` (`records/`, `releases/`). Exit
status 0 only for `SUCCEEDED`.

## Operating notes

- The preflight asks GitHub for `ci-gate` through `gh`, which needs a writable cache directory.
  If `/tmp/gh-cli-cache` belongs to another user, run with `TMPDIR=$HOME/.cache/tmp`. An unreadable
  check is recorded as `ci-gate could not be read ... <reason>` and nothing is deployed; an absent
  check is recorded as `missing`.

## Decisions taken here

- **OD-CICD-01 (02): serialization of ReleaseManifest and DeploymentRecord.** Both are
  JSON documents validated by a JSON Schema shipped with the tool; a manifest is
  fingerprinted by the SHA-256 of its canonical (sorted-key, compact) JSON and a record
  names that fingerprint. 02 leaves JSON schema, a database table or another form to the
  implementation. This is recorded here until an ADR can be admitted to the ADR index
  (WP-DOC-002); an ADR for OD-CICD-01 is a follow-up.
- **Identities without a producer are explicit.** Model, workflow, prompt/tool/routing,
  knowledge-index and configuration-schema versions, and the database schema target
  (until `manufacturing-core` is a release image), are `NOT_YET_PRODUCED` with a reason, never
  null and never invented.
- **The tag is a name.** Images are also tagged `sha-<commit>` for people; deployment uses
  the digest only.

## Not here

- Application deployable images: none has a Dockerfile yet; each joins `images.json` with its
  own work package.
- Database migration execution in the deploy path: WP-CICD-003.
- Deployment from GitHub Actions: it needs a self-hosted runner on the Integration host
  (DN-PLAT-RUNNER); until then `deploy` runs as a command on the host.
- Integrated acceptance (TEST-PLAT-CD, INSP-DEP-HOST) and NFR-DEP-003's measurement over
  formal deployments.
