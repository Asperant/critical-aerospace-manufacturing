# CTRL-HOST-016 / CHG-035 — canonical future binding obligations

Baseline main: d45173359f01c7471339eb63c2c8b4e4cb8e8760.
Authorized scope: explicit project-owner request to resolve missing canonical
ownership/dependency precision without changing slot policy or lifecycle.

This C3 / CR-3 source change defines previously missing subdeliverables. It does
not assert that these concrete paths existed in earlier specifications or that
any runtime interface, protocol version, service or artifact is implemented.

| Chain | Runtime roles and responsible WPs | Waiting shared-context consumer |
|---|---|---|
| HTTP | WP-CORE-001/asrin supplies Core query HTTP context ingress; WP-UI-001/asrin supplies the BFF backend client | WP-EVT-002/asrin |
| NATS | WP-CORE-005/asrin supplies the publisher; WP-TWIN-001/asrin supplies the first explicit application projection consumer | WP-EVT-002/asrin |
| Temporal | WP-AUTO-001/batuhan supplies workflow context and activity-side restoration | WP-EVT-002/asrin |

The five registry mappings name six concrete future paths, all verified absent.
Exact runtime operation/version/subject/stream/durable/workflow/worker choices
remain future producer/consumer contract obligations; this change invents none
as implemented or accepted. Broker/server runtime ownership stays Yavuz; generic
EVT-003 hooks are not application adoption. Core, Twin and HITL authority boundaries
are preserved. CHG-035 records the common protocol obligations and non-readiness
consumer-specific dependency allocations at INTEGRATION, without adding HARD
START edges or changing existing graph predicates.

Only producing WBS cards, the change record/registry and this evidence change.
EVT-002's own WBS/RTM scope projection remains
052d908bb24769d74259a455d99c53567dfaa8faafcb8977bf780d154973d499.
General architecture, dependency graph, DoR/DoD/governance and all slot-policy code
are untouched. The producer scope digests and canonical WBS SHA256 are recomputed
and validated by the unchanged CHG-034 registry validator.

## Actually executed checks

- Canonical project validation: PASS.
- Catalog lint against origin/main: PASS.
- CHG-034 registry validation: PASS, five mappings with canonical owners, precise
  requirements, producer/consumer scope digests and pinned canonical provenance.
- All six future artifact paths absent and explicitly present in producing WBS
  deliverables: PASS.
- Actual canonical policy builder, sandbox output only: PASS; no installed file
  or staged production policy was written.
- Consumer scope and non-projected canonical inputs preserved relative to baseline
  main: PASS; no new scope drift introduced by this allocation.
- Whitespace/source review: PASS. No product code, tests or runtime paths created;
  no product/broad test suite was run for this metadata-only allocation.

## Live eligibility remains FAIL

A read-only installed proof check still has zero registered live mappings and
returns no slot proof. Local records have not merged or deployed, and the old
active blocker assessment/audit linkage remains unchanged. No assessment comment,
lifecycle transition, blocker re-assertion or queue mutation is performed.

An independent original-merge scope check against the already installed CHG-034
policy also returns DEFERRED_CANONICAL_SCOPE_CHANGED: docs/09 changed between the
EVT-002 merge 9db6a1080b8604a36a4629d85c8f844b57879cd6 and baseline main. This is
pre-existing governance-source drift; this allocation does not edit docs/09 or
weaken the slot proof to hide it. After source review/merge, deployment and fresh
accountable evidence, that distinct proof condition still needs supported handling.
No slot release, readiness, DONE or acceptance is claimed by this record.
