# Requirement catalog — WP-GOV-001

`catalog.json` is a generated index of the 186 FRs and 120 NFRs in approved
01 Items 81/82. Requirement wording and meaning remain in 01. Entries contain
stable IDs, one canonical PrimaryOwner, classification and source anchors with
SHA-256 digests; no SHALL text is copied. `catalog.schema.json` is JSON Schema
2020-12 generated from the same typed models used by the linter.

FR `scope_class` is F0/F1/R1 (product identity/product depth/research evidence).
NFR `quality_class` is H0/A1/S2/C3; its `scope_class` is null because Item 82
does not assign that separate classification. Every entry has explicit
`revision` and `status` fields, currently null: 01 lacks per-record values.
The document's Approved heading is not an individual requirement lifecycle.
GAP-RTM-004/005 remain open for the designated owners; this WP does not invent
their metadata or alter canonical semantics. Lint PASS means structural/source
conformity, never READY, VERIFIED, measurement acceptance or WP completion.

## Inspect and regenerate

From the repository root, with the existing environment and projectctl installed:

```sh
projectctl catalog-lint
projectctl catalog-lint --base main --json
projectctl catalog-export --artifact catalog
projectctl catalog-export --artifact schema
projectctl catalog-export --artifact counts
projectctl catalog-export --artifact rtm-counts
python -B -m pytest tools/projectctl/tests/test_requirement_catalog.py -q
```

All commands emit to stdout; none writes files, uses a network client or mutates
Plane. To update checked-in artifacts, capture each export to a temporary file,
review it, then replace the corresponding artifact. Never redirect catalog
export onto its own input: it reads existing retirement history. Replace only
the marked generated-counts block in 03 with `rtm-counts` output. Re-run lint
and the tests. `coverage_counts.json` includes domain and owner counts for
downstream regeneration; these are inventory counts, not verified coverage.

Exit codes: 0 = conforming; 1 = lint violations; 2 = missing/malformed input or
invalid Git baseline. Errors identify the failing source/schema/history surface.
Missing files, duplicate JSON keys/IDs, unknown or multiple owners, wrong
classes, altered source anchors, fabricated lifecycle values and stale generated
files fail closed. JSON Schema checks structure; the linter additionally checks
cross-field rules, canonical equality, uniqueness and history.

## Permanent identities and CI

`retired_ids` is the append-only retirement ledger within the catalog. It starts
empty because this baseline records no retired/superseded requirements; no claim
about pre-catalog history is made. A future approved retirement adds the ID,
RETIRED/SUPERSEDED status and an existing `09_change/CHG-NNN.yaml` reference.
Review must verify that decision's approval; file existence is not approval.
Regeneration preserves this ledger. Historical IDs may leave the current index
only with tombstones. Tombstones cannot disappear/change, and terminal IDs may
never become live again. Lint without `--base` explicitly reports that historical
checks were not run.

The existing `projectctl / projectctl` CI job runs catalog lint with the PR base
or push-before SHA, using a complete Git checkout. A new branch falls back to
its merge base with main. An invalid baseline fails; the first catalog
introduction reports that the baseline has no catalog. The existing required
check includes this step: a lint failure fails that job. Branch-protection
enforcement remains the limitation documented in
`project_control/ENGINEERING_WORKFLOW.md`; this change does not claim remote
settings or CI executions that have not occurred.

Concrete assets in `tools/projectctl/tests/test_requirement_catalog.py`:

| Asset | Planned family | Scope |
|---|---|---|
| TEST-GOV-001 (`test_gov_001_*`) | TEST-GOV-CATALOG | Actual catalog/schema/CI entry points, generated counts and rejection cases |
| TEST-GOV-002 (`test_gov_002_*`) | TEST-GOV-TRACELINT | ID history/non-reuse slice only; general trace-edge tooling remains WP-GOV-002 |
| TEST-GOV-003 (`test_gov_003_*`) | INSP-GOV-NFR | NFR class inspection only; measurement completeness remains with its assigned WPs |

This is offline repository tooling, not a runtime service. DOD-WP-06 runtime
health/telemetry does not apply. This runbook supplies the relevant DOD-WP-07
operator instructions. Required CI, supporting review by Yavuz, merge and
post-merge validation must still precede completion. Revert a rejected change
through normal reviewed Git changes; never erase retirement history to obtain
a green check.
