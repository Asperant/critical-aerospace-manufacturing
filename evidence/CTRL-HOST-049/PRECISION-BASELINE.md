# CTRL-HOST-049 — precision diagnostic baseline

The approved DEP-023 binding added a precise requirement to one canonical HARD
edge. The deterministic dependency validator therefore emits 166
`PRECISION_MISSING` warnings instead of the previous 166, while retaining the
same 100-node / 217-edge graph and all diagnostic identity assertions.

This is project-control housekeeping only. It changes no product dependency
semantics, readiness level, lifecycle state or evidence claim.
