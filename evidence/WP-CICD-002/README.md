# WP-CICD-002 — CD to INTEGRATION with immutable artifacts: evidence

Owner: Yavuz Gümüş · supporting reviewer: Asrın (advisory, CHG-018) · F0 · M1 ·
readiness node DN-PLAT-CD · requirements FR-PLAT-004, FR-PLAT-005, NFR-DEP-003.

DEP-002 (the START edge) was clarified and recorded READY by CHG-076
([DEP-002 readiness](DEP-002-START-READINESS.md)).

## Slices

| Slice | Content |
|---|---|
| 1 | `release/images.json` (the image registry) and the registry check; `cap.release-manifest/v1` and `cap.deployment-record/v1`; the manifest builder and validator; the digest-pinned deploy decisions with their record and rollback |
| 2 | `.github/workflows/release.yml` (build once on main, GHCR, SBOM, provenance, attestation, ReleaseManifest), the `CAP_COMPOSE_OVERRIDE` hook of `stack.sh`, CI wiring |
| 3 | `release/README.md` (operator guide and the OD-CICD-01 decision) and `collect_run.py` |
| 4 | the shared-host run (RUN-CICD-002-DEV-001), recorded after the first publish from main |

## Verification

| Asset | Family | Boundary mode | Where it runs |
|---|---|---|---|
| `tools/release/tests/` (TEST-CICD-002-001…004, 98 tests) | TEST-PLAT-CD | FIXTURE_ALLOWED (a fake host); the Compose override test calls the real `docker compose config` | CI t1-unit |
| the `release` workflow dry-run build | TEST-PLAT-CD | REAL image build, nothing pushed | CI, pull requests |
| RUN-CICD-002-DEV-001 | TEST-PLAT-CD, INSP-DEP-HOST instrumentation | REAL | shared host (DEV), after the first publish |

Local at the branch head: 98 release tests passed, `ruff` and strict `pyright` clean on
the package, the static ratchet, `check_test_strategy.py`, `projectctl validate` and the
trace lint pass. On the pull request the `release` workflow's plan and dry-run build
(`release-build (mlflow)`, SBOM and provenance on, nothing pushed) passed.

## What the deploy command decides

`python -m cap_release deploy` writes a DeploymentRecord for every outcome:

| Situation | Result | Rolled out |
|---|---|---|
| host source tree has any change, or the checkout is not the release commit | FAILED at preflight | nothing |
| release commit not on main, `ci-gate` not success or absent | FAILED at preflight | nothing |
| an image digest is not in the registry, or a reference is a tag | FAILED at preflight | nothing |
| migration fails (a release that binds a schema target) | FAILED at migrate | nothing |
| rollout, health or smoke fails | FAILED, or ROLLED_BACK to the last SUCCEEDED release | the previous release again |
| every stage passes | SUCCEEDED | the digests of the manifest |

The record validator rejects a SUCCEEDED record that has a stage that did not pass, a
host with manual patches or a checkout that differs from the release commit, a release
that is not main-derived, a red `ci-gate` or digests absent from the registry.

## Findings

- **A test found a crash before commit.** A registry file whose top level is a JSON list
  raised `AttributeError` instead of failing closed; it now raises the registry error.
- **A design error caught before it mattered.** Binding the database schema target to the
  repository's migrations would have made `SUCCEEDED` impossible (the migrate stage must
  pass when a target is bound and migration execution is WP-CICD-003). The target is now bound
  only when its owner image is a release image; until then it is `NOT_YET_PRODUCED`.
- **A CI step overrode the job `PYTHONPATH`** (`pytest_quarantine` not importable); fixed and
  the exact CI command reproduced locally.
- **The DEP-002 gate was circular** (its evidence was this package's own deliverable); see
  CHG-076.

## Known limitations

- No application deployable has a Dockerfile, so the only released image is the MLflow image
  built from `infra/compose/mlflow`.
- Deployment from GitHub Actions needs a self-hosted runner on the Integration host
  (DN-PLAT-RUNNER); until then `deploy` is a command on the host.
- Model, workflow, prompt/tool/routing, knowledge-index and configuration-schema versions and
  the database schema target are `NOT_YET_PRODUCED` in the ReleaseManifest; migration execution
  is WP-CICD-003.
- The live rollback needs two published releases; it is covered by the fake-host tests only.
- OD-CICD-01 is decided in `release/README.md`; an ADR follows when the ADR index can admit it
  (WP-DOC-002).
- WP-CICD-002 is F0: DONE needs the integrated acceptance (TEST-PLAT-CD at INTEGRATION,
  INSP-DEP-HOST at EVALUATION) and the NFR-DEP-003 measurement over formal deployments.
  EvidenceState is EVIDENCE_PENDING and `observed` stays null.
