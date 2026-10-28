# CTRL-HOST-046 — projectctl precision baseline

The canonical dependency graph remains 100 nodes, 217 edges, 208 blocking and
9 non-blocking edges with no hard cycle. `validate_dependencies` returns no
errors or `READINESS_INCOMPATIBLE` findings and produces 167
`PRECISION_MISSING` warnings. The generic regression assertion was stale at
173; CHG-072 aligns only that diagnostic count and does not alter the graph or
product readiness semantics.
