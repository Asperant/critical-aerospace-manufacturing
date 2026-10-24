# WP-EVT-001 CI compatibility gate slice — CHG-032

Date: 2026-10-25 (Europe/Istanbul).
Base: 3c26df0e2286397f2448c1deccc7922727b05029.
Branch: wp/WP-EVT-001-event-contracts.
Live queue returned OK, current WP-EVT-001 IN_PROGRESS, blocked false.
Read the WP context, existing contract-slice evidence, architecture compatibility
policy, docs/09 change control and host policy source-pin handling before coding.

Implemented package-local cap_contracts.ci_gate, an adapter over Registry.verify,
load_schema, compare_contracts and enforce_version_policy. The only workflow edit
is six additive lines in t1-contract: full-history checkout and one gate step with
package PYTHONPATH and event-bound baseline SHA. Other jobs, generic schema tests,
required checks and permissions are unchanged. schema-refs.json is an empty array
of explicit FileRef approvals until a package schema needs a file dependency.

Both committed snapshots are registry/schema/fixture validated. Only declarations,
approvals and pinned files are materialized from Git blobs; worktree files cannot
satisfy a missing tracked input. Missing history, invalid declarations, drift,
invalid/unapproved/cyclic/remote references, unknown comparisons and invalid version
transitions fail closed. Symlinks/submodules are rejected without following them.
No compatibility algorithm is duplicated in the adapter. Failures are deterministic
JSON codes/stages/contract IDs, never payload values or exception details.

Scoping: unchanged verified declarations/resolved documents receive an unchanged
count, without a new compatibility claim. Added majors compare against the highest
baseline major of the same family. A first family has no previous contract and
receives boundary validation and an explicit added count; prior-version compatibility
is inapplicable, not asserted. Removed declarations fail closed. Unsupported changed
schemas remain unverifiable; existing detector limitations are not weakened.

Executed checks (pinned `uv run --project ci --locked` toolchain):

- `pytest -c ci/pyproject.toml ci/tests/test_contract_ci_gate.py -q`:
  29 passed in 0.86s, TEST-EVT-001-006. Includes synthetic Git histories, real adapter
  invocation, JSON redaction/determinism, baseline selection, scoped unchanged/new
  contracts, major rules, authority, references, drift, fixtures and bad inputs.
- `ruff check`, `ruff format --check` and `pyright` on ci_gate.py and
  test_contract_ci_gate.py: pass; 2 files formatted, 0 type errors/warnings/informations.
- Local package entrypoint smoke with --base 3c26df0e2286397f2448c1deccc7922727b05029:
  PASS, validated=1, unchanged=1, compared=0, added=0, failures=[]. This validates
  the existing committed Core exemplar; it makes no unsupported compatibility claim.
- `projectctl validate`: exit 0, validation PASS, 179 WPs, 306 requirements,
  217 dependency edges, zero hard cycles. Existing canonical metadata/need-by
  warnings remain visible; this is not a DoR/dependency-readiness certification.
- YAML/CSV CHG-032 consistency and manual parsed workflow comparison excluding only
  the contract job: PASS. The other workflow content is identical to the base.
- `git diff --check`: PASS.

Initial focused run: 24 adapter tests passed; one workflow test failed because a
historical Git helper stripped a final YAML block-scalar newline. The final focused
workflow check verifies current gate routing to exactly the contract job rather
than imposing a permanent historical baseline on unrelated jobs. The complete
unchanged-other-jobs comparison was separately executed with raw Git YAML and passed.
No existing test was changed. Additional baseline, pin-drift and invalid-JSON cases pass.

Pinned-source change control: CHG-032 (C1 / CR-2, APPROVED_WITH_CONDITIONS), recorded
in 09_change/CHG-032.yaml and the canonical change registry. Advisory reviewer routing
is documented, no review or human approval is claimed. New workflow SHA-256:
cdcbcc24a038d54270e74e854e82e3af2a5cbf52eaa07ce9df62bcf293719835.
After eventual merge, the deployed policy source pins require the existing supported
merged-source builder/installer refresh, with backup/rollback and any applicable
attributable wait re-assertion. No installed policy, other profile, Plane field or
lifecycle was touched here; no unmerged policy was deployed.

Not executed/claimed: broad/full suites, full remote CI success, integrated consumer
acceptance, dependency readiness, merged rollout, final WP PR or WP DONE.
Next smallest slice: canonical producer-authority registry validation before ACL work.
