# WP-EVT-002 — external binding provenance reconciliation

Assessed canonical main: `d45173359f01c7471339eb63c2c8b4e4cb8e8760`.
Consumer: WP-EVT-002 / Asrın Dündar; the consumer scope and canonical source SHA256 values are recorded in EXTERNAL-BINDING-PROVENANCE.json.

This is partial evidence, not an accepted binding registry or readiness assertion. No new runtime path or producer assignment is invented.

| Transport | Verified producer | Unknown required evidence |
|---|---|---|
| HTTP | Exact backend producer UNKNOWN; WP-UI-001 owns the BFF shell/contract only | Backend producer assignment, bound transport contract and concrete adapter path |
| NATS | WP-CORE-005 / Asrın owns domain events/outbox; EVT-003 supplies generic consumer hooks | Concrete publisher path plus actual application consumer WP/path and subject/stream/durable binding |
| Temporal | WP-AUTO-001 / Batuhan owns WorkflowBundles and typed activities | Concrete workflow/activity/context-hook output path and bound interface |

WP-CORE-005 and WP-AUTO-001 both retain `Repository reference: TBD_BY_IMPLEMENTATION` in their canonical WBS cards. `operations_bff/overview.py` explicitly says backend Query APIs are not canonically bound; the Core README supplies no HTTP endpoint. The consumer framework README explicitly supplies no production stream/subject binding or downstream-adoption claim. Existing source files demonstrate the gaps; they cannot be inserted as missing binding paths because those files already exist.

Therefore no complete entry can truthfully be admitted to `project_control/merged_external_bindings.yaml`: its required `binding_paths` cannot be sourced, and HTTP/the NATS application consumer assignments remain UNKNOWN. Invalid UNKNOWN entries would fail the production policy builder; partial observations are kept here instead.

All canonical ownership and scope digests were read from the installed current-main policy and checked against this checkout. Precise requirements are scoped descriptions derived from the EVT-002, CORE-005 and AUTO-001 canonical cards, not new accepted transport schemas. No HARD START edge or global readiness is introduced.

A fresh GitHub assessment may correct current-main binding and field names and repeat the audited external dependency exactly. It must retain `External bindings: UNKNOWN` until real registry entries exist. Posting an assessment does not link it to the active blocker audit. No supported BLOCKED/UNCHANGED re-assertion is authorized in this task, so historical audit linkage and lifecycle are left unchanged.

Validation: JSON parsing, canonical file SHA256 comparisons and installed scope-projection recomputation; production empty registry validation. Provenance completeness remains FAIL. No product tests or lifecycle writers are run.

## Fresh attributable assessment and read-only outcome

New unedited owner assessment: https://github.com/Asperant/critical-aerospace-manufacturing/pull/76#issuecomment-6401360609

It names current canonical main, Implementation PR 76, the correct external wait
class and local actionable work NONE. The structured blocker matches the VERIFIED
audit exactly, including the stored external-dependency truncation.
`External bindings: UNKNOWN` remains truthful. Field reconciliation passes except
for unresolved binding IDs; complete assessment/provenance and slot eligibility
remain FAIL. The installed registry remains empty.

The fresh comment is not linked to the active historical audit: no lifecycle or
BLOCKED/UNCHANGED writer was invoked. The installed proof still consumes that
active audit's existing evidence. Fresh comment formatting alone cannot release
a slot. Final read-only state: VALIDATING + BLOCKED, slot retained.
