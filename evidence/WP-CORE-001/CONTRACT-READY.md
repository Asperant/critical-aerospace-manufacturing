# DN-CORE-CONTRACTS — CONTRACT_READY binding for DEP-018

This is an attributable contract-readiness assessment for the existing merged
WP-CORE-001 producer slice. It does not add domain implementation, certify
integrated acceptance, or claim real-factory data.

The bound surface is the Core order-domain query contract and its nested
ProductionOrder, Lot, SerializedComponent, ManufacturingRoute and RouteVisit
models. The contract preserves opaque immutable identity/revision fields,
cross-entity references, route traversal order, and distinct visit identities
when an operation class is revisited. The normal and reentrant fixtures are
published under `services/manufacturing-core/contracts/v1/`.

`evidence/readiness/DN-CORE-CONTRACTS.json` binds this assessment to the
merged CORE-001 PR, its current-main ancestor, exact artifact/test/trace blobs,
and DEP-018's precise requirement. Lifecycle state representation is a
consumer-side WP-CORE-009 concern; legal transition semantics remain in
WP-CORE-002.
