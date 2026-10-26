# CHG-046 evidence applicability

This record declares the evidence applicability for the independent `WP-CORE-009`
producer slice. It is a planning/change-control record, not `COMPONENT_READY`
evidence and not a WP completion claim.

Required future producer evidence:

- `evidence/WP-CORE-009/COMPONENT-READY.md`, attributable to the exact current-main
  revision and bound to `DN-CORE-LIFECYCLE`;
- current-main CI evidence for `TEST-CORE-LIFECYCLE` with the lifecycle component
  suite green;
- an exact consumer binding from that artifact to `WP-CORE-002` / `DEP-020`.

Legal transition semantics, hold/release handlers, rework and split/merge remain
outside this slice and belong to their existing producer packages.

Current status: `NOT_YET_EXECUTED`; no readiness artifact or test result is
claimed by CHG-046. The existing merged-binding provenance pins were refreshed
to the current canonical WBS revision; their scope digests and binding meaning
are unchanged.

The controlling requirement is `DEP-020`: before the WP-CORE-002 transition
engine starts, the minimal lifecycle component must be implemented, its
component tests must be green on current main, and an attributable
`COMPONENT_READY` artifact bound to `DN-CORE-LIFECYCLE` and WP-CORE-002 must
exist. This record does not satisfy that requirement.
