# traceability/ — machine-readable trace registry (WP-GOV-002)

The trace graph of 01 Item 83 and 03 §4 as data: requirement nodes and
TraceEdges in the controlled relation vocabulary, checked in CI by the trace
linter (03 §18.1). Requirements: FR-GOV-004, FR-GOV-005, FR-GOV-009,
NFR-GOV-009. Tooling: `tools/trace` (`cap_trace`).

| File | Content |
|---|---|
| `trace_schema.json` | `cap.trace-registry/v1`: requirement nodes (class, owner, anchor, realization, acceptance, state, measurement, note) and edges `{from, relation, to, applicability}` |
| `trace_edges.yaml` | the registry: 306 requirement nodes and their edges, seeded from the 03 §17 records |

## Model

| Element | Rule |
|---|---|
| Edge identity | `from + relation + to` (Item 83); no random edge IDs, Git history records when an edge appeared |
| Relations | the 03 §4.2 vocabulary only: DERIVED_FROM, ALLOCATED_TO, DECIDED_BY, EXPOSED_BY, REALIZED_BY, USES_DATA, USES_MODEL, GOVERNED_BY, EXERCISED_IN, VERIFIED_BY, EXECUTED_AS, EVIDENCED_BY, SUPPORTS_CLAIM, MITIGATES, CARRIES_DEBT; vague relations (`related_to`, `maybe_supports`) are rejected |
| Applicability | `PLANNED` — from the planning baseline; `RECORDED` — the target exists or ran (a repository path, a run record, an evidence bundle) |
| REALIZED_BY | one edge per repository path named in the 03 reference (`repo:<path>`, RECORDED) plus one `TBD_BY_IMPLEMENTATION` edge (PLANNED) while any part is still planned; the reference text itself is kept on the node |
| Requirement text | never copied (Item 83 #3); the node carries identity-level attributes only |

## Commands (repository root)

```bash
export PYTHONPATH=tools/trace/src
uv run --project ci --locked python -m cap_trace validate        # lint; exit 1 on findings
uv run --project ci --locked python -m cap_trace validate --json # machine-readable result
uv run --project ci --locked python -m cap_trace seed            # regenerate from 03 §17
uv run --project ci --locked python -m cap_trace drift           # registry vs 03 §17
```

Exit codes: 0 clean; 1 findings (or drift with `--strict`); 2 inputs unreadable
(missing file, invalid YAML, a §17 record that cannot be seeded without guessing).

## Checks implemented

| Check | State | Rule |
|---|---|---|
| TL-01 schema | slice 1 | every node and edge validates against `trace_schema.json`; every edge starts at a declared requirement |
| TL-04 vocabulary | slice 1 | relation ∈ controlled set |
| TL-05 duplicates | slice 1 | edge identity unique |
| TL-02, TL-03, TL-10 | slice 2 | referenced IDs exist (catalog, 02, 01 index, verification registry), superseded misuse, prefix-boundary-safe matching |
| TL-06, TL-08, TL-09, TL-11, TL-12 | slice 3 | dangling run/evidence, coverage regression, stale evidence, class sufficiency, no VERIFIED without evidence |
| TL-07 | slice 4 | generated views fresh (`mfgctl trace`) |
| TL-13 | slice 5 | PR Requirement-Impact declared |

## Relation to 03 (until slice 4)

03 stays the canonical document and every owner keeps updating 03 §17 in their
own PRs (03 §19). The registry is seeded from it; `drift` reports any
difference and does not fail CI, so another owner's 03 edit never blocks their
work. Refresh with `seed` when drift is reported. Which side is generated from
which is settled in slice 4 together with the 03 maintainers.
