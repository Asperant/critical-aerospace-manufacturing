# CTRL-HOST-013 / CHG-028 — automatic readiness attestation

This control adds a generic, fail-closed evaluator for canonical CONTRACT edges
that require CONTRACT_READY. It can package an existing producer-authored semantic
basis with current-main mechanical evidence; it cannot create semantic acceptance.

The semantic basis convention is `evidence/readiness/<node>.json`. The evaluator
requires exact producer attribution through the merged PR that introduced the basis,
current artifact/test/trace blobs, green current-SHA checks, unchanged canonical
producer scope projections and the edge's non-null precise consumer requirement.

Manual dependency readiness evidence is unchanged and remains authoritative. An
automatic result other than PASS is diagnostic only and never writes Plane.

Implementation, focused verification, merged revision, deployment digest and
read-only production diagnostics are recorded in the pull request.
