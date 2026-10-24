# WP-CORE-004 — genealogy exposure queries

Owner: Asrın Dündar (Asperant). Date: 24 October 2026.
Implementation revision: the commit containing this evidence on
`wp/WP-CORE-004-temporal-genealogy`, starting from
`6c140b8ad7f2ce89c1ecbc6dca18595d0b9201b1`.

## Canonical basis and implementation

Read the live own-profile queue (WP-CORE-004 IN_PROGRESS, unblocked), exact
`projectctl context WP-CORE-004`, WBS card, FR-CORE-009…012/RTM, architecture
Genealogy section, Item 25 temporal/backward/forward/exposure/query families,
applicable DoR/DoD, and accepted IMPLEMENTATION-START.md. This implements the
planned stored component/lot history and equipment/time exposure query boundary,
with its bounded WP-NORMAL query sanity check. It is an additive internal derived
implementation, not a new public transport/schema or architectural decision.

`GenealogyQueries` exposes typed frozen requests/results, reusing the immutable
history models. Rework reads preserve original/rework segments, directive origin,
execution IDs, route/visit revisions and stored append order. Lot reads traverse
backward ancestry or forward descendants using world-scoped recursive relational
queries. Complete event parent/child snapshots, including merge context, remain
intact. Component reads start from that component's exact stored lot memberships;
merge context never asserts target membership in another parent lot.

Lineage facts are causally ordered. Among ready independent facts, UTC occurrence,
effectivity and identity make ordering deterministic; recording time is retained
but never substitutes for occurrence. Original delivery positions remain explicit.
Recursive UNION deduplicates shared ancestry without truncating depth. The selected
event IDs are captured with the traversal snapshot; later supported appends cannot
rewrite selected facts. Caller-managed isolation remains necessary for broader
cross-query snapshot semantics; no global freshness/completeness claim is made.

Equipment/time reads use actual execution equipment, not route assignments, with
half-open overlap windows and optional historical operation class. Zero-length
visits are instants. Each re-entrant visit retains segment/visit position, route
revision and directive reference. Cohort equipment summaries count distinct target
components, not visits; return execution references and explicitly missing history.
Their denominator is the requested distinct cohort, including missing histories;
missing history does not establish no exposure. Correlation is not causality.

Unknown stored history returns None; unknown equipment exposure returns an empty
tuple. Missing schemas/real DB failures propagate rather than becoming empty
manufacturing histories. Existing structured telemetry provides correlated
outcome/duration without domain payloads or credentials. The GET-only health
method checks read access to both storage surfaces; READY is access health only.

No migration, persistence write, arbitrary SQL input, HTTP endpoint, UI, command
handler, protected action, Plane/lifecycle write or unrelated Core refactor is
added. Existing repositories and migrations are unchanged. Lineage is world-scoped;
execution storage still uses global canonical component identities with no world
binding. RecipeVersions, inspection/hold/maintenance facts and producer fields
absent from the persisted contracts are not synthesized. The broader Item 25
integration families are not represented as complete by this internal interface.

## Focused checks executed

Real PostgreSQL 18.6 in an isolated temporary Unix-socket cluster, no TCP listener;
restricted migration/runtime roles and isolated databases, all synthetic fixtures.
Cluster data was removed after shutdown. No full platform or broad suite ran.

| Check | Actual result |
|---|---|
| `ci/.venv/bin/python -m pytest -c services/manufacturing-core/pyproject.toml services/manufacturing-core/tests/persistence/test_genealogy_queries.py -m integration -q -s` with disposable `CI_PG_DSN`, `CORE_TEST_DISPOSABLE=1` | 24 passed in 1.47 s |
| `ci/.venv/bin/ruff check` on genealogy_queries.py and test_genealogy_queries.py | All checks passed |
| `ci/.venv/bin/ruff format --check` on those files | 2 files already formatted |
| `ci/.venv/bin/pyright --project services/manufacturing-core/pyrightconfig.json --pythonpath ci/.venv/bin/python` | 0 errors, 0 warnings |
| `projectctl validate --json` after scoped RTM references | Exit 0, 634 existing diagnostics, zero errors |
| `git diff --check` | PASS |

Coverage: persisted rework/directive/route retrieval; split and merge ancestry;
four-generation diamonds; forward impact; component memberships versus merge
context; deterministic causal/temporal ordering despite reversed delivery and
recording time; independent timestamp ties; retained persisted positions; unknown
world/material/equipment and known components without history; actual versus
planned equipment; re-entrant exposure; time/operation filters; zero-duration
window boundaries; cohort component counts/ratios/missing history; invalid query
requests; correlated success/failure telemetry; missing-schema failure; read-only
transaction health/query paths. An initial 18-case run passed, then focused cases
were added for health/failure/scale/ties and the zero-duration boundary; the final
24-case run above passed. Ruff caught and corrected import/fixture-shadowing/lambda
style issues; no failing product assertion was weakened or removed.

## Bounded WP-NORMAL sanity

100 equipment identities; 1,000 terminal material lots plus six retained ancestors;
1,000 components with stored execution histories. The multi-generation lineage
branch retains its other conserved components. Query results were asserted on
every sample. Thirty sequential samples per query on this shared Linux host,
private PostgreSQL with 16 MiB shared buffers, no concurrent platform startup:

| Query | median ms | p95 ms (nearest rank) | max ms | samples |
|---|---:|---:|---:|---:|
| Four-generation ancestry | 1.716 | 2.211 | 2.391 | 30 |
| Actual equipment/time exposure | 0.424 | 0.638 | 0.760 | 30 |

This is local synthetic query sanity, not final integrated WP-NORMAL workload,
soak/concurrency acceptance or real manufacturing performance. No canonical
latency target or integrated scenario pass is inferred. Logs remained at
`/tmp/asrin-core004-genealogy-iws6ydcr/tests.log` for this run.

## One canonical scope check and remaining work

Append-only history, split/merge facts/persistence and the prepared stored
history/equipment-time exposure query capability now exist with focused checks.
FR-CORE-010/011/012 realization references point to the read interface; requirement
coverage remains ALLOCATED and final accepted evidence NOT_YET_EXECUTED. There is
no accepted EvidenceID or DoD completion claim.

The scope check also finds a genuine unimplemented product requirement:
WP-CORE-004's task "implement ReworkDirective execution without overwriting
history" and FR-CORE-009's `ExecuteApprovedReworkDirective` exposure still lack
that command's contract/handler and governed lifecycle execution binding. The
current values/repositories/query interface represent supplied facts; none executes
a protected directive. The repository's existing README and RTM already identify
this gap. It cannot be relabeled as mere missing test evidence or as implemented
by fixture persistence. Product implementation work remains beyond this query-only
authorization; full WP implementation completion is therefore not certified.

DEP-029 still requires attributable DN-CORE-LIFECYCLE COMPONENT_READY consumer
binding and queries over real lineage at INTEGRATION. Its precise consumer fields
are absent from the canonical edge. This slice does not certify those readiness
facts or establish whether the command gap can presently cross that boundary.
Recipe/inspection/hold/maintenance/world execution bindings require their actual
producer contracts, rather than inferred data. AV-SCEN-01, BENCH-E2E-001,
BENCH-RQ1-001, protected execution tests, CI/post-merge validation and final DoD
remain unproven. No lifecycle state or blocker projection was changed. AUTO_NEXT,
deployment and the two pre-existing untracked Asrın audit files were untouched.


## Closeout classification clarification

[CLOSEOUT-PART1.md](CLOSEOUT-PART1.md) reconciles the completed slice commits and
clarifies the remaining requirement after binding inspection:
`ExecuteApprovedReworkDirective` is blocked by missing authoritative approval
lookup, lifecycle transition interface, and frozen protected-command contract.
The command gap is not currently independently owner-executable on this branch;
no full-WP implementation/DoD completion is asserted. The historical query test
results and limitations above remain unchanged.
