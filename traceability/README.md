# traceability/ — machine-readable trace registry (WP-GOV-002)

The trace graph of 01 Item 83 and 03 §4 as data: requirement nodes and
TraceEdges in the controlled relation vocabulary, checked in CI by the trace
linter (03 §18.1). Requirements: FR-GOV-004, FR-GOV-005, FR-GOV-009,
NFR-GOV-009. Tooling: `tools/trace` (`cap_trace`).

| File | Content |
|---|---|
| `trace_schema.json` | `cap.trace-registry/v1`: requirement nodes (class, owner, anchor, realization, acceptance, state, measurement, note) and edges `{from, relation, to, applicability}` |
| `trace_edges.yaml` | the registry: 306 requirement nodes and their edges, seeded from the 03 §17 records |
| `generated/` | views generated from the registry only (Item 83 layout): `requirements.csv` (one wide row per requirement), `verification_coverage.csv` (backward trace asset → requirements), `evidence_coverage.csv`, `claim_coverage.csv` (empty until claims exist), `orphan_report.json`; never edited by hand |

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
mfgctl trace validate --base origin/main   # what CI runs
mfgctl trace generate                      # refresh traceability/generated/
mfgctl trace seed                          # registry from 03 §17, then the views
mfgctl trace drift                         # registry vs 03 §17 (CI: --strict)
mfgctl trace impact --body-file pr.md      # TL-13 on a PR description
mfgctl trace requirement FR-GOV-009        # one requirement's node and edges
mfgctl trace orphans                       # orphan report summary
```

`mfgctl trace` runs the same `cap_trace` commands in the repository root; without mfgctl:

```bash
export PYTHONPATH=tools/trace/src
uv run --project ci --locked python -m cap_trace validate        # lint; exit 1 on findings
uv run --project ci --locked python -m cap_trace validate --base origin/main  # plus TL-08 regression
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
| TL-02 referenced IDs | slice 2 | registry nodes = active catalog requirements; each target resolves in the registry its relation names (table below) |
| TL-03 superseded misuse | slice 2 | a retired or superseded requirement carries no node and no edges |
| TL-10 prefix boundaries | slice 2 | identities are matched as whole tokens: `REAL-INV-01` is not found in `SIM-REAL-INV-01`, `ARCH-INV-04` is not `ARCH-INV-004` (03 GAP-RTM-016) |
| TL-06 dangling | slice 3 | EXECUTED_AS → a run record of the producing work package (`evidence/WP-<AREA>-<NNN>/`: a file or directory named by the run ID, or the ID written in its records); EVIDENCED_BY → a sealed bundle directory `EVID-*`; SUPPORTS_CLAIM → a claim register (none exists yet, so any claim fails) |
| TL-08 coverage | slice 3 | every active F0/F1 has ≥1 DERIVED_FROM (FR-GOV-004), ALLOCATED_TO and VERIFIED_BY (FR-GOV-005); with `--base REV`, none of those edges disappears unless the requirement note cites an existing `CHG-NNN` |
| TL-09 stale claims | slice 3 | no SUPPORTS_CLAIM from a requirement whose evidence state is STALE |
| TL-11 class sufficiency | slice 3 | F0 ⇒ integrated scenario/demo path; H0 ⇒ TEST/DRILL/SCENARIO asset, not inspection- or benchmark-only; FR verify codes (03 View D) E → integrated asset (scenario, demo, or a family whose minimum environment is INTEGRATION or later), B → BENCH, R → DRILL or restart test, N → executable TEST/DRILL, D → DEMO, I → inspection or lint; T is not an audited code (03 §22 C-08…C-13) |
| TL-12 evidence | slice 3 | coverage VERIFIED or evidence CURRENT ⇒ ≥1 EVIDENCED_BY; a final NFR also needs an observed measurement (NFR-GOV-009) |
| TL-07 freshness | slice 4 | every file in `generated/` equals what the registry produces now; missing, stale or foreign files fail |
| TL-13 impact | slice 5 | a PR that changes anything outside `docs/`, `evidence/`, `09_change/`, `project_control/` or Markdown names its impacted requirements in the template field `Requirements (...)`: active catalog IDs, or `NONE — reason` / a control-only explanation; the check also lists each declared requirement's owner for advisory review (CHG-018) |

## Where TL-02 resolves each relation

| Relation | Resolved against |
|---|---|
| DERIVED_FROM | `ITEM-nn` → 01 item headings (`# NN — Title`); `<FAMILY>-INV-nn` → identity tokens of 01 |
| ALLOCATED_TO | 02 Architecture Component ID Registry and its append-only allocations (CHG-010); `ARCH-INV-*` excluded |
| VERIFIED_BY | 03 §9.X Verification Asset Registry, 03 §19 concrete assets, `ci/test-strategy.json` TestIDs |
| DECIDED_BY | `docs/adr/NNNN-*.md` |
| EXERCISED_IN, MITIGATES | identity tokens of 01 (scenarios, Item 69 risk register `<AREA>-Rnn`) |
| EXPOSED_BY | `IC-<NS>-nnn` and `IC-<NS>-*` → identity tokens of 01 and 02; descriptive surfaces are not resolvable yet (exact schema versions TBD, 03 §4.2) |
| REALIZED_BY | `repo:<path>` must exist in the repository; `TBD_BY_IMPLEMENTATION` is planned |
| USES_DATA, USES_MODEL, GOVERNED_BY | artifact *types*, no identity registry exists (03 §4.2: no DatasetVersion/ModelPackage IDs invented) — counted, not resolved |
| EXECUTED_AS, EVIDENCED_BY, SUPPORTS_CLAIM | run and evidence identities, resolved by TL-06 |

`validate` prints how many edges fall into each mode, so nothing is silently
treated as checked.

## 03 §17 is the source (decided 25 October 2026)

Owners keep editing the 03 §17 records in their own PRs, as 03 §19 describes.
In the same PR they run `mfgctl trace seed`, which refreshes
`trace_edges.yaml` and `generated/`. CI runs `drift --strict` and TL-07, so a
PR that changes 03 §17 without refreshing fails with the command to run. The
registry is never edited by hand.
