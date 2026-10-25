# WP-SIM-001 historical evidence identity addendum

Prepared 2026-10-25 from existing historical records only. This adds provenance; it does not alter earlier claims, reconstruct missing identities, create a new run or certify DOD-WP-11 PASS. No tests were rerun for this addendum.

## Historical local run

- Real run reference: `evidence/WP-SIM-001/runs/run-5-post-review/`. There is no run-specific run-manifest.json there: the binding manifest is `evidence/WP-SIM-001/run-manifest.json`.
- Recorded command window: 2026-10-24T12:23:19+00:00 through 2026-10-24T12:27:53+00:00. Manifest created: 2026-10-24T12:28:30+00:00.
- Source branch: `wp/WP-SIM-001-deterministic-des-kernel`; base commit `ff56cfeb3142a41e0eb77b0649e6d8ab0fb7c506`. Historical manifest explicitly says committed=false. No exact tested commit is asserted.
- Source-map digest (as recorded): `8955880d41fefe8eb4b1dd1ed3cbf37a543e8792ecec155840d02c70ebff3609`; tracked-diff digest: `442ee0c3783d99436eec68934fd5e025d660e5a0d5eac1d2ef56b149482100b1`. The original manifest retains all 24 per-file SHA-256 bindings. These are not a Release ID.
- JUnit host name: `ailab`; timestamp `2026-10-24T15:23:20.238812+03:00`; 202 tests, 0 failures, 0 errors, 0 skipped. These are historical recorded results, not newly executed tests.
- Recorded environment: Python 3.11.16; platform `Linux-7.0.0-38-generic-x86_64-with-glibc2.43`; uv project environment kept outside the repository via UV_PROJECT_ENVIRONMENT (CI uses ci/.venv); ci/uv.lock used with --locked.
- Recorded packages: numpy=2.4.6, hypothesis=6.168.1, pytest=8.3.3, ruff=0.7.4, pyright=1.1.389, manufacturing-simulator=0.1.0. uv: 0.12.13 (pinned as UV_VERSION in .github/workflows/ci.yml).
- Workload: single local session on the shared development host; no containers or shared services started; commands run sequentially. Scenario: toy-kernel v1 (opaque counters; not the canonical ScenarioDefinition); master seed 20261024; config SHA-256 `b059aba725ace525a02475254beec0393fdb54f064efdb3f386d63c1e8cba655`. Replay seeds and fixed stream mapping remain in the manifest.

## Unavailable historical identities

- Release identity/versioned Release record: UNAVAILABLE in inspected run records. The scenario simulator_version `kernel-test-0` and package version 0.1.0 are recorded labels, not proof of a governed Release identity.
- Exact committed SHA under test: UNAVAILABLE; source was uncommitted and bound by hashes/base/diff.
- Detailed historical hardware identity (CPU model/count, RAM, GPU, machine/VM identity or governed Hardware ID): UNAVAILABLE. Hostname ailab and x86_64 platform do not establish those details.
- Governed Environment ID and immutable environment/image digest: UNAVAILABLE; versions and lock usage are recorded, not an invented environment record.
- No current machine inspection was used to fill historical gaps. Any new measurement must be a separately identified run, not a retrofit of this one.

## Separate post-merge GitHub runs

PR52 merge revision: `471a9b19dbd1319727443cee4f50215a371af716`.
- CI run [40099331443](https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/40099331443): push, completed/success; started 2026-10-24T13:42:56Z, last updated 2026-10-24T13:46:47Z.
- projectctl run [40099331483](https://github.com/Asperant/critical-aerospace-manufacturing/actions/runs/40099331483): push, completed/success; started 2026-10-24T13:42:56Z, last updated 2026-10-24T13:46:57Z.
These timestamps/statuses were re-read from the GitHub API for this addendum. updated_at is not asserted to be exact test completion time. These later runs do not supply the earlier local run's missing identities or integrated acceptance.

## Historical artifact byte bindings

- `run-manifest.json`: SHA-256 `56793002a9e76d2682f1f46eb062124d30b1e70d83b6114b0825024a8622ba7a`.
- `runs/run-5-post-review/results.json`: SHA-256 `acd5c4aaa281820c896d724f877fb59f10a9e76d27d846b7d274d11d437d00d2`.
- `test-results.xml`: SHA-256 `95153e9d1b2fc842726275e8ed36eaf9f8dd763f75350b42c816958693afb3fd`.
- `replay-comparison.json`: SHA-256 `3ca5175e82c393503017d1a0f237c4a38e6d3297fb8e3b329e68a70e8087950d`.

Disposition: addendum finalized as a factual provenance record; DOD-WP-11 remains UNKNOWN/incomplete for unavailable required identities pending accountable disposition or separately identified evidence. No DoD waiver, acceptance or deferred status claimed.

## Update 2026-10-25: new run and producer allocation

`runs/run-7-identity-2026-10-25/` is NEW local evidence from a clean committed source (commit, lock, CPU, memory, package and seed identity, 202 tests, replay equal across seeds). It does not fill the historical gaps above and is not a governed Release, Environment or Hardware identity, so DOD-WP-11 stays incomplete. The canonical producer of EnvironmentManifest, ReleaseManifest and HardwareProfile records is WP-PLAT-005 (docs/06D, readiness DN-ART-RELEASE, owner Yavuz, NOT_STARTED); no SIM-001-local action can create them. Whether to classify this as waiting for that named producer is the accountable owner's decision, recorded in the owner assessment, not an agent waiver.
